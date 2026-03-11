import os
import json
import re
import fitz  # PyMuPDF
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.gemini import Gemini
from llama_index.llms.groq import Groq
from llama_index.embeddings.gemini import GeminiEmbedding

load_dotenv()

# Global Settings
Settings.embed_model = GeminiEmbedding(
    api_key=os.environ.get("GEMINI_API_KEY"),
    model_name="models/embedding-001"  # <--- Change this line right here
)
Settings.llm = Groq(
    api_key=os.environ.get("GROQ_API_KEY"), 
    model="llama-3.3-70b-versatile"
)

class ExtractionAgent:
    def __init__(self):
        self.llm = Gemini(
            api_key=os.environ.get("GEMINI_API_KEY"), 
            model="models/gemini-3.1-flash-lite-preview"
        )
        
    def run(self, file_path: str) -> list[str]:
        # 1. Extract physical text from the PDF
        raw_text = ""
        try:
            doc = fitz.open(file_path)
            for page in doc:
                raw_text += page.get_text()
        except Exception as e:
            print(f"Failed to read PDF: {e}")
            return []
            
        # 2. Ask Gemini to chunk it logically
        prompt = f"""
        Extract the individual legal clauses from the following contract text. 
        Return ONLY a valid JSON list of strings, where each string is a distinct clause.
        Do not include markdown formatting or conversational text.
        Text: {raw_text[:15000]} # Limiting characters to ensure speed
        """
        
        response = self.llm.complete(prompt)
        
        # 3. Bulletproof JSON extraction using Regex
        try:
            # Look for everything between the first [ and the last ]
            match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                return json.loads(response.text)
        except json.JSONDecodeError:
            print("Regex failed. Falling back to raw text chunking.")
            return [raw_text]

class AuditAgent:
    def __init__(self, user_id: int):
        # 1. Dynamically target the user's private rulebook folder
        self.rules_dir = f"storage/rules/user_{user_id}"
        self.query_engine = None

        # 2. Safety Check: If they haven't uploaded rules yet, gracefully skip the audit
        if not os.path.exists(self.rules_dir) or not os.listdir(self.rules_dir):
            print(f"User {user_id} has no custom rules. Audit will return compliant by default.")
            return

        # 3. Load the user-specific Vector Database
        try:
            self.compliance_docs = SimpleDirectoryReader(self.rules_dir).load_data()
            
            embed_model = GeminiEmbedding(
                api_key=os.environ.get("GEMINI_API_KEY"),
                model_name="models/gemini-embedding-001"
            )
            
            self.index = VectorStoreIndex.from_documents(
                self.compliance_docs,
                embed_model=embed_model
            )
            self.query_engine = self.index.as_query_engine()
            print(f"Successfully loaded Vector DB for User {user_id}!")
            
        except Exception as e:
            print(f"Warning: Could not load rules for User {user_id}. {e}")

    def evaluate_clauses(self, clauses: list) -> list[dict]:
        flagged_items = []
        # If no query engine exists (because they have no rules), return empty list (compliant)
        if not self.query_engine: 
            return flagged_items

        for clause in clauses:
            prompt = f"""
            Audit this clause against our compliance rules: "{clause}"
            If it violates a rule, output ONLY a JSON object with keys: 
            "violation" (string), "confidence" (float 0.0-1.0), and "source_citation" (string).
            If it is completely compliant, output EXACTLY the word "COMPLIANT".
            """
            
            response = self.query_engine.query(prompt)
            result_text = str(response).strip()
            
            if "COMPLIANT" not in result_text.upper():
                try:
                    match = re.search(r'\{.*\}', result_text, re.DOTALL)
                    if match:
                        issue = json.loads(match.group(0))
                        issue["original_text"] = clause
                        flagged_items.append(issue)
                except json.JSONDecodeError:
                    pass
                    
        return flagged_items


class DraftingAgent:
    def __init__(self):
        self.llm = Gemini(
            api_key=os.environ.get("GEMINI_API_KEY"), 
            model="models/gemini-3.1-flash-lite-preview"
        )

    def rewrite_clause(self, original_text: str, violation: str) -> str:
        prompt = f"""
        You are an expert contract lawyer. Rewrite the following clause so it is compliant.
        Original: "{original_text}"
        Reason it was flagged: "{violation}"
        
        Return ONLY the rewritten clause, keeping the professional legal tone.
        """
        response = self.llm.complete(prompt)
        return response.text.strip()