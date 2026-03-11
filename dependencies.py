from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import jwt 
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # THE FIX: Grab the secret dynamically at runtime so it always matches auth.py!
    JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "your_secret_key")
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            print("❌ AUTH ERROR: Token is missing the email payload.")
            raise HTTPException(status_code=401, detail="Invalid token")
            
    except jwt.ExpiredSignatureError:
        print("❌ AUTH ERROR: The JWT token has expired.")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        print(f"❌ AUTH ERROR: JWT decoding failed - {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token signature")
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        print(f"❌ AUTH ERROR: User {email} not found in the database.")
        raise HTTPException(status_code=401, detail="User not found")
        
    return user