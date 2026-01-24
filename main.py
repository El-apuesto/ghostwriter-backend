"""
Story generation routes for FastAPI - Add these to your main.py
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models import Story
from story_generation import generate_story, create_story_record

# Create router
router = APIRouter(prefix="/api/stories", tags=["stories"])

# Pydantic models for request/response
class StoryCreate(BaseModel):
    genre: str
    theme: str
    characters: Optional[str] = None
    setting: Optional[str] = None
    length: Optional[str] = 'short'

class StoryResponse(BaseModel):
    id: int
    title: Optional[str]
    genre: str
    theme: str
    characters: Optional[str]
    setting: Optional[str]
    length: str
    content: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[StoryResponse])
async def get_stories(db: Session = Depends(get_db)):
    """Get all stories"""
    try:
        stories = db.query(Story).order_by(Story.created_at.desc()).all()
        return [story.to_dict() for story in stories]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(story_id: int, db: Session = Depends(get_db)):
    """Get a single story by ID"""
    try:
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        return story.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=StoryResponse, status_code=201)
async def create_story(
    story_data: StoryCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new story and start generation in background"""
    try:
        # Create story record immediately
        story = create_story_record(db, story_data.dict())
        
        # Start story generation in background
        background_tasks.add_task(
            generate_story_task,
            story.id,
            story_data.genre,
            story_data.theme,
            story_data.characters,
            story_data.setting,
            story_data.length
        )
        
        # Return the story record immediately with ID
        return story.to_dict()
        
    except Exception as e:
        print(f"Error in create_story: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{story_id}")
async def delete_story(story_id: int, db: Session = Depends(get_db)):
    """Delete a story"""
    try:
        story = db.query(Story).filter(Story.id == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        db.delete(story)
        db.commit()
        return {"message": "Story deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def generate_story_task(story_id: int, genre: str, theme: str, 
                       characters: str, setting: str, length: str):
    """
    Background task to generate story.
    Creates its own database session.
    """
    from database import SessionLocal
    db = SessionLocal()
    try:
        generate_story(db, story_id, genre, theme, characters, setting, length)
    except Exception as e:
        print(f"Background task error: {str(e)}")
    finally:
        db.close()


# To use this in your main.py:
# from story_routes import router as story_router
# app.include_router(story_router)
