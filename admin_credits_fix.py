#!/usr/bin/env python3
"""
Standalone admin script to grant credits
Run on Render or locally with DATABASE_URL env var
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Get database URL from environment
database_url = os.getenv('DATABASE_URL')
if not database_url:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

# Fix PostgreSQL URL for psycopg3
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)

print(f"Connecting to database...")
engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine)

def grant_credits(email, credits):
    """Grant credits to user using raw SQL for reliability"""
    db = SessionLocal()
    try:
        # Check if user exists
        result = db.execute(
            text("SELECT id, email, credits_balance FROM users WHERE LOWER(email) = LOWER(:email)"),
            {"email": email}
        ).fetchone()
        
        if not result:
            print(f"❌ User not found: {email}")
            return False
        
        user_id, user_email, current_balance = result
        print(f"✅ Found user: {user_email} (ID: {user_id})")
        print(f"   Current balance: {current_balance} credits")
        
        # Update credits using raw SQL
        db.execute(
            text("""
                UPDATE users 
                SET credits_balance = :credits,
                    total_credits_purchased = total_credits_purchased + :credits
                WHERE id = :user_id
            """),
            {"credits": credits, "user_id": user_id}
        )
        db.commit()
        
        # Verify update
        result = db.execute(
            text("SELECT credits_balance FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        ).fetchone()
        
        new_balance = result[0]
        print(f"✅ Updated! New balance: {new_balance} credits")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "THECITIESCHOICE@gmail.com"
    credits = int(sys.argv[2]) if len(sys.argv) > 2 else 999999
    
    print(f"\n🔧 Granting {credits} credits to {email}...\n")
    success = grant_credits(email, credits)
    
    if success:
        print("\n✅ SUCCESS! Credits granted.")
        print("   Log out and log back in to see updated balance.\n")
    else:
        print("\n❌ FAILED! Check error messages above.\n")
