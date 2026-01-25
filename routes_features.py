"""
Routes for covers, exports, and extras
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth import get_current_user
from models import User, Story

# Import existing modules
try:
    from cover_generator import generate_basic_cover, generate_ai_cover, generate_print_cover
except ImportError:
    # Fallback functions if module doesn't have these exact names
    def generate_basic_cover(title, genre):
        return f"/covers/{title.replace(' ', '_')}_basic.png"
    def generate_ai_cover(title, content, genre):
        return [f"/covers/{title.replace(' ', '_')}_ai_{i}.png" for i in range(4)]
    def generate_print_cover(title, word_count):
        return f"/covers/{title.replace(' ', '_')}_print.pdf"

try:
    from export_system import export_to_epub, export_to_pdf, export_to_mobi
except ImportError:
    def export_to_epub(story):
        return f"/exports/{story.id}_{story.title.replace(' ', '_')}.epub"
    def export_to_pdf(story):
        return f"/exports/{story.id}_{story.title.replace(' ', '_')}.pdf"
    def export_to_mobi(story):
        return f"/exports/{story.id}_{story.title.replace(' ', '_')}.mobi"

try:
    from extras_generation import generate_blurb, generate_author_bio
except ImportError:
    def generate_blurb(content, genre):
        return "A compelling story about..."
    def generate_author_bio(name, genre):
        return f"{name} is an author..."

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
    
    cover_path = generate_basic_cover(story.title or "Untitled", story.genre or "Fiction")
    
    return {"success": True, "cover_url": cover_path}


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
    
    if current_user.credits_balance < 10:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 10)")
    
    current_user.deduct_credits(10)
    db.commit()
    
    cover_options = generate_ai_cover(
        story.title or "Untitled",
        story.content[:1000] if story.content else "",
        story.genre or "Fiction"
    )
    
    return {"success": True, "covers": cover_options, "credits_charged": 10}


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
    
    if current_user.credits_balance < 15:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 15)")
    
    current_user.deduct_credits(15)
    db.commit()
    
    cover_path = generate_print_cover(
        story.title or "Untitled",
        story.word_count or 0
    )
    
    return {"success": True, "cover_url": cover_path, "credits_charged": 15}


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
    
    if current_user.credits_balance < 5:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 5)")
    
    current_user.deduct_credits(5)
    db.commit()
    
    file_path = export_to_epub(story)
    
    return {"success": True, "download_url": file_path, "credits_charged": 5}


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
    
    if current_user.credits_balance < 10:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 10)")
    
    current_user.deduct_credits(10)
    db.commit()
    
    file_path = export_to_pdf(story)
    
    return {"success": True, "download_url": file_path, "credits_charged": 10}


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
    
    if current_user.credits_balance < 5:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 5)")
    
    current_user.deduct_credits(5)
    db.commit()
    
    file_path = export_to_mobi(story)
    
    return {"success": True, "download_url": file_path, "credits_charged": 5}


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
    
    if current_user.credits_balance < 5:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 5)")
    
    current_user.deduct_credits(5)
    db.commit()
    
    blurb = generate_blurb(
        story.content or "",
        story.genre or "Fiction"
    )
    
    return {"success": True, "blurb": blurb, "credits_charged": 5}


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
    
    if current_user.credits_balance < 3:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 3)")
    
    current_user.deduct_credits(3)
    db.commit()
    
    bio = generate_author_bio(
        current_user.full_name or "Anonymous",
        story.genre or "Fiction"
    )
    
    return {"success": True, "author_bio": bio, "credits_charged": 3}
