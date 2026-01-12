import json
import logging
from datetime import datetime
from typing import Dict
from sqlalchemy.orm import Session

from config import settings, CREDIT_COSTS
from models import User, Story, Transaction
from schemas import FictionRequest, BiographyRequest, FictionLength, BiographyLength
from llm_client import llm, GHOSTWRITER_FICTION, GHOSTWRITER_BIOGRAPHY

logger = logging.getLogger(__name__)

# ===== FICTION GENERATION =====

def generate_fiction_story(request: FictionRequest, user: User, db: Session) -> Dict:
    """Generate fiction story with credit check"""
    
    # Determine credit cost
    cost_key = f"fiction_{request.story_length.value}"
    credit_cost = CREDIT_COSTS.get(cost_key, 0)
    
    # Check if user has enough credits (skip for free samples)
    if credit_cost > 0 and user.credits_balance < credit_cost:
        raise Exception(f"Insufficient credits. Need {credit_cost}, have {user.credits_balance}")
    
    # Word count targets
    word_counts = {
        FictionLength.SAMPLE: 1500,
        FictionLength.NOVELLA: 30000,
        FictionLength.NOVEL: 100000
    }
    target_words = word_counts[request.story_length]
    
    logger.info(f"Generating {request.story_length.value}: {request.premise[:50]}...")
    
    # Create story record
    story = Story(
        user_id=user.id,
        user_email=user.email,
        story_type="fiction",
        title=request.title or "Untitled Story",
        length_type=request.story_length.value,
        generation_status="generating",
        credits_cost=credit_cost,
        metadata=json.dumps({
            "premise": request.premise,
            "style": request.style.value if request.style else "sarcastic_deadpan",
            "genre": request.genre.value if request.genre else None,
            "setting": request.setting,
            "themes": request.themes
        })
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    
    try:
        # STEP 1: Generate outline using Llama 70B
        outline_prompt = f"""Create a detailed story outline for:

PREMISE: {request.premise}

TARGET LENGTH: {target_words} words
WRITING STYLE: {request.style.value if request.style else 'sarcastic_deadpan'}
GENRE: {request.genre.value if request.genre else 'dark comedy/thriller'}
SETTING: {request.setting or 'Choose atmospheric, engaging setting'}
{f'THEMES: {", ".join(request.themes)}' if request.themes else ''}
{f'EMULATE: {request.emulate_author}' if request.emulate_author else ''}

Generate a JSON outline with:
{{
  "title": "compelling title",
  "chapters": [
    {{"number": 1, "title": "chapter title", "synopsis": "what happens", "word_count": 3000}}
  ],
  "characters": ["main characters"],
  "themes": ["core themes"]
}}

Make it {request.tone or 'darkly humorous, suspenseful, and engaging'}."""
        
        outline_text = llm.generate(outline_prompt, GHOSTWRITER_FICTION, "llama-3.3-70b-versatile")
        
        # Parse outline
        try:
            outline = json.loads(outline_text)
        except:
            # Fallback if JSON parsing fails
            outline = {
                "title": request.title or "Untitled Story",
                "chapters": [{"number": 1, "title": "Chapter 1", "synopsis": request.premise, "word_count": target_words}],
                "themes": request.themes or []
            }
        
        story.title = outline.get("title", request.title or "Untitled Story")
        
        # STEP 2: Generate chapters
        max_chapters = 2 if request.story_length == FictionLength.SAMPLE else len(outline.get("chapters", []))
        chapters = []
        context = ""
        
        for i, chapter_spec in enumerate(outline.get("chapters", [])[:max_chapters]):
            logger.info(f"Generating chapter {i+1}/{max_chapters}")
            
            words_per_chapter = target_words // max_chapters
            
            chapter_prompt = f"""Write Chapter {chapter_spec.get('number', i+1)}: {chapter_spec.get('title', f'Chapter {i+1}')}

SYNOPSIS: {chapter_spec.get('synopsis', '')}

PREVIOUS CONTEXT: {context[-2000:] if context else 'This is the beginning'}

WRITING REQUIREMENTS:
- Target: {words_per_chapter} words
- Style: {request.style.value if request.style else 'sarcastic_deadpan'} - witty, dark humor, sharp observations
- Tone: {request.tone or 'Suspenseful yet darkly funny'}
- Show don't tell
- Sharp dialogue
- Vivid descriptions
- Keep reader hooked

Write the full chapter now:"""
            
            chapter_content = llm.generate(chapter_prompt, GHOSTWRITER_FICTION, "llama-3.3-70b-versatile")
            
            chapters.append({
                "number": i + 1,
                "title": chapter_spec.get('title', f'Chapter {i+1}'),
                "content": chapter_content
            })
            
            context = chapter_content  # Use for next chapter
        
        # STEP 3: Save completed story
        story.content = json.dumps(chapters)
        story.generation_status = "complete"
        story.completed_at = datetime.utcnow()
        
        # Deduct credits (if not free sample)
        if credit_cost > 0:
            if not user.deduct_credits(credit_cost):
                raise Exception("Credit deduction failed")
            
            # Log transaction
            transaction = Transaction(
                user_id=user.id,
                transaction_type="story_generation",
                credits_amount=-credit_cost,
                description=f"Generated {request.story_length.value} fiction story",
                status="completed",
                story_id=story.id
            )
            db.add(transaction)
        
        db.commit()
        db.refresh(story)
        
        # Calculate word count
        word_count = sum(len(ch['content'].split()) for ch in chapters)
        
        return {
            "story_id": story.id,
            "title": story.title,
            "chapters": chapters,
            "word_count": word_count,
            "credits_used": credit_cost
        }
        
    except Exception as e:
        logger.error(f"Fiction generation failed: {str(e)}")
        story.generation_status = "error"
        db.commit()
        raise Exception(f"Story generation failed: {str(e)}")


# ===== BIOGRAPHY GENERATION =====

def generate_biography_story(request: BiographyRequest, user: User, db: Session) -> Dict:
    """Generate biography with credit check"""
    
    # Determine credit cost
    cost_key = f"biography_{request.story_length.value}"
    credit_cost = CREDIT_COSTS.get(cost_key, 0)
    
    # Check credits
    if credit_cost > 0 and user.credits_balance < credit_cost:
        raise Exception(f"Insufficient credits. Need {credit_cost}, have {user.credits_balance}")
    
    # Word count targets
    word_counts = {
        BiographyLength.SAMPLE: 2000,
        BiographyLength.SHORT_MEMOIR: 15000,
        BiographyLength.STANDARD_BIOGRAPHY: 40000,
        BiographyLength.COMPREHENSIVE: 80000
    }
    target_words = word_counts[request.story_length]
    
    logger.info(f"Generating {request.story_length.value}: {request.subject_names}")
    
    # Create story record
    story = Story(
        user_id=user.id,
        user_email=user.email,
        story_type="biography",
        title=f"The Life of {request.subject_names}",
        length_type=request.story_length.value,
        generation_status="generating",
        credits_cost=credit_cost,
        metadata=json.dumps({
            "subject": request.subject_names,
            "type": request.biography_type.value,
            "time_period": f"{request.time_period_start} - {request.time_period_end}",
            "narrative_voice": request.narrative_voice.value if request.narrative_voice else "third_person_limited"
        })
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    
    try:
        # Build detailed biography prompt
        details = []
        if request.birth_details:
            details.append(f"BIRTH: {json.dumps(request.birth_details)}")
        if request.family_background:
            details.append(f"FAMILY: {json.dumps(request.family_background)}")
        if request.childhood:
            details.append(f"CHILDHOOD: {json.dumps(request.childhood)}")
        if request.career:
            details.append(f"CAREER: {json.dumps(request.career)}")
        if request.relationships:
            details.append(f"RELATIONSHIPS: {json.dumps(request.relationships)}")
        if request.major_events:
            details.append(f"MAJOR EVENTS: {json.dumps([e.dict() for e in request.major_events])}")
        if request.personality:
            details.append(f"PERSONALITY: {json.dumps(request.personality)}")
        if request.achievements:
            details.append(f"ACHIEVEMENTS: {json.dumps(request.achievements)}")
        
        bio_prompt = f"""Write a compelling {request.biography_type.value} about:

SUBJECT: {request.subject_names}
TIME PERIOD: {request.time_period_start} to {request.time_period_end}
TARGET LENGTH: {target_words} words
NARRATIVE VOICE: {request.narrative_voice.value if request.narrative_voice else 'third_person_limited'}
TONE: {request.tone or 'balanced, respectful, engaging'}
WRITING STYLE: {request.writing_style or 'chronological'}

DETAILS PROVIDED:
{'\n'.join(details) if details else 'Limited information - create plausible, historically accurate details based on context'}

{f'FOCUS AREAS: {", ".join(request.focus_areas)}' if request.focus_areas else ''}
{f'THEMES: {", ".join(request.themes)}' if request.themes else ''}

INSTRUCTIONS:
- Create a compelling, human life story
- Fill in missing details with historically accurate, contextually appropriate content
- Structure in chapters covering different life periods
- Make it engaging and emotionally resonant
- Show character growth and transformation
- Include vivid scenes and anecdotes
- Balance facts with storytelling

Write the complete {request.biography_type.value} now:"""
        
        content = llm.generate(bio_prompt, GHOSTWRITER_BIOGRAPHY, "llama-3.3-70b-versatile")
        
        # Save completed biography
        story.content = content
        story.generation_status = "complete"
        story.completed_at = datetime.utcnow()
        
        # Deduct credits
        if credit_cost > 0:
            if not user.deduct_credits(credit_cost):
                raise Exception("Credit deduction failed")
            
            transaction = Transaction(
                user_id=user.id,
                transaction_type="story_generation",
                credits_amount=-credit_cost,
                description=f"Generated {request.story_length.value} biography",
                status="completed",
                story_id=story.id
            )
            db.add(transaction)
        
        db.commit()
        db.refresh(story)
        
        word_count = len(content.split())
        
        return {
            "story_id": story.id,
            "title": story.title,
            "content": content,
            "word_count": word_count,
            "credits_used": credit_cost
        }
        
    except Exception as e:
        logger.error(f"Biography generation failed: {str(e)}")
        story.generation_status = "error"
        db.commit()
        raise Exception(f"Biography generation failed: {str(e)}")
