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
            model="models/gemini-2.5-flash"
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
    def __init__(self):
        # 1. Force create the directory and a dummy policy file
        os.makedirs("rules", exist_ok=True)
        policy_path = os.path.join("rules", "policy.txt")
        
        if not os.path.exists(policy_path):
            with open(policy_path, "w") as f:
                f.write("COMPANY COMPLIANCE POLICY FOR FREELANCE CONTRACTS\n\nRULE 1 - PAYMENT TERMS:\nAll client payments must be made within a Net-30 day schedule from the date of invoice receipt. Any payment terms extending beyond 30 days (such as Net-60, Net-90, or Net-120) are strictly prohibited and non-compliant.\n\nRULE 2 - LIMITATION OF LIABILITY:\nIndependent Contractors shall not assume uncapped or unlimited financial liability under any circumstances. Liability must be strictly capped at the total project fee paid to the contractor. Any clause forcing the contractor to cover total business losses or unlimited damages is non-compliant.")

        # 2. Load the vector database with the NEWEST embedding model
        try:
            self.compliance_docs = SimpleDirectoryReader("rules").load_data()
            
            embed_model = GeminiEmbedding(
                api_key=os.environ.get("GEMINI_API_KEY"),
                model_name="models/gemini-embedding-001" # <--- UPDATED HERE
            )
            
            self.index = VectorStoreIndex.from_documents(
                self.compliance_docs,
                embed_model=embed_model
            )
            self.query_engine = self.index.as_query_engine()
            print("Successfully loaded rules into the Vector DB!")
            
        except Exception as e:
            print(f"Warning: Could not load rules directory. {e}")
            self.query_engine = None

    def evaluate_clauses(self, clauses: list) -> list[dict]:
        flagged_items = []
        if not self.query_engine: return flagged_items

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
                    # Look for everything between the first { and the last }
                    match = re.search(r'\{.*\}', result_text, re.DOTALL)
                    if match:
                        issue = json.loads(match.group(0))
                        issue["original_text"] = clause
                        flagged_items.append(issue)
                except json.JSONDecodeError:
                    print(f"Failed to parse Audit Agent output: {result_text}")
                    pass
                    
        return flagged_items


class DraftingAgent:
    def __init__(self):
        self.llm = Gemini(
            api_key=os.environ.get("GEMINI_API_KEY"), 
            model="models/gemini-2.5-flash"
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