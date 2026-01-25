"""
Database migration script to add new fields to Story table
Run this on Render to update production database
"""
from database import engine
from sqlalchemy import text

def add_missing_columns():
    """
    Add new columns to stories table if they don't exist
    """
    print("Starting database migration...\n")
    
    with engine.connect() as conn:
        # Add chapters_completed column
        try:
            conn.execute(text(
                "ALTER TABLE stories ADD COLUMN chapters_completed INTEGER DEFAULT 0"
            ))
            conn.commit()
            print("✓ Added chapters_completed column")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e).lower():
                print("• chapters_completed column already exists")
            else:
                print(f"! Error adding chapters_completed: {e}")
        
        # Add total_chapters column
        try:
            conn.execute(text(
                "ALTER TABLE stories ADD COLUMN total_chapters INTEGER DEFAULT 0"
            ))
            conn.commit()
            print("✓ Added total_chapters column")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e).lower():
                print("• total_chapters column already exists")
            else:
                print(f"! Error adding total_chapters: {e}")
        
        # Add theme column (TEXT type)
        try:
            conn.execute(text(
                "ALTER TABLE stories ADD COLUMN theme TEXT"
            ))
            conn.commit()
            print("✓ Added theme column")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e).lower():
                print("• theme column already exists")
            else:
                print(f"! Error adding theme: {e}")
        
        # Add metadata column (JSON type)
        try:
            conn.execute(text(
                "ALTER TABLE stories ADD COLUMN metadata JSON"
            ))
            conn.commit()
            print("✓ Added metadata column")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e).lower():
                print("• metadata column already exists")
            else:
                print(f"! Error adding metadata: {e}")
    
    print("\n✅ Database migration complete!")
    print("\nNew columns added:")
    print("  - chapters_completed (tracks chapter progress during generation)")
    print("  - total_chapters (total chapters for the story)")
    print("  - theme (story theme/subject)")
    print("  - metadata (JSON field for chapter outlines and other metadata)")

if __name__ == "__main__":
    try:
        add_missing_columns()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nIf you see connection errors, make sure DATABASE_URL is set correctly.")
