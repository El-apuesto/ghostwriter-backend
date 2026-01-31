#!/usr/bin/env python3
"""
List all users in the database
"""
from database import get_db
from models import User

def list_users():
    """List all users"""
    
    db = next(get_db())
    
    try:
        users = db.query(User).all()
        
        if not users:
            print("❌ No users found in database!")
            return
        
        print(f"📋 Found {len(users)} users:")
        print("-" * 80)
        
        for user in users:
            print(f"👤 {user.full_name or 'No name'}")
            print(f"📧 {user.email}")
            print(f"💰 Credits: {user.credits_balance:,}")
            print(f"📅 Created: {user.created_at}")
            print("-" * 80)
        
    except Exception as e:
        print(f"❌ Error listing users: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    list_users()
