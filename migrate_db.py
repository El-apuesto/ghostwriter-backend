"""
Database migration script to add new Story model fields
Run this once after updating models.py
"""
from database import engine
from sqlalchemy import text, inspect

def add_missing_columns():
    """Add new columns to stories table if they don't exist"""
    
    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('stories')]
    
    with engine.connect() as conn:
        # Add chapters_completed
        if 'chapters_completed' not in existing_columns:
            try:
                conn.execute(text("ALTER TABLE stories ADD COLUMN chapters_completed INTEGER DEFAULT 0"))
                conn.commit()
                print("✓ Added chapters_completed")
            except Exception as e:
                print(f"chapters_completed: {e}")
        else:
            print("chapters_completed already exists")
        
        # Add total_chapters
        if 'total_chapters' not in existing_columns:
            try:
                conn.execute(text("ALTER TABLE stories ADD COLUMN total_chapters INTEGER DEFAULT 0"))
                conn.commit()
                print("✓ Added total_chapters")
            except Exception as e:
                print(f"total_chapters: {e}")
        else:
            print("total_chapters already exists")
        
        # Add theme
        if 'theme' not in existing_columns:
            try:
                conn.execute(text("ALTER TABLE stories ADD COLUMN theme TEXT"))
                conn.commit()
                print("✓ Added theme")
            except Exception as e:
                print(f"theme: {e}")
        else:
            print("theme already exists")
        
        # Add metadata
        if 'metadata' not in existing_columns:
            try:
                conn.execute(text("ALTER TABLE stories ADD COLUMN metadata JSON"))
                conn.commit()
                print("✓ Added metadata")
            except Exception as e:
                print(f"metadata: {e}")
        else:
            print("metadata already exists")

if __name__ == "__main__":
    print("Starting database migration...")
    add_missing_columns()
    print("\n✅ Database migration complete!")
