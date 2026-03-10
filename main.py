from fastapi import FastAPI, UploadFile, File, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import models
from websocket_manager import manager
from ai_pipeline import process_document_agents

import os
import shutil


os.makedirs("uploads", exist_ok=True)


# --- Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./compliance.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
models.Base.metadata.create_all(bind=engine)

# --- App Initialization ---
app = FastAPI(title="Compliance Guard API")

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependencies ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Routes ---

# 1. Serve the Frontend Dashboard
@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

# 2. Handle the File Upload (Strictly POST)
@app.post("/api/upload")
async def upload_document(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    # 1. Save the physical file to disk
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Mocking a user
    user = db.query(models.User).first()
    if not user:
        user = models.User(email="test@example.com")
        db.add(user)
        db.commit()

    # 3. Save document record
    new_doc = models.Document(filename=file.filename, user_id=user.id)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    # 4. Pass the actual file_path to the orchestrator, not just the name
    background_tasks.add_task(process_document_agents, new_doc.id, file_path, db)
    
    return {"document_id": new_doc.id, "status": new_doc.status}

#

# 3. Handle the WebSocket Live Updates
@app.websocket("/ws/documents/{document_id}")
async def websocket_endpoint(websocket: WebSocket, document_id: int):
    await manager.connect(websocket, document_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, document_id)

# 4. Fetch the Final Report
@app.get("/api/documents/{document_id}/report")
def get_report(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    findings = db.query(models.AuditFinding).filter(models.AuditFinding.document_id == document_id).all()
    return {"status": doc.status, "findings": findings}