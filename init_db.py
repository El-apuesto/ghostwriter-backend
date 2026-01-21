#!/usr/bin/env python3
"""
Initialize database tables
Run this to create all tables in the database
"""
import os
import sys
from sqlalchemy import create_engine, text
from models import Base, User
from config import settings

print("🔧 Initializing GhostWriter Database...\n")

# Get database URL
database_url = settings.database_url

# Fix PostgreSQL URL for psycopg3
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)

print(f"Database URL: {database_url[:30]}...\n")

# Create engine
engine = create_engine(database_url, pool_pre_ping=True)

try:
    # Create all tables
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!\n")
    
    # Verify tables exist
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = [row[0] for row in result]
        
    if tables:
        print("📋 Tables in database:")
        for table in tables:
            print(f"   - {table}")
    else:
        print("⚠️  No tables found!")
    
    print("\n✅ Database initialization complete!")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    sys.exit(1)
