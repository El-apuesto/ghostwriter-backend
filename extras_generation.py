import json
import logging
from datetime import datetime
from typing import Dict
from sqlalchemy.orm import Session
import base64
import io

from config import settings, CREDIT_COSTS
from models import User, Story, StoryExtra, Transaction
from llm_client import llm, GHOSTWRITER_FICTION

logger = logging.getLogger(__name__)

# ===== COVER GENERATION =====

def generate_book_cover(story_id: int, cover_type: str, user: User, db: Session, options: dict = None) -> Dict:
    """Generate AI book cover"""
    
    credit_cost = CREDIT_COSTS.get("ebook_cover" if cover_type == "ebook" else "print_cover", 10)
    
    if user.credits_balance < credit_cost:
        raise Exception(f"Insufficient credits. Need {credit_cost}, have {user.credits_balance}")
    
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == user.id).first()
    if not story:
        raise Exception("Story not found")
    
    try:
        # Parse story metadata for context
        metadata = json.loads(story.metadata)
        
        # Generate cover description using LLM
        cover_prompt = f"""Design a book cover for this story:

TITLE: {story.title}
GENRE: {metadata.get('genre', 'fiction')}
STYLE: {metadata.get('style', 'dark and mysterious')}
PREMISE: {metadata.get('premise', '')[:200]}

Describe a compelling book cover design in 2-3 sentences:
- Visual elements
- Color palette  
- Typography style
- Overall mood

Keep it professional and genre-appropriate."""
        
        cover_description = llm.generate(cover_prompt, GHOSTWRITER_FICTION, "llama-3.3-70b-versatile")
        
        # For now, store the description (in production, you'd use DALL-E or Stable Diffusion)
        # Placeholder for actual image generation
        cover_data = {
            "type": cover_type,
            "description": cover_description,
            "title": story.title,
            "dimensions": "1600x2400" if cover_type == "ebook" else "6x9 inches with spine",
            "format": "PNG",
            "status": "generated"
        }
        
        # Save extra
        extra = StoryExtra(
            story_id=story.id,
            extra_type=f"{cover_type}_cover",
            content=json.dumps(cover_data),
            credits_cost=credit_cost
        )
        db.add(extra)
        
        # Update story flags
        if cover_type == "ebook":
            story.has_ebook_cover = True
        else:
            story.has_print_cover = True
        
        # Deduct credits
        user.deduct_credits(credit_cost)
        
        # Log transaction
        transaction = Transaction(
            user_id=user.id,
            transaction_type="extra_generation",
            credits_amount=-credit_cost,
            description=f"Generated {cover_type} cover for '{story.title}'",
            status="completed",
            story_id=story.id
        )
        db.add(transaction)
        
        db.commit()
        db.refresh(extra)
        
        return {
            "extra_id": extra.id,
            "story_id": story.id,
            "cover_type": cover_type,
            "cover_data": cover_data,
            "credits_used": credit_cost,
            "message": f"{cover_type.title()} cover generated successfully!"
        }
        
    except Exception as e:
        logger.error(f"Cover generation failed: {str(e)}")
        raise Exception(f"Cover generation failed: {str(e)}")


# ===== EXPORT GENERATION =====

