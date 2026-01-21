#!/usr/bin/env python3
"""
Create a test user with unlimited credits
Run this from Render shell or locally with production DB URL
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Base
from config import settings

def create_test_user(email, password, credits=999999):
    """Create a test user with specified credits"""
    
    # Setup database connection
    database_url = settings.database_url
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if user exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"❌ User {email} already exists!")
            print(f"   Current credits: {existing.credits_balance}")
            
            # Update credits for existing user
            existing.credits_balance = credits
            db.commit()
            print(f"✅ Updated credits to {credits}")
            return
        
        # Create new user
        user = User(
            email=email,
            full_name="Test User",
            credits_balance=credits,
            is_active=True
        )
        user.set_password(password)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"✅ User created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Credits: {credits}")
        print(f"   User ID: {user.id}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Get email from command line or use default
    email = sys.argv[1] if len(sys.argv) > 1 else "thecitieschoice@gmail.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "ghostwriter123"
    credits = int(sys.argv[3]) if len(sys.argv) > 3 else 999999
    
    print(f"🔧 Creating test user...")
    create_test_user(email, password, credits)
