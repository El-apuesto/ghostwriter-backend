"""Initialize database - drops old tables and creates fresh ones"""
from database import engine
from models import Base

print("Dropping existing tables...")
Base.metadata.drop_all(bind=engine)
print("✓ Old tables dropped")

print("Creating fresh database tables...")
Base.metadata.create_all(bind=engine)
print("✓ Database tables created successfully!")
print("✓ Tables: users, stories")