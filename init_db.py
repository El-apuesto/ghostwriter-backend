"""
Initialize database tables for FastAPI
Replace your entire init_db.py with this
"""
from database import engine
from models import Base

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✓ Database tables created successfully!")
print("✓ Tables: users, stories")