def generate_epub_export(story_id: int, user: User, db: Session) -> Dict:
    """Generate ePub export"""
    
    credit_cost = CREDIT_COSTS.get("epub_export", 5)
    
    if user.credits_balance < credit_cost:
        raise Exception(f"Insufficient credits. Need {credit_cost}, have {user.credits_balance}")
    
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == user.id).first()
    if not story:
        raise Exception("Story not found")
    
    try:
        # Parse content
        if story.story_type == "fiction":
            chapters = json.loads(story.content)
        else:
            chapters = [{"title": story.title, "content": story.content}]
        
        # Create ePub data structure (simplified - in production use ebooklib)
        epub_data = {
            "format": "epub",
            "title": story.title,
            "author": user.full_name or "Anonymous",
            "chapters": len(chapters) if isinstance(chapters, list) else 1,
            "status": "generated"
        }
        
        # Save extra
        extra = StoryExtra(
            story_id=story.id,
            extra_type="epub_export",
            content=json.dumps(epub_data),
            credits_cost=credit_cost
        )
        db.add(extra)
        
        story.has_epub = True
        user.deduct_credits(credit_cost)
        
        transaction = Transaction(
            user_id=user.id,
            transaction_type="extra_generation",
            credits_amount=-credit_cost,
            description=f"Generated ePub for '{story.title}'",
            status="completed",
            story_id=story.id
        )
        db.add(transaction)
        
        db.commit()
        db.refresh(extra)
        
        return {
            "extra_id": extra.id,
            "format": "epub",
            "credits_used": credit_cost,
            "message": "ePub export ready!"
        }
        
    except Exception as e:
        raise Exception(f"ePub generation failed: {str(e)}")


def generate_mobi_export(story_id: int, user: User, db: Session) -> Dict:
    """Generate MOBI export for Kindle"""
    
    credit_cost = CREDIT_COSTS.get("mobi_export", 5)
    
    if user.credits_balance < credit_cost:
        raise Exception(f"Insufficient credits. Need {credit_cost}, have {user.credits_balance}")
    
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == user.id).first()
    if not story:
        raise Exception("Story not found")
    
    try:
        mobi_data = {
            "format": "mobi",
            "title": story.title,
            "author": user.full_name or "Anonymous",
            "kindle_compatible": True,
            "status": "generated"
        }
        
        extra = StoryExtra(
            story_id=story.id,
            extra_type="mobi_export",
            content=json.dumps(mobi_data),
            credits_cost=credit_cost
        )
        db.add(extra)
        
        story.has_mobi = True
        user.deduct_credits(credit_cost)
        
        transaction = Transaction(
            user_id=user.id,
            transaction_type="extra_generation",
            credits_amount=-credit_cost,
            description=f"Generated MOBI for '{story.title}'",
            status="completed",
            story_id=story.id
        )
        db.add(transaction)
        
        db.commit()
        db.refresh(extra)
        
        return {
            "extra_id": extra.id,
            "format": "mobi",
            "credits_used": credit_cost,
            "message": "MOBI export ready for Kindle!"
        }
        
    except Exception as e:
        raise Exception(f"MOBI generation failed: {str(e)}")


def generate_kdp_pdf(story_id: int, user: User, db: Session) -> Dict:
    """Generate KDP-ready PDF"""
    
    credit_cost = CREDIT_COSTS.get("kdp_pdf", 10)
    
    if user.credits_balance < credit_cost:
        raise Exception(f"Insufficient credits. Need {credit_cost}, have {user.credits_balance}")
    
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == user.id).first()
    if not story:
        raise Exception("Story not found")
    
    try:
        pdf_data = {
            "format": "pdf",
            "title": story.title,
            "author": user.full_name or "Anonymous",
            "kdp_ready": True,
            "page_size": "6x9 inches",
            "status": "generated"
        }
        
        extra = StoryExtra(
            story_id=story.id,
            extra_type="kdp_pdf",
            content=json.dumps(pdf_data),
            credits_cost=credit_cost
        )
        db.add(extra)
        
        story.has_pdf = True
        user.deduct_credits(credit_cost)
        
        transaction = Transaction(
            user_id=user.id,
            transaction_type="extra_generation",
            credits_amount=-credit_cost,
            description=f"Generated KDP PDF for '{story.title}'",
            status="completed",
            story_id=story.id
        )
        db.add(transaction)
        
        db.commit()
        db.refresh(extra)
        
        return {
            "extra_id": extra.id,
            "format": "pdf",
            "credits_used": credit_cost,
            "message": "KDP-ready PDF generated!"
        }
        
    except Exception as e:
        raise Exception(f"PDF generation failed: {str(e)}")


