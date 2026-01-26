"""
Story routes for generating and managing stories
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from database import get_db
from auth import get_current_user
from models import User, Story
from schemas import StoryResponse
from story_generation import generate_story, create_story_record, generate_chapter_outline, generate_chapter

router = APIRouter(prefix="/api/stories", tags=["stories"])


@router.post("/generate", response_model=StoryResponse)
async def create_story(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new fiction story with enhanced creative controls
    
    Accepts:
    - premise (required): Story premise/theme
    - length (required): sample, novella, novel, epic
    - title (optional)
    - genre (optional)
    - setting (optional)
    - tone (optional)
    - writing_style (optional)
    - emulate_author (optional)
    - themes (optional): array of theme strings
    - characters (optional): array of character objects
    - timeline (optional): array of timeline event objects
    """
    try:
        # Extract and validate required fields
        theme = request.get('theme') or request.get('premise')
        if not theme:
            raise HTTPException(status_code=400, detail="Missing required field: theme or premise")
        
        length = request.get('length', 'sample')
        genre = request.get('genre', 'Fiction')
        
        # Credit costs
        credit_costs = {
            'sample': 0,
            'short': 0,
            'novella': 50,
            'novel': 100,
            'epic': 150
        }
        
        cost = credit_costs.get(length, 0)
        
        # Check credits
        if current_user.credits_balance < cost:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {cost}, you have {current_user.credits_balance}"
            )
        
        # Deduct credits if not free
        if cost > 0:
            current_user.deduct_credits(cost)
            db.commit()
        
        # Build enhanced theme with all optional fields
        enhanced_theme = theme
        
        if request.get('writing_style'):
            enhanced_theme += f"\n\nWriting Style: {request['writing_style']}"
        
        if request.get('tone'):
            enhanced_theme += f"\nTone: {request['tone']}"
        
        if request.get('emulate_author'):
            enhanced_theme += f"\nEmulate Author: {request['emulate_author']}"
        
        if request.get('themes'):
            themes_list = [t for t in request['themes'] if t]
            if themes_list:
                enhanced_theme += f"\n\nThemes: {', '.join(themes_list)}"
        
        if request.get('characters'):
            chars = request['characters']
            if chars:
                enhanced_theme += "\n\nCharacters:"
                for char in chars:
                    if char.get('name'):
                        enhanced_theme += f"\n- {char['name']}"
                        if char.get('role'):
                            enhanced_theme += f" ({char['role']})"
                        if char.get('description'):
                            enhanced_theme += f": {char['description']}"
                        if char.get('quirks'):
                            quirks = [q for q in char['quirks'] if q]
                            if quirks:
                                enhanced_theme += f"\n  Quirks: {', '.join(quirks)}"
        
        if request.get('timeline'):
            events = request['timeline']
            if events:
                enhanced_theme += "\n\nPlot Timeline:"
                for event in events:
                    if event.get('event'):
                        enhanced_theme += f"\n- Chapter {event.get('chapter', '?')}: {event['event']}"
                        if event.get('mood'):
                            enhanced_theme += f" (Mood: {event['mood']})"
        
        # Create story record
        story_data = {
            'user_id': current_user.id,
            'title': request.get('title'),
            'genre': genre,
            'theme': enhanced_theme,
            'characters': request.get('characters'),
            'setting': request.get('setting'),
            'length': length
        }
        
        story = create_story_record(db, story_data)
        story.credits_cost = cost
        db.commit()
        db.refresh(story)
        
        # Start generation in background
        background_tasks.add_task(
            generate_story,
            db,
            story.id,
            genre,
            enhanced_theme,
            request.get('characters'),
            request.get('setting'),
            length
        )
        
        return story.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create story: {str(e)}"
        )


