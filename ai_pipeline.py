import asyncio
from sqlalchemy.orm import Session
import models
from websocket_manager import manager
from agents import ExtractionAgent, AuditAgent, DraftingAgent

async def process_document_agents(document_id: int, filename: str, db: Session):
    try:
        # Update DB Status
        doc = db.query(models.Document).filter(models.Document.id == document_id).first()
        doc.status = models.DocStatus.processing
        db.commit()

        # Phase 1: Extraction
        await manager.broadcast_status(document_id, {
            "status": "processing", "agent": "Extraction", "message": "Extracting clauses..."
        })
        extractor = ExtractionAgent()
        clauses = extractor.run(filename)
        await asyncio.sleep(1) # Simulating IO wait

        # Phase 2: Audit
        await manager.broadcast_status(document_id, {
            "status": "processing", "agent": "Audit", "message": "Evaluating compliance..."
        })
        auditor = AuditAgent()
        flagged_issues = auditor.evaluate_clauses(clauses)
        await asyncio.sleep(1)

        # Phase 3: Drafting & Saving
        await manager.broadcast_status(document_id, {
            "status": "processing", "agent": "Drafting", "message": "Rewriting risky clauses..."
        })
        drafter = DraftingAgent()
        
        for issue in flagged_issues:
            rewrite = drafter.rewrite_clause(issue["original_text"], issue["violation"])
            
            new_finding = models.AuditFinding(
                document_id=document_id,
                original_text=issue["original_text"],
                issue_description=issue["violation"],
                confidence_score=issue["confidence"],
                suggested_rewrite=rewrite,
                rule_citation=issue["source_citation"]
            )
            db.add(new_finding)

        # Finalize
        doc.status = models.DocStatus.completed
        db.commit()
        await manager.broadcast_status(document_id, {
            "status": "completed", "message": "Audit complete. Report ready."
        })

    except Exception as e:
        doc.status = models.DocStatus.failed
        db.commit()
        await manager.broadcast_status(document_id, {
            "status": "failed", "message": f"Pipeline failed: {str(e)}"
        })