from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from auth import get_current_user
from models import User, Story
from schemas import (
    FictionRequest, BiographyRequest,
    StoryResponse, StoryDetail
)
from story_generation import generate_fiction_story, generate_biography_story

router = APIRouter()

def get_db():
    from main_new import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== STORY GENERATION ENDPOINTS =====

@router.post("/api/generate/fiction")
def create_fiction(
    request: FictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate fiction story (requires credits unless sample)"""
    
    try:
        result = generate_fiction_story(request, current_user, db)
        return {
            "success": True,
            "story": result,
            "message": f"Your {request.story_length.value} has been summoned from the void!",
            "credits_remaining": current_user.credits_balance
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/api/generate/biography")
def create_biography(
    request: BiographyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate biography (requires credits unless sample)"""
    
    try:
        result = generate_biography_story(request, current_user, db)
        return {
            "success": True,
            "story": result,
            "message": f"The life story of {request.subject_names} is ready!",
            "credits_remaining": current_user.credits_balance
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ===== STORY LIBRARY ENDPOINTS =====

@router.get("/api/stories", response_model=List[StoryResponse])
def get_my_stories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get user's story library"""
    
    stories = db.query(Story).filter(
        Story.user_id == current_user.id
    ).order_by(Story.created_at.desc()).offset(offset).limit(limit).all()
    
    return stories


@router.get("/api/stories/{story_id}", response_model=StoryDetail)
def get_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific story details"""
    
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(404, "Story not found or access denied")
    
    # Parse content
    if story.story_type == "fiction":
        try:
            content = json.loads(story.content)
        except:
            content = story.content
    else:
        content = story.content
    
    # Parse metadata
    try:
        metadata = json.loads(story.metadata)
    except:
        metadata = {}
    
    return {
        "id": story.id,
        "title": story.title,
        "story_type": story.story_type,
        "length_type": story.length_type,
        "content": content,
        "metadata": metadata,
        "credits_cost": story.credits_cost,
        "has_ebook_cover": story.has_ebook_cover,
        "has_print_cover": story.has_print_cover,
        "has_epub": story.has_epub,
        "has_mobi": story.has_mobi,
        "has_pdf": story.has_pdf,
        "has_blurb": story.has_blurb,
        "has_author_bio": story.has_author_bio,
        "created_at": story.created_at,
        "completed_at": story.completed_at
    }


@router.delete("/api/stories/{story_id}")
def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a story"""
    
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(404, "Story not found or access denied")
    
    db.delete(story)
    db.commit()
    
    return {"success": True, "message": "Story deleted successfully"}
