# routers/rules.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import os
import models
from dependencies import get_db, get_current_user

router = APIRouter(tags=["Knowledge Base"])

@router.post("/api/rules/upload")
async def upload_rules(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user)
):
    # THE PAYWALL
    if current_user.tier != "pro":
        raise HTTPException(status_code=403, detail="Upgrade to Pro to unlock custom rulebooks.")

    user_rules_dir = f"storage/rules/user_{current_user.id}"
    os.makedirs(user_rules_dir, exist_ok=True)
    
    file_path = os.path.join(user_rules_dir, "policy.md")
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    return {"message": f"Successfully updated rules for {current_user.email}"}