"""
Database migration script to add new fields to Story model

Run this on Render after deploying updated models.py:
  python migrate_db.py
"""
from database import engine
from sqlalchemy import text, inspect

def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_missing_columns():
    """Add missing columns to stories table"""
    print("Starting database migration...\n")
    
    migrations = [
        {
            'column': 'chapters_completed',
            'sql': 'ALTER TABLE stories ADD COLUMN chapters_completed INTEGER DEFAULT 0',
            'description': 'Track completed chapters during generation'
        },
        {
            'column': 'total_chapters',
            'sql': 'ALTER TABLE stories ADD COLUMN total_chapters INTEGER DEFAULT 0',
            'description': 'Track total chapters for story'
        },
        {
            'column': 'theme',
            'sql': 'ALTER TABLE stories ADD COLUMN theme TEXT',
            'description': 'Store story theme/premise'
        },
        {
            'column': 'metadata',
            'sql': 'ALTER TABLE stories ADD COLUMN metadata JSON',
            'description': 'Store chapter outlines and other metadata'
        },
    ]
    
    with engine.connect() as conn:
        for migration in migrations:
            column = migration['column']
            
            if check_column_exists('stories', column):
                print(f"✓ {column} already exists - skipping")
            else:
                try:
                    conn.execute(text(migration['sql']))
                    conn.commit()
                    print(f"✓ Added {column}: {migration['description']}")
                except Exception as e:
                    print(f"✗ Failed to add {column}: {str(e)}")
    
    print("\n✅ Database migration complete!")
    print("\nYour Story model now supports:")
    print("  - Chapter-by-chapter progress tracking")
    print("  - Story themes")
    print("  - Metadata storage for chapter outlines")
    print("\nYou can now generate full-length novels with real-time progress updates!")

if __name__ == "__main__":
    add_missing_columns()