@router.post("/generate-biography")
async def generate_biography(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a biography/autobiography/memoir
    
    Accepts comprehensive biographical data and generates a narrative.
    """
    try:
        # Validate required fields
        required = ['biography_type', 'subject_name', 'time_period_start', 'time_period_end', 'length']
        for field in required:
            if field not in payload:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Credit costs
        credit_costs = {
            'sample': 0,
            'short_memoir': 75,
            'standard_biography': 150,
            'comprehensive': 200
        }
        
        length = payload['length']
        cost = credit_costs.get(length, 0)
        
        # Check credits
        if current_user.credits_balance < cost:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {cost}, you have {current_user.credits_balance}"
            )
        
        # Deduct credits
        current_user.deduct_credits(cost)
        db.commit()
        
        # Create story record
        story = Story(
            user_id=current_user.id,
            story_type='biography',
            status='pending',
            biography_type=payload['biography_type'],
            subject_names=payload['subject_name'],
            time_period_start=payload['time_period_start'],
            time_period_end=payload['time_period_end'],
            length=length,
            credits_cost=cost,
            
            # Optional text fields
            setting=payload.get('birth_place'),
            tone=payload.get('tone'),
            narrative_voice=payload.get('narrative_voice'),
            
            # Optional JSON fields
            birth_details={
                'date': payload.get('birth_date'),
                'place': payload.get('birth_place'),
                'circumstances': payload.get('birth_circumstances')
            } if any([payload.get('birth_date'), payload.get('birth_place'), payload.get('birth_circumstances')]) else None,
            
            family_background={'text': payload.get('family_background')} if payload.get('family_background') else None,
            childhood={'text': payload.get('childhood_details')} if payload.get('childhood_details') else None,
            career={'text': payload.get('career_information')} if payload.get('career_information') else None,
            relationships={'text': payload.get('relationships')} if payload.get('relationships') else None,
            challenges={'text': payload.get('challenges_overcome')} if payload.get('challenges_overcome') else None,
            achievements={'text': payload.get('achievements')} if payload.get('achievements') else None,
            philosophy={'text': payload.get('philosophy_beliefs')} if payload.get('philosophy_beliefs') else None,
            
            # Arrays
            personality=payload.get('personality_traits'),
            hobbies=payload.get('hobbies_interests'),
            quotes=payload.get('notable_quotes'),
            sources=payload.get('sources'),
            focus_areas=payload.get('focus_areas'),
            themes=payload.get('themes'),
            major_events=payload.get('major_life_events'),
        )
        
        db.add(story)
        db.commit()
        db.refresh(story)
        
        # Start generation in background
        background_tasks.add_task(
            generate_biography_content,
            db,
            story.id
        )
        
        return {
            'success': True,
            'story_id': story.id,
            'status': 'pending',
            'credits_charged': cost
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate biography: {str(e)}"
        )


def generate_biography_content(db: Session, story_id: int):
    """
    Background task to generate biography with iterative chapter-by-chapter generation
    """
    from groq import Groq
    import os
    
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        return
    
    try:
        story.status = 'generating'
        db.commit()
        
        # Determine chapter structure based on length
        length_config = {
            'sample': {'words': 1500, 'chapters': 1, 'words_per_chapter': 1500},
            'short_memoir': {'words': 30000, 'chapters': 5, 'words_per_chapter': 6000},
            'standard_biography': {'words': 70000, 'chapters': 10, 'words_per_chapter': 7000},
            'comprehensive': {'words': 100000, 'chapters': 15, 'words_per_chapter': 6667}
        }
        
        config = length_config.get(story.length, length_config['sample'])
        
        # Build comprehensive theme from all biography fields
        theme = build_biography_theme(story)
        
        # Generate chapter outline
        print(f"Generating {config['chapters']}-chapter outline for biography...")
        chapter_outline = generate_chapter_outline(
            subject=theme,
            genre='Biography',
            num_chapters=config['chapters'],
            total_words=config['words']
        )
        
        story.story_metadata = {'chapter_outline': chapter_outline}
        db.commit()
        
        # Generate chapters iteratively
        all_chapters = []
        context_summary = ""
        
        for i, chapter_info in enumerate(chapter_outline):
            chapter_num = i + 1
            chapter_title = chapter_info.get('title', f'Chapter {chapter_num}')
            
            print(f"Generating biography chapter {chapter_num}/{config['chapters']}: {chapter_title}")
            
            chapter_content = generate_chapter(
                chapter_title=chapter_title,
                subject=theme + f"\n\nChapter focus: {chapter_info.get('summary', '')}",
                genre='Biography',
                style='truthful and narrative-driven',
                context_summary=context_summary,
                target_word_count=config['words_per_chapter']
            )
            
            all_chapters.append(chapter_content)
            
            # Update context summary with last 512 words
            words = chapter_content.split()
            context_summary = ' '.join(words[-512:]) if len(words) > 512 else chapter_content
            
            # Save progress after each chapter
            story.content = '\n\n---\n\n'.join(all_chapters)
            story.chapters_completed = chapter_num
            story.total_chapters = config['chapters']
            story.word_count = len(story.content.split())
            story.updated_at = datetime.utcnow()
            db.commit()
            
            print(f"Biography chapter {chapter_num} complete. Total words: {story.word_count}")
        
        # Generate title if not provided
        if not story.title:
            client = Groq(api_key=os.getenv('GROQ_API_KEY'))
            title_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a publishing expert who creates compelling biography titles."},
                    {"role": "user", "content": f"Create a 2-6 word title for this biography:\n\n{all_chapters[0][:500]}\n\nRespond with ONLY the title, no quotes or explanation."}
                ],
                temperature=0.7,
                max_tokens=20
            )
            story.title = title_response.choices[0].message.content.strip().strip('"').strip("'")
        
        # Mark as completed
        story.status = 'completed'
        story.completed_at = datetime.utcnow()
        db.commit()
        
        print(f"Biography generation complete. Final word count: {story.word_count}")
        
    except Exception as e:
        print(f"Biography generation error: {str(e)}")
        story.status = 'failed'
        story.error_message = str(e)
        db.commit()


def build_biography_theme(story: Story) -> str:
    """
    Build comprehensive theme from biography fields
    """
    parts = [
        f"Write a {story.biography_type} about {story.subject_names}.",
        f"Time period: {story.time_period_start} to {story.time_period_end}."
    ]
    
    if story.birth_details:
        bd = story.birth_details
        if bd.get('date') or bd.get('place'):
            parts.append(f"Born: {bd.get('date', '')} in {bd.get('place', '')}")
        if bd.get('circumstances'):
            parts.append(f"Birth circumstances: {bd['circumstances']}")
    
    if story.family_background:
        parts.append(f"Family: {story.family_background.get('text', '')[:200]}")
    
    if story.childhood:
        parts.append(f"Childhood: {story.childhood.get('text', '')[:200]}")
    
    if story.career:
        parts.append(f"Career: {story.career.get('text', '')[:200]}")
    
    if story.relationships:
        parts.append(f"Relationships: {story.relationships.get('text', '')[:200]}")
    
    if story.challenges:
        parts.append(f"Challenges: {story.challenges.get('text', '')[:200]}")
    
    if story.achievements:
        parts.append(f"Achievements: {story.achievements.get('text', '')[:200]}")
    
    if story.personality:
        parts.append(f"Personality: {', '.join(story.personality)}")
    
    if story.hobbies:
        parts.append(f"Hobbies: {', '.join(story.hobbies)}")
    
    if story.philosophy:
        parts.append(f"Philosophy: {story.philosophy.get('text', '')[:150]}")
    
    if story.themes:
        parts.append(f"Themes: {', '.join(story.themes)}")
    
    if story.focus_areas:
        parts.append(f"Focus on: {', '.join(story.focus_areas)}")
    
    voice = story.narrative_voice or 'third_person_limited'
    tone = story.tone or 'balanced and respectful'
    parts.append(f"Voice: {voice.replace('_', ' ')}. Tone: {tone}.")
    parts.append("Write compelling narrative-driven biography that reads like a story, not a resume.")
    parts.append("Be truthful and grounded in provided facts.")
    
    return '\n'.join(parts)


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
