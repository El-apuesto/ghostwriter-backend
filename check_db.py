#!/usr/bin/env python3
"""
Check database schema and create user without reset_token fields
"""
from database import get_db
from models import User
from datetime import datetime

def create_capi_user_simple():
    """Create therealcapicapi@gmail.com user with 10,000 credits - simple version"""
    
    db = next(get_db())
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == "therealcapicapi@gmail.com").first()
        if existing_user:
            print(f"✅ User {existing_user.email} already exists!")
            print(f"👤 Name: {existing_user.full_name}")
            print(f"💰 Current balance: {existing_user.credits_balance:,} credits")
            
            # Add 10,000 credits if they don't have enough
            if existing_user.credits_balance < 10000:
                existing_user.add_credits(10000 - existing_user.credits_balance)
                db.commit()
                print(f"🎉 Added credits! New balance: {existing_user.credits_balance:,}")
            return
        
        # Create new user without reset_token fields
        user = User(
            email="therealcapicapi@gmail.com",
            full_name="Capi",
            is_active=True,
            credits_balance=10000,
            total_credits_purchased=10000,
            total_credits_spent=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Set a default password
        user.set_password("phantm123")
        
        db.add(user)
        db.commit()
        
        print(f"✅ Created user: {user.email}")
        print(f"👤 Name: {user.full_name}")
        print(f"💰 Credits: {user.credits_balance:,}")
        print(f"🔑 Default password: phantm123")
        print(f"⚠️  Please change your password after first login!")
        
    except Exception as e:
        print(f"❌ Error creating user: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_capi_user_simple()
