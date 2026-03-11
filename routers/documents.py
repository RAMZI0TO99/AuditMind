# routers/documents.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, WebSocket, BackgroundTasks
from sqlalchemy.orm import Session
import os
import models
from dependencies import get_db, get_current_user
from websocket_manager import manager
from ai_pipeline import process_document_agents

router = APIRouter(tags=["Documents"])

@router.post("/api/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Save the file
    os.makedirs("storage/uploads", exist_ok=True)
    file_path = f"storage/uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Create the database record
    new_doc = models.Document(
        filename=file.filename,
        user_id=current_user.id,
        status="uploaded"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # Fire off the AI pipeline in the background
    background_tasks.add_task(process_document_agents, new_doc.id, file_path, current_user.id, db)

    return {"message": "Upload successful", "document_id": new_doc.id}

@router.websocket("/ws/documents/{document_id}")
async def websocket_endpoint(websocket: WebSocket, document_id: int):
    await manager.connect(websocket, document_id)
    try:
        while True:
            data = await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket, document_id)

@router.get("/api/documents/{document_id}/report")
async def get_report(document_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    doc = db.query(models.Document).filter(models.Document.id == document_id, models.Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    findings = db.query(models.AuditFinding).filter(models.AuditFinding.document_id == document_id).all()
    return {"status": doc.status, "findings": findings}