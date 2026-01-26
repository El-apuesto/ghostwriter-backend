"""
Routes for covers, exports, and extras
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth import get_current_user
from models import User, Story

# Import your existing modules
from cover_generator import generate_basic_cover, generate_ai_cover, generate_print_cover
from export_system import export_to_epub, export_to_pdf, export_to_mobi
from extras_generation import generate_blurb, generate_author_bio

router = APIRouter(prefix="/api", tags=["features"])


# COVER GENERATION
@router.post("/stories/{story_id}/cover/basic")
async def create_basic_cover(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate basic programmatic cover (free)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.status != 'completed':
        raise HTTPException(status_code=400, detail="Story must be completed first")
    
    try:
        # Generate cover using existing function
        cover_path = generate_basic_cover(story.title, story.genre or "Fiction")
        return {"success": True, "cover_url": cover_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cover generation failed: {str(e)}")


@router.post("/stories/{story_id}/cover/ai")
async def create_ai_cover(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI cover with Grok-2 (10 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.status != 'completed':
        raise HTTPException(status_code=400, detail="Story must be completed first")
    
    # Check credits
    if current_user.credits_balance < 10:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 10)")
    
    try:
        # Deduct credits
        current_user.deduct_credits(10)
        db.commit()
        
        # Generate AI cover
        cover_options = generate_ai_cover(story.title, story.content[:1000], story.genre)
        
        return {"success": True, "covers": cover_options, "credits_charged": 10}
    except Exception as e:
        # Refund credits on failure
        current_user.add_credits(10)
        db.commit()
        raise HTTPException(status_code=500, detail=f"AI cover generation failed: {str(e)}")


@router.post("/stories/{story_id}/cover/print")
async def create_print_cover(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate print-ready cover with spine (15 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.status != 'completed':
        raise HTTPException(status_code=400, detail="Story must be completed first")
    
    # Check credits
    if current_user.credits_balance < 15:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 15)")
    
    try:
        # Deduct credits
        current_user.deduct_credits(15)
        db.commit()
        
        # Generate print cover
        cover_path = generate_print_cover(story.title, story.word_count)
        
        return {"success": True, "cover_url": cover_path, "credits_charged": 15}
    except Exception as e:
        # Refund credits on failure
        current_user.add_credits(15)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Print cover generation failed: {str(e)}")


# EXPORTS
@router.post("/stories/{story_id}/export/epub")
async def export_epub(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export to EPUB (5 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.status != 'completed':
        raise HTTPException(status_code=400, detail="Story must be completed first")
    
    if current_user.credits_balance < 5:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 5)")
    
    try:
        current_user.deduct_credits(5)
        db.commit()
        
        file_path = export_to_epub(story)
        
        return {"success": True, "download_url": file_path, "credits_charged": 5}
    except Exception as e:
        # Refund credits on failure
        current_user.add_credits(5)
        db.commit()
        raise HTTPException(status_code=500, detail=f"EPUB export failed: {str(e)}")


@router.post("/stories/{story_id}/export/pdf")
async def export_pdf(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export to PDF for KDP (10 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.status != 'completed':
        raise HTTPException(status_code=400, detail="Story must be completed first")
    
    if current_user.credits_balance < 10:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 10)")
    
    try:
        current_user.deduct_credits(10)
        db.commit()
        
        file_path = export_to_pdf(story)
        
        return {"success": True, "download_url": file_path, "credits_charged": 10}
    except Exception as e:
        # Refund credits on failure
        current_user.add_credits(10)
        db.commit()
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


@router.post("/stories/{story_id}/export/mobi")
async def export_mobi(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export to MOBI (5 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.status != 'completed':
        raise HTTPException(status_code=400, detail="Story must be completed first")
    
    if current_user.credits_balance < 5:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 5)")
    
    try:
        current_user.deduct_credits(5)
        db.commit()
        
        file_path = export_to_mobi(story)
        
        return {"success": True, "download_url": file_path, "credits_charged": 5}
    except Exception as e:
        # Refund credits on failure
        current_user.add_credits(5)
        db.commit()
        raise HTTPException(status_code=500, detail=f"MOBI export failed: {str(e)}")


# EXTRAS
@router.post("/stories/{story_id}/blurb")
async def create_blurb(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate marketing blurb (5 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.status != 'completed':
        raise HTTPException(status_code=400, detail="Story must be completed first")
    
    if current_user.credits_balance < 5:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 5)")
    
    try:
        current_user.deduct_credits(5)
        db.commit()
        
        blurb = generate_blurb(story.content, story.genre)
        
        return {"success": True, "blurb": blurb, "credits_charged": 5}
    except Exception as e:
        # Refund credits on failure
        current_user.add_credits(5)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Blurb generation failed: {str(e)}")


@router.post("/stories/{story_id}/author-bio")
async def create_author_bio(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate author bio (3 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.status != 'completed':
        raise HTTPException(status_code=400, detail="Story must be completed first")
    
    if current_user.credits_balance < 3:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 3)")
    
    try:
        current_user.deduct_credits(3)
        db.commit()
        
        bio = generate_author_bio(current_user.full_name, story.genre)
        
        return {"success": True, "author_bio": bio, "credits_charged": 3}
    except Exception as e:
        # Refund credits on failure
        current_user.add_credits(3)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Author bio generation failed: {str(e)}")
