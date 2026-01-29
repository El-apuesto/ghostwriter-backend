"""
Database models for FastAPI + SQLAlchemy
"""
from datetime import datetime
import bcrypt
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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
    
    # Password reset fields
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
    # Relationships
    stories = relationship("Story", back_populates="user", cascade="all, delete-orphan")
    
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
    """Story model for AI-generated fiction and biographies"""
    __tablename__ = 'stories'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Basic info
    title = Column(String(200))
    story_type = Column(String(20), nullable=False)  # 'fiction' or 'biography'
    status = Column(String(20), default='pending')  # pending, generating, completed, failed
    
    # Fiction fields
    premise = Column(Text)  # Main plot description
    theme = Column(Text)  # Story theme (for compatibility with story_generation.py)
    genre = Column(String(50))
    writing_style = Column(String(50))
    setting = Column(String(500))
    tone = Column(String(200))
    
    # JSON fields for complex data
    themes = Column(JSON)  # Array of theme strings
    characters = Column(JSON)  # Array of {name, role, description, quirks}
    timeline = Column(JSON)  # Array of {chapter, description, mood}
    story_metadata = Column(JSON)  # General metadata storage (chapter outlines, etc.) - renamed from 'metadata' which is SQLAlchemy reserved
    
    # Biography fields
    biography_type = Column(String(50))  # autobiography, biography, memoir
    subject_names = Column(String(200))
    time_period_start = Column(String(100))
    time_period_end = Column(String(100))
    narrative_voice = Column(String(50))
    
    # Biography JSON fields
    birth_details = Column(JSON)
    family_background = Column(JSON)
    childhood = Column(JSON)
    career = Column(JSON)
    relationships = Column(JSON)
    major_events = Column(JSON)  # Array of life events
    challenges = Column(JSON)
    achievements = Column(JSON)
    personality = Column(JSON)
    historical_context = Column(JSON)
    hobbies = Column(JSON)
    philosophy = Column(JSON)
    quotes = Column(JSON)  # Array of {quote, context}
    sources = Column(JSON)
    focus_areas = Column(JSON)  # Array of strings
    
    # Story content and metadata
    length = Column(String(20), default='short')  # short, medium, long, novella, novel, epic
    word_count = Column(Integer, default=0)
    content = Column(Text)  # Generated story text
    chapters = Column(JSON)  # Array of {number, title, content}
    
    # NEW: Chapter progress tracking
    chapters_completed = Column(Integer, default=0)
    total_chapters = Column(Integer, default=0)
    
    # Generation tracking
    error_message = Column(Text)
    credits_cost = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="stories")
    
    def to_dict(self):
        """Convert story to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'story_type': self.story_type,
            'status': self.status,
            'premise': self.premise,
            'theme': self.theme,
            'genre': self.genre,
            'writing_style': self.writing_style,
            'setting': self.setting,
            'tone': self.tone,
            'themes': self.themes,
            'characters': self.characters,
            'timeline': self.timeline,
            'story_metadata': self.story_metadata,
            'biography_type': self.biography_type,
            'subject_names': self.subject_names,
            'time_period_start': self.time_period_start,
            'time_period_end': self.time_period_end,
            'narrative_voice': self.narrative_voice,
            'birth_details': self.birth_details,
            'family_background': self.family_background,
            'childhood': self.childhood,
            'career': self.career,
            'relationships': self.relationships,
            'major_events': self.major_events,
            'challenges': self.challenges,
            'achievements': self.achievements,
            'personality': self.personality,
            'historical_context': self.historical_context,
            'hobbies': self.hobbies,
            'philosophy': self.philosophy,
            'quotes': self.quotes,
            'sources': self.sources,
            'focus_areas': self.focus_areas,
            'length': self.length,
            'word_count': self.word_count,
            'content': self.content,
            'chapters': self.chapters,
            'chapters_completed': self.chapters_completed,
            'total_chapters': self.total_chapters,
            'error_message': self.error_message,
            'credits_cost': self.credits_cost,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
    
    def __repr__(self):
        return f'<Story {self.id}: {self.title or "Untitled"}>'
