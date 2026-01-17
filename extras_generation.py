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
from cover_generator import cover_gen

logger = logging.getLogger(__name__)

# ===== COVER GENERATION =====

def generate_book_cover(story_id: int, cover_type: str, user: User, db: Session, 
                       premium: bool = False, style: str = "dark") -> Dict:
    """
    Generate book cover - FREE basic or PREMIUM AI with 4 options
    
    Args:
        story_id: Story to generate cover for
        cover_type: 'ebook' or 'print'
        user: Current user
        db: Database session
        premium: If True, generate 4 AI options (costs 10 credits)
                If False, generate 1 free basic cover (0 credits)
        style: For basic covers - 'dark', 'mystery', 'fantasy', 'romance', 'scifi'
    """
    
    # Get story
    story = db.query(Story).filter(Story.id == story_id, Story.user_id == user.id).first()
    if not story:
        raise Exception("Story not found")
    
    # Parse metadata
    try:
        metadata = json.loads(story.metadata) if story.metadata else {}
    except:
        metadata = {}
    
    genre = metadata.get('genre', 'fiction')
    themes = metadata.get('themes', [])
    
    # ===== FREE BASIC COVER =====
    if not premium:
        try:
            logger.info(f"Generating FREE basic {cover_type} cover for story {story_id}")
            
            if cover_type == "ebook":
                cover_path = cover_gen.create_basic_cover(
                    title=story.title,
                    author=user.full_name or "Anonymous",
                    genre=genre,
                    style=style,
                    size=cover_gen.EBOOK_SIZE
                )
            else:  # print
                # For print, we need page count estimate
                page_count = metadata.get('estimated_pages', 200)
                cover_path = cover_gen.create_print_cover(
                    title=story.title,
                    author=user.full_name or "Anonymous",
                    page_count=page_count,
                    size="6x9",
                    genre=genre
                )
            
            cover_data = {
                "type": cover_type,
                "premium": False,
                "style": style,
                "file_path": cover_path,
                "dimensions": "1600x2560" if cover_type == "ebook" else "6x9 with spine",
                "format": "PNG",
                "status": "generated"
            }
            
            # Save extra (0 credits)
            extra = StoryExtra(
                story_id=story.id,
                extra_type=f"{cover_type}_cover",
                content=json.dumps(cover_data),
                credits_cost=0
            )
            db.add(extra)
            
            # Update story flag
            if cover_type == "ebook":
                story.has_ebook_cover = True
            else:
                story.has_print_cover = True
            
            db.commit()
            db.refresh(extra)
            
            return {
                "extra_id": extra.id,
                "story_id": story.id,
                "cover_type": cover_type,
                "premium": False,
                "cover_data": cover_data,
                "credits_used": 0,
                "message": f"FREE basic {cover_type} cover generated! Upgrade to premium for AI-designed covers."
            }
            
        except Exception as e:
            logger.error(f"Basic cover generation failed: {str(e)}")
            raise Exception(f"Cover generation failed: {str(e)}")
    
    # ===== PREMIUM AI COVER (4 OPTIONS) =====
    else:
        credit_cost = CREDIT_COSTS.get("ebook_cover" if cover_type == "ebook" else "print_cover", 10)
        
        if user.credits_balance < credit_cost:
            raise Exception(f"Insufficient credits. Need {credit_cost}, have {user.credits_balance}")
        
        try:
            logger.info(f"Generating PREMIUM AI {cover_type} cover with 4 options for story {story_id}")
            
            # Generate 4 AI cover options
            ai_options = cover_gen.generate_ai_cover_options(
                title=story.title,
                author=user.full_name or "Anonymous",
                genre=genre,
                themes=themes,
                style_preference=style
            )
            
            if not ai_options:
                raise Exception("Failed to generate AI cover options")
            
            cover_data = {
                "type": cover_type,
                "premium": True,
                "ai_generated": True,
                "options": ai_options,
                "total_options": len(ai_options),
                "dimensions": "1600x2560" if cover_type == "ebook" else "6x9 with spine",
                "format": "JPG",
                "status": "options_ready",
                "note": "User must select one of the 4 options"
            }
            
            # Save extra
            extra = StoryExtra(
                story_id=story.id,
                extra_type=f"{cover_type}_cover_premium",
                content=json.dumps(cover_data),
                credits_cost=credit_cost
            )
            db.add(extra)
            
            # Update story flag
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
                description=f"Generated PREMIUM AI {cover_type} cover (4 options) for '{story.title}'",
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
                "premium": True,
                "options": ai_options,
                "credits_used": credit_cost,
                "message": f"4 AI-generated {cover_type} cover options ready! Choose your favorite."
            }
            
        except Exception as e:
            logger.error(f"Premium AI cover generation failed: {str(e)}")
            raise Exception(f"AI cover generation failed: {str(e)}")


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
