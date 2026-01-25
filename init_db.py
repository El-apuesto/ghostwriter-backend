"""Initialize database - drops old tables and creates fresh ones"""
from database import engine
from models import Base
from sqlalchemy import text

print("Dropping existing tables with CASCADE...")

# Drop tables manually with CASCADE to handle foreign key dependencies
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS story_extras CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS transactions CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS stories CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))

print("✓ Old tables dropped")

print("Creating fresh database tables...")
Base.metadata.create_all(bind=engine)
print("✓ Database tables created successfully!")
print("✓ Tables: users, stories")