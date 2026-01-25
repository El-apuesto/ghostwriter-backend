"""Fix database schema - drops and recreates tables with correct columns"""
from database import engine
from models import Base

print("Dropping existing tables...")
Base.metadata.drop_all(bind=engine)
print("✓ Tables dropped")

print("Creating fresh tables...")
Base.metadata.create_all(bind=engine)
print("✓ Database tables created successfully!")
print("✓ Tables: users, stories")
