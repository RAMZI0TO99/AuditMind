import models
import asyncio
from sqlalchemy.orm import Session
from websocket_manager import manager
from agents import ExtractionAgent, AuditAgent, DraftingAgent

async def process_document_agents(document_id: int, file_path: str, user_id: int, db: Session):
    try:
        print(f"\n[Doc {document_id}] Starting AI Pipeline...")

        doc = db.query(models.Document).filter(models.Document.id == document_id).first()
        if doc:
            doc.status = "processing"
            db.commit()

        # A tiny pause just to let the frontend switch UI states
        await asyncio.sleep(0.5)

        # 1. Extraction Phase
        print(f"[Doc {document_id}] Waking up ExtractionAgent...")
        await manager.broadcast_to_document(document_id, {
            "agent": "Extraction", 
            "message": "Extracting clauses from PDF...", 
            "status": "processing"
        })
        
        extractor = ExtractionAgent()
        # THE FIX: Run the blocking extraction in a separate thread!
        clauses = await asyncio.to_thread(extractor.run, file_path)

        if not clauses:
            raise Exception("No text could be extracted from the document.")

        # 2. Audit Phase 
        print(f"[Doc {document_id}] Waking up AuditAgent for User {user_id}...")
        await manager.broadcast_to_document(document_id, {
            "agent": "Audit", 
            "message": "Loading custom rulebook and evaluating clauses...", 
            "status": "processing"
        })
        
        auditor = AuditAgent(user_id=user_id) 
        # THE FIX: Run the blocking RAG queries in a separate thread!
        flagged_items = await asyncio.to_thread(auditor.evaluate_clauses, clauses)

        # 3. Drafting Phase
        if flagged_items:
            print(f"[Doc {document_id}] Found {len(flagged_items)} risks. Waking up DraftingAgent...")
            await manager.broadcast_to_document(document_id, {
                "agent": "Drafting", 
                "message": f"Found {len(flagged_items)} risk(s). Drafting compliant rewrites...", 
                "status": "processing"
            })
            
            drafter = DraftingAgent()
            seen_texts = set() 
            
            for item in flagged_items:
                original = item["original_text"].strip()
                
                if original in seen_texts:
                    continue
                seen_texts.add(original)
                
                # THE FIX: Run the blocking rewrite generation in a separate thread!
                rewrite = await asyncio.to_thread(drafter.rewrite_clause, original, item["violation"])
                
                finding = models.AuditFinding(
                    document_id=document_id,
                    original_text=original,
                    issue_description=item["violation"],
                    suggested_rewrite=rewrite,
                    rule_citation=item.get("source_citation", "Standard Policy"),
                    confidence_score=item.get("confidence", 0.90)
                )
                db.add(finding)
            
            db.commit()
        else:
            print(f"[Doc {document_id}] No violations found.")
            await manager.broadcast_to_document(document_id, {
                "agent": "Audit", 
                "message": "No compliance violations found.", 
                "status": "processing"
            })

        # Finalize
        if doc:
            doc.status = "completed"
            db.commit()

        print(f"[Doc {document_id}] Pipeline Complete.")
        await manager.broadcast_to_document(document_id, {
            "agent": "System", 
            "message": "Audit complete. Generating report.", 
            "status": "completed"
        })

    except Exception as e:
        print(f"\n[Doc {document_id}] Pipeline Error: {e}")
        doc = db.query(models.Document).filter(models.Document.id == document_id).first()
        if doc:
            doc.status = "failed"
            db.commit()
            
        await manager.broadcast_to_document(document_id, {
            "agent": "System", 
            "message": f"Audit failed: {str(e)}", 
            "status": "failed"
        })