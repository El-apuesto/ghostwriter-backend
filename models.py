"""
Database models for FastAPI + SQLAlchemy
"""
from datetime import datetime
import bcrypt
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    """User model with authentication and credits"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Credits system
    credits_balance = Column(Integer, default=0)
    total_credits_purchased = Column(Integer, default=0)
    total_credits_spent = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    def set_password(self, password: str):
        """Hash and set password"""
        salt = bcrypt.gensalt()
        self.hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Verify password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.hashed_password.encode('utf-8'))
    
    def add_credits(self, amount: int):
        """Add credits to user balance"""
        self.credits_balance += amount
        self.total_credits_purchased += amount
    
    def deduct_credits(self, amount: int) -> bool:
        """Deduct credits if sufficient balance"""
        if self.credits_balance >= amount:
            self.credits_balance -= amount
            self.total_credits_spent += amount
            return True
        return False
    
    def __repr__(self):
        return f'<User {self.id}: {self.email}>'


class Story(Base):
    """Story model for AI-generated stories"""
    __tablename__ = 'stories'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # Will add ForeignKey later
    title = Column(String(200))
    genre = Column(String(50), nullable=False)
    theme = Column(String(200), nullable=False)
    characters = Column(Text)
    setting = Column(String(200))
    length = Column(String(20), default='short')
    content = Column(Text)
    status = Column(String(20), default='pending')  # pending, generating, completed, failed
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert story to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
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
