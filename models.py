from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    stripe_customer_id = Column(String, nullable=True)
    subscription_status = Column(String, default="free")  # free, active, cancelled
    subscription_end = Column(DateTime, nullable=True)
    stories_generated = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Story(Base):
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    story_type = Column(String)  # fiction, biography
    title = Column(String)
    length_type = Column(String)  # sample, novella, novel, etc.
    content = Column(Text)  # JSON string
    metadata = Column(Text)  # JSON string
    generation_status = Column(String, default="pending")  # pending, generating, complete, error
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
