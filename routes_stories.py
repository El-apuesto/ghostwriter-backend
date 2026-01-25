"""
Story routes for generating and managing stories
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from auth import get_current_user
from models import User, Story
from schemas import StoryCreateRequest, StoryResponse
from story_generation import generate_story, create_story_record

router = APIRouter(prefix="/api/stories", tags=["stories"])


@router.post("/generate", response_model=StoryResponse)
async def create_story(
    request: StoryCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new story
    
    Creates a story record and starts generation in the background.
    Returns immediately with story ID and pending status.
    """
    try:
        # Create story record
        story_data = {
            'user_id': current_user.id,
            'title': request.title,
            'genre': request.genre,
            'theme': request.theme,
            'characters': request.characters,
            'setting': request.setting,
            'length': request.length
        }
        
        story = create_story_record(db, story_data)
        
        # Start generation in background
        background_tasks.add_task(
            generate_story,
            db,
            story.id,
            request.genre,
            request.theme,
            request.characters,
            request.setting,
            request.length
        )
        
        return story.to_dict()
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create story: {str(e)}"
        )


@router.get("/", response_model=List[StoryResponse])
async def get_my_stories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Get user's story library
    
    Returns all stories for the current user, ordered by most recent.
    """
    stories = db.query(Story).filter(
        Story.user_id == current_user.id
    ).order_by(Story.created_at.desc()).offset(offset).limit(limit).all()
    
    return [story.to_dict() for story in stories]


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific story details
    
    Returns full story content including generated text.
    """
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=404,
            detail="Story not found or you don't have permission to access it"
        )
    
    return story.to_dict()


@router.delete("/{story_id}")
async def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a story
    
    Permanently removes a story from the database.
    """
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(
            status_code=404,
            detail="Story not found or you don't have permission to delete it"
        )
    
    db.delete(story)
    db.commit()
    
    return {
        "success": True,
        "message": f"Story '{story.title}' has been banished to the void"
    }
