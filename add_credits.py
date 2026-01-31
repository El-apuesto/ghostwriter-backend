#!/usr/bin/env python3
"""
Add credits to a specific user account
"""
import sys
from database import get_db
from models import User
from datetime import datetime

def add_credits_to_user():
    """Add 10,000 credits to citieschoice@gmail.com"""
    
    # Database session
    db = next(get_db())
    
    try:
        # Find the user
        user = db.query(User).filter(User.email == "citieschoice@gmail.com").first()
        
        if not user:
            print("❌ User citieschoice@gmail.com not found!")
            return False
        
        # Add credits
        credits_to_add = 10000
        user.add_credits(credits_to_add)
        
        db.commit()
        
        print(f"✅ Successfully added {credits_to_add:,} credits to {user.email}")
        print(f"📊 New balance: {user.credits_balance:,} credits")
        return True
        
    except Exception as e:
        print(f"❌ Error adding credits: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    add_credits_to_user()
