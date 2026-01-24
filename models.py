"""
Database models for the story application
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# This should match the db instance in main.py
# In main.py: db = SQLAlchemy(app)
# Import this db instance here or pass it appropriately

db = None  # This will be set by importing from main.py

class Story(db.Model):
    """Story model"""
    __tablename__ = 'stories'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    genre = db.Column(db.String(50), nullable=False)
    theme = db.Column(db.String(200), nullable=False)
    characters = db.Column(db.Text)
    setting = db.Column(db.String(200))
    length = db.Column(db.String(20), default='short')
    content = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, generating, completed, failed
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
