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
    Background task to generate biography content
    """
    from groq import Groq
    import os
    
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        return
    
    try:
        story.status = 'generating'
        db.commit()
        
        # Build comprehensive prompt from all fields
        prompt_parts = [
            f"Write a {story.length} {story.biography_type} about {story.subject_names}.",
            f"Time period: {story.time_period_start} to {story.time_period_end}."
        ]
        
        # Add all optional details
        if story.birth_details:
            bd = story.birth_details
            if bd.get('date') or bd.get('place'):
                prompt_parts.append(f"Born: {bd.get('date', '')} in {bd.get('place', '')}")
            if bd.get('circumstances'):
                prompt_parts.append(f"Birth circumstances: {bd['circumstances']}")
        
        if story.family_background:
            prompt_parts.append(f"Family background: {story.family_background.get('text')}")
        
        if story.childhood:
            prompt_parts.append(f"Childhood: {story.childhood.get('text')}")
        
        if story.career:
            prompt_parts.append(f"Career: {story.career.get('text')}")
        
        if story.relationships:
            prompt_parts.append(f"Relationships: {story.relationships.get('text')}")
        
        if story.major_events:
            prompt_parts.append("\nMajor life events:")
            for event in story.major_events:
                if event.get('description'):
                    prompt_parts.append(f"- {event.get('date', '')} {event.get('type', '')}: {event['description']}")
                    if event.get('impact'):
                        prompt_parts.append(f"  Impact: {event['impact']}")
        
        if story.challenges:
            prompt_parts.append(f"\nChallenges overcome: {story.challenges.get('text')}")
        
        if story.achievements:
            prompt_parts.append(f"\nAchievements: {story.achievements.get('text')}")
        
        if story.personality:
            prompt_parts.append(f"\nPersonality traits: {', '.join(story.personality)}")
        
        if story.hobbies:
            prompt_parts.append(f"Hobbies/interests: {', '.join(story.hobbies)}")
        
        if story.philosophy:
            prompt_parts.append(f"\nPhilosophy/beliefs: {story.philosophy.get('text')}")
        
        if story.quotes:
            prompt_parts.append(f"\nNotable quotes: {', '.join(['"' + q + '"' for q in story.quotes if q])}")
        
        if story.themes:
            prompt_parts.append(f"\nThemes to emphasize: {', '.join(story.themes)}")
        
        if story.focus_areas:
            prompt_parts.append(f"Focus on: {', '.join(story.focus_areas)}")
        
        # Writing style instructions
        voice = story.narrative_voice or 'third_person_limited'
        tone_text = story.tone or 'balanced and respectful'
        
        prompt_parts.append(f"\nWrite in {voice.replace('_', ' ')} narrative voice.")
        prompt_parts.append(f"Tone: {tone_text}.")
        prompt_parts.append("\nWrite a compelling, narrative-driven biography that reads like a story, not a resume.")
        prompt_parts.append("Include vivid scenes, dialogue where appropriate, and emotional depth.")
        prompt_parts.append("Be truthful and grounded in the provided facts.")
        
        full_prompt = "\n".join(prompt_parts)
        
        # Generate with Groq
        client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        
        system_prompt = """
You are GhostWriter, a skilled biographer and memoirist with a gift for capturing authentic human experiences.
You write with empathy, insight, and narrative flair, making real lives compelling without sensationalizing or fabricating.

Your non-fiction writing is:
- Truthful and grounded in provided facts
- Emotionally resonant
- Well-researched in tone
- Narrative-driven (reads like a story, not a resume)
- Balanced (acknowledges complexity and contradictions)
- Respectful but honest

Write ONLY the biography content - no preamble, no meta-commentary.
        """
        
        # Determine word count target
        word_targets = {
            'sample': 1500,
            'short_memoir': 30000,
            'standard_biography': 70000,
            'comprehensive': 100000
        }
        target_words = word_targets.get(story.length, 1500)
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{full_prompt}\n\nTarget length: approximately {target_words} words."}
            ],
            temperature=0.8,
            max_tokens=8000  # Will need chunking for longer stories
        )
        
        content = response.choices[0].message.content.strip()
        word_count = len(content.split())
        
        # Generate title if not provided
        if not story.title:
            title_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a publishing expert who creates compelling biography titles."},
                    {"role": "user", "content": f"Create a 2-6 word title for this biography:\n\n{content[:1000]}\n\nRespond with ONLY the title, no quotes or explanation."}
                ],
                temperature=0.7,
                max_tokens=20
            )
            story.title = title_response.choices[0].message.content.strip().strip('"').strip("'")
        
        # Save
        story.content = content
        story.word_count = word_count
        story.status = 'completed'
        story.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        story.status = 'failed'
        story.error_message = str(e)
        db.commit()


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
