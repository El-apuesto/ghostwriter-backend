"""
Database models for FastAPI + SQLAlchemy
Replace your ENTIRE models.py file with this
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    """User model"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    username = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Story(Base):
    """Story model for AI-generated stories"""
    __tablename__ = 'stories'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    genre = Column(String(50), nullable=False)
    theme = Column(String(200), nullable=False)
    characters = Column(Text)
    setting = Column(String(200))
    length = Column(String(20), default='short')
    content = Column(Text)
    status = Column(String(20), default='pending')
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert story to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'genre': self.genre,
            'theme': self.theme,
            'characters': self.characters,
            'setting': self.setting,
            'length': self.length,
            'content': self.content,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f'<Story {self.id}: {self.title or "Untitled"}>'