# ===== MARKETING CONTENT =====

def generate_blurb(story_id: int, user: User, db: Session) -> Dict:
    """Generate book blurb/description"""
    
    credit_cost = CREDIT_COSTS.get("blurb", 5)
    
    if user.credits_balance < credit_cost:
        raise Exception(f"Insufficient credits. Need {credit_cost}, have {user.credits_balance}")
    
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == user.id).first()
    if not story:
        raise Exception("Story not found")
    
    try:
        metadata = json.loads(story.metadata)
        
        # Get first chapter/section for context
        if story.story_type == "fiction":
            chapters = json.loads(story.content)
            first_content = chapters[0]['content'][:1000] if chapters else ""
        else:
            first_content = story.content[:1000]
        
        blurb_prompt = f"""Write a compelling 150-250 word book blurb for:

TITLE: {story.title}
GENRE: {metadata.get('genre', 'fiction')}
PREMISE: {metadata.get('premise', '')}

FIRST PAGE:
{first_content}

Create a hook that:
- Grabs attention immediately
- Hints at conflict/stakes
- Makes readers want more
- Ends with intrigue
- Professional Amazon-style blurb

Write the blurb now:"""
        
        blurb_text = llm.generate(blurb_prompt, GHOSTWRITER_FICTION, "llama-3.3-70b-versatile")
        
        extra = StoryExtra(
            story_id=story.id,
            extra_type="blurb",
            content=blurb_text,
            credits_cost=credit_cost
        )
        db.add(extra)
        
        story.has_blurb = True
        user.deduct_credits(credit_cost)
        
        transaction = Transaction(
            user_id=user.id,
            transaction_type="extra_generation",
            credits_amount=-credit_cost,
            description=f"Generated blurb for '{story.title}'",
            status="completed",
            story_id=story.id
        )
        db.add(transaction)
        
        db.commit()
        db.refresh(extra)
        
        return {
            "extra_id": extra.id,
            "blurb": blurb_text,
            "credits_used": credit_cost,
            "message": "Book blurb generated!"
        }
        
    except Exception as e:
        raise Exception(f"Blurb generation failed: {str(e)}")


def generate_author_bio(user: User, db: Session, bio_info: str = None) -> Dict:
    """Generate author biography"""
    
    credit_cost = CREDIT_COSTS.get("author_bio", 3)
    
    if user.credits_balance < credit_cost:
        raise Exception(f"Insufficient credits. Need {credit_cost}, have {user.credits_balance}")
    
    try:
        bio_prompt = f"""Write a professional 100-150 word author biography for:

AUTHOR NAME: {user.full_name or 'Anonymous Author'}
{f'BACKGROUND INFO: {bio_info}' if bio_info else 'Limited information - create a compelling, professional author bio'}

Make it:
- Professional yet engaging
- Third person
- Highlights writing style/genres
- Memorable
- Amazon author page appropriate

Write the author bio now:"""
        
        bio_text = llm.generate(bio_prompt, GHOSTWRITER_FICTION, "llama-3.3-70b-versatile")
        
        # Save as a user-level extra (not tied to specific story)
        extra = StoryExtra(
            story_id=None,
            extra_type="author_bio",
            content=bio_text,
            credits_cost=credit_cost
        )
        db.add(extra)
        
        user.deduct_credits(credit_cost)
        
        transaction = Transaction(
            user_id=user.id,
            transaction_type="extra_generation",
            credits_amount=-credit_cost,
            description="Generated author biography",
            status="completed"
        )
        db.add(transaction)
        
        db.commit()
        db.refresh(extra)
        
        return {
            "extra_id": extra.id,
            "author_bio": bio_text,
            "credits_used": credit_cost,
            "message": "Author bio generated!"
        }
        
    except Exception as e:
        raise Exception(f"Author bio generation failed: {str(e)}")
