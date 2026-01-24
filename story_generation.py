"""
Story generation module with proper database commit handling
"""
import os
from datetime import datetime
from anthropic import Anthropic

def generate_story(db, story_id, genre, theme, characters=None, setting=None, length='short'):
    """
    Generate a story using Claude AI with immediate database commit
    
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
        from models import Story  # Adjust import based on your structure
        story = db.query(Story).filter(Story.id == story_id).first()
        
        if not story:
            raise ValueError(f"Story with ID {story_id} not found")
        
        # Update status to generating and commit immediately
        story.status = 'generating'
        db.commit()  # CRITICAL FIX: Commit immediately so frontend can find the record
        db.refresh(story)
        
        print(f"Starting story generation for ID: {story_id}")
        
        # Prepare the prompt
        prompt = build_story_prompt(genre, theme, characters, setting, length)
        
        # Initialize Anthropic client
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        client = Anthropic(api_key=api_key)
        
        # Generate the story
        print("Calling Claude API...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Extract the story content
        story_content = response.content[0].text
        
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


def build_story_prompt(genre, theme, characters, setting, length):
    """
    Build the prompt for story generation
    """
    length_map = {
        'short': '500-1000 words',
        'medium': '1000-2000 words',
        'long': '2000-3000 words'
    }
    
    target_length = length_map.get(length, '500-1000 words')
    
    prompt = f"""Write a compelling {genre} story with the following specifications:

Theme: {theme}
Target Length: {target_length}
"""
    
    if characters:
        prompt += f"\nMain Characters: {characters}"
    
    if setting:
        prompt += f"\nSetting: {setting}"
    
    prompt += """

Please write a complete, engaging story that:
1. Has a clear beginning, middle, and end
2. Develops the characters and theme effectively
3. Uses vivid descriptions and engaging dialogue
4. Stays within the target length
5. Is appropriate for a general audience

Write only the story itself, without any preamble or meta-commentary.
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
        db.commit()  # CRITICAL FIX: Commit immediately to get the ID
        db.refresh(story)
        
        print(f"Created story record with ID: {story.id}")
        return story
        
    except Exception as e:
        print(f"Error creating story record: {str(e)}")
        db.rollback()
        raise
