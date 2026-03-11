from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
import os
import bcrypt
import models

from dependencies import get_db, get_current_user

# --- MODERN PURE BCRYPT HASHING ---
def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8') # Decode back to string for the DB

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)
    except ValueError:
        return False

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "your_secret_key")
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
# ----------------------------------

router = APIRouter(tags=["Authentication"])

@router.post("/api/signup", status_code=status.HTTP_201_CREATED)
async def signup(user: dict, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.get('email')).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user['password'])
    new_user = models.User(email=user['email'], hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

@router.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/api/me")
async def get_my_profile(current_user: models.User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "tier": current_user.tier 
    }