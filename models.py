from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import declarative_base, relationship
import datetime
import enum

Base = declarative_base()

class DocStatus(enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String) # <--- NEW: Secure password storage
    stripe_customer_id = Column(String, nullable=True)
    tier = Column(String, default="basic")
    
    documents = relationship("Document", back_populates="owner")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String)
    status = Column(Enum(DocStatus), default=DocStatus.uploaded)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    owner = relationship("User", back_populates="documents")
    findings = relationship("AuditFinding", back_populates="document")

class AuditFinding(Base):
    __tablename__ = "audit_findings"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    original_text = Column(String)
    issue_description = Column(String)
    confidence_score = Column(Float)
    suggested_rewrite = Column(String)
    rule_citation = Column(String)
    
    document = relationship("Document", back_populates="findings")