"""
Story generation module using Groq LLM with proper database commit handling
"""
from datetime import datetime
from llm_client import llm
from config import settings

def generate_story(db, story_id, genre, theme, characters=None, setting=None, length='short'):
    """
    Generate a story using Groq (Llama 3.3 70B) with immediate database commit
    
    Args:
        db: Database session/connection
        story_id: ID of the story record
        genre: Story genre
        theme: Story theme
        characters: Optional character descriptions
        setting: Optional setting description
        length: Story length (short, medium, long)
    """
    try:
        # Get the story record
        from models import Story
        story = db.query(Story).filter(Story.id == story_id).first()
        
        if not story:
            raise ValueError(f"Story with ID {story_id} not found")
        
        # Update status to generating and commit immediately
        story.status = 'generating'
        db.commit()  # CRITICAL: Commit immediately so frontend can find the record
        db.refresh(story)
        
        print(f"Starting story generation for ID: {story_id}")
        
        # Build the prompt
        prompt = build_story_prompt(genre, theme, characters, setting, length)
        
        # System prompt with GhostWriter personality
        system_prompt = """You are GhostWriter, a sardonic and wickedly clever AI storyteller with a penchant for deadpan humor and dark comedy.

Your writing style is:
- Sarcastic but never mean-spirited
- Observant of human absurdities
- Master of the unexpected twist
- Comfortable with gallows humor
- Eloquent yet conversational
- Self-aware (occasionally breaks the fourth wall)

You write stories that make readers laugh uncomfortably, think deeply, and question reality.
Your prose is sharp, your dialogue crackles, and your descriptions paint vivid, slightly unsettling pictures.

Write ONLY the story itself - no preamble, no meta-commentary, no "Here's your story" intro."""
        
        # Generate the story using Groq
        print(f"Calling Groq API with model: {settings.creative_model}")
        story_content = llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=settings.creative_model,
            temperature=0.8,
            max_tokens=4000
        )
        
        # Generate a title if none exists
        if not story.title or story.title == 'Untitled Story':
            title = generate_title(genre, theme, story_content[:500])
            story.title = title
        
        # Update the story record with content
        story.content = story_content
        story.status = 'completed'
        story.updated_at = datetime.utcnow()
        db.commit()  # Commit the completed story
        db.refresh(story)
        
        print(f"Story generation completed for ID: {story_id}")
        return story
        
    except Exception as e:
        print(f"Error generating story: {str(e)}")
        
        # Update story status to failed
        try:
            story = db.query(Story).filter(Story.id == story_id).first()
            if story:
                story.status = 'failed'
                story.error_message = str(e)
                db.commit()
        except Exception as db_error:
            print(f"Error updating story status: {str(db_error)}")
            db.rollback()
        
        raise


def generate_title(genre, theme, story_preview):
    """
    Generate a catchy title for the story based on genre, theme, and preview
    """
    try:
        prompt = f"""Based on this story preview, create a short, catchy title (3-6 words max):

Genre: {genre}
Theme: {theme}
Preview: {story_preview}

Respond with ONLY the title, nothing else."""
        
        system_prompt = "You are a creative title generator. Respond with ONLY the title, no quotes, no explanation."
        
        title = llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=settings.creative_model,
            temperature=0.7,
            max_tokens=50
        )
        
        # Clean up the title
        title = title.strip().strip('"').strip("'").strip()
        return title[:100]  # Limit length
        
    except Exception as e:
        print(f"Error generating title: {str(e)}")
        return f"{genre.title()}: {theme[:30]}"


def build_story_prompt(genre, theme, characters, setting, length):
    """
    Build the prompt for story generation
    """
    length_map = {
        'short': '800-1200 words',
        'medium': '1500-2500 words',
        'long': '3000-4000 words'
    }
    
    target_length = length_map.get(length, '800-1200 words')
    
    prompt = f"""Write a complete {genre} story with the following specifications:

**Theme:** {theme}
**Target Length:** {target_length}
"""
    
    if characters:
        prompt += f"\n**Main Characters:** {characters}"
    
    if setting:
        prompt += f"\n**Setting:** {setting}"
    
    prompt += f"""

**Requirements:**
1. Full narrative arc: beginning, middle, and satisfying end
2. Rich character development and thematic depth
3. Vivid descriptions that engage the senses
4. Natural, distinctive dialogue
5. Maintain your signature sardonic wit and dark humor
6. Stay within the target word count
7. Make it memorable and slightly unsettling

Write the complete story now. Begin immediately with the narrative - no title, no introduction.
"""
    
    return prompt


def create_story_record(db, story_data):
    """
    Create a new story record in the database
    
    Args:
        db: Database session
        story_data: Dictionary containing story parameters
    
    Returns:
        Created story object with ID
    """
    from models import Story
    
    try:
        # Create new story record
        story = Story(
            title=story_data.get('title', 'Untitled Story'),
            genre=story_data.get('genre'),
            theme=story_data.get('theme'),
            characters=story_data.get('characters'),
            setting=story_data.get('setting'),
            length=story_data.get('length', 'short'),
            status='pending',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(story)
        db.commit()  # CRITICAL: Commit immediately to get the ID
        db.refresh(story)
        
        print(f"Created story record with ID: {story.id}")
        return story
        
    except Exception as e:
        print(f"Error creating story record: {str(e)}")
        db.rollback()
        raise
