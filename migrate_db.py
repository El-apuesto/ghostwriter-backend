"""
Database migration script - adds new fields to Story model
Run this before starting the app or make it part of startup
"""
from database import engine
from sqlalchemy import text, inspect
import sys

def column_exists(table_name: str, column_name: str) -> bool:
    """Check if column exists in table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_missing_columns():
    """Add new columns to stories table if they don't exist"""
    migrations = [
        {
            'column': 'chapters_completed',
            'sql': 'ALTER TABLE stories ADD COLUMN chapters_completed INTEGER DEFAULT 0'
        },
        {
            'column': 'total_chapters',
            'sql': 'ALTER TABLE stories ADD COLUMN total_chapters INTEGER DEFAULT 0'
        },
        {
            'column': 'theme',
            'sql': 'ALTER TABLE stories ADD COLUMN theme TEXT'
        },
        {
            'column': 'metadata',
            'sql': 'ALTER TABLE stories ADD COLUMN metadata JSON'
        },
    ]
    
    with engine.connect() as conn:
        for migration in migrations:
            column_name = migration['column']
            
            if column_exists('stories', column_name):
                print(f"✓ Column '{column_name}' already exists")
                continue
            
            try:
                conn.execute(text(migration['sql']))
                conn.commit()
                print(f"✓ Added column '{column_name}'")
            except Exception as e:
                print(f"✗ Error adding '{column_name}': {e}")
                conn.rollback()
                # Don't fail completely, continue with other migrations
    
    print("\n✅ Database migration complete!")

if __name__ == "__main__":
    try:
        add_missing_columns()
        sys.exit(0)  # Success
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)  # Failure
