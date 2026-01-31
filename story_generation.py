"""
Story generation module with iterative chapter-by-chapter generation
"""
from datetime import datetime
from llm_client import llm
from config import settings
import json

def generate_chapter(
    chapter_title: str,
    subject: str,
    genre: str,
    style: str,
    context_summary: str = "",
    target_word_count: int = 8000
) -> str:
    """
    Generates a single chapter iteratively until target word count is reached.
    Uses last 512 words as context for continuation to avoid token limits.
    
    Args:
        chapter_title: Title of the chapter
        subject: Main story theme/subject
        genre: Story genre
        style: Writing style
        context_summary: Summary from previous chapter (last 512 words)
        target_word_count: Target word count for this chapter
    
    Returns:
        Complete chapter text
    """
    try:
        generated_text = ""
        total_word_count = 0
        
        # Initial prompt for chapter start
        prompt = f"""Chapter Title: {chapter_title}
Story Theme: {subject}
Story Style: {style}
Story Genre: {genre}
Context Summary: {context_summary}

Write the next part of this chapter with rich detail, vivid descriptions, and compelling narrative.
"""
        
        system_prompt = """You are Phantm.ink, a creative and sophisticated AI storyteller with expertise in crafting compelling narratives.

Your writing style is:
- Sarcastic but never mean-spirited
- Observant of human absurdities
- Master of the unexpected twist
- Comfortable with gallows humor
- Eloquent yet conversational
- Self-aware (occasionally breaks the fourth wall)

You write stories that make readers laugh uncomfortably, think deeply, and question reality.
Your prose is sharp, your dialogue crackles, and your descriptions paint vivid, slightly unsettling pictures.

Write ONLY the story content - no preamble, no meta-commentary."""
        
        # Iteratively generate until we hit target word count
        while total_word_count < target_word_count:
            # Calculate remaining words needed
            remaining_words = target_word_count - total_word_count
            # Estimate tokens (roughly 1.3 words per token)
            max_tokens = min(1500, int(remaining_words * 1.3))
            
            # Generate next chunk
            new_text = llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model=settings.creative_model,
                temperature=0.8,
                max_tokens=max_tokens
            )
            
            generated_text += new_text + "\n\n"
            total_word_count = len(generated_text.split())
            
            # Update prompt with last 512 words for context continuity
            words = generated_text.split()
            last_512_words = ' '.join(words[-512:]) if len(words) > 512 else generated_text
            prompt = f"Continue the story: {last_512_words}\n\nStory Theme: {subject}\n\n"
            
            print(f"Chapter '{chapter_title}': {total_word_count}/{target_word_count} words generated")
        
        return f"# {chapter_title}\n\n{generated_text.strip()}"
        
    except Exception as e:
        print(f"Error generating chapter '{chapter_title}': {e}")
        raise


def generate_chapter_outline(subject: str, genre: str, num_chapters: int, total_words: int) -> list:
    """
    Generate chapter titles and summaries for the entire story structure.
    
    Args:
        subject: Story theme/subject
        genre: Story genre
        num_chapters: Number of chapters needed
        total_words: Total target word count
    
    Returns:
        List of dicts with 'title' and 'summary' for each chapter
    """
    try:
        prompt = f"""Create a {num_chapters}-chapter outline for a {genre} story about: {subject}

Target total length: {total_words} words

For each chapter, provide:
1. A compelling chapter title (3-8 words)
2. A brief summary of what happens (2-3 sentences)

Format your response as a JSON array like this:
[
  {{"title": "Chapter Title", "summary": "What happens in this chapter"}},
  ...
]

Respond with ONLY the JSON array, no other text."""
        
        system_prompt = "You are a story structure expert. Respond with ONLY valid JSON, no markdown, no explanation."
        
        outline_json = llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=settings.creative_model,
            temperature=0.7,
            max_tokens=2000
        )
        
        # Clean up response (remove markdown code blocks if present)
        outline_json = outline_json.strip()
        if outline_json.startswith("```"):
            lines = outline_json.split("\n")
            outline_json = "\n".join(lines[1:-1])  # Remove first and last lines
        
        outline = json.loads(outline_json)
        
        # Validate we got the right number of chapters
        if len(outline) != num_chapters:
            print(f"Warning: Got {len(outline)} chapters, expected {num_chapters}")
        
        return outline
        
    except Exception as e:
        print(f"Error generating chapter outline: {e}")
        # Fallback: create simple numbered chapters
        return [
            {
                "title": f"Chapter {i+1}",
                "summary": f"Part {i+1} of the story"
            }
            for i in range(num_chapters)
        ]


def generate_story(db, story_id, genre, theme, characters=None, setting=None, length='short'):
    """
    Generate a complete multi-chapter story using iterative generation.
    Updates database after each chapter completes.
    
    Args:
        db: Database session/connection
        story_id: ID of the story record
        genre: Story genre
        theme: Story theme
        characters: Optional character descriptions
        setting: Optional setting description
        length: Story length (short, medium, long, novella, novel, epic)
    """
    try:
        from models import Story
        print(f"DEBUG: Looking for story ID: {story_id}")
        story = db.query(Story).filter(Story.id == story_id).first()
        
        if not story:
            raise ValueError(f"Story with ID {story_id} not found")
        
        print(f"DEBUG: Found story: {story.id}, Status: {story.status}")
        
        # Update status to generating and commit immediately
        story.status = 'generating'
        db.commit()
        db.refresh(story)
        
        print(f"Starting story generation for ID: {story_id}")
        print(f"DEBUG: Genre: {genre}, Theme: {theme[:100]}...")
        print(f"DEBUG: Length: {length}")
        
        # Determine chapter structure based on length
        length_config = {
            'short': {'words': 3000, 'chapters': 1, 'words_per_chapter': 3000},
            'medium': {'words': 8000, 'chapters': 2, 'words_per_chapter': 4000},
            'long': {'words': 15000, 'chapters': 3, 'words_per_chapter': 5000},
            'novella': {'words': 45000, 'chapters': 6, 'words_per_chapter': 7500},
            'novel': {'words': 90000, 'chapters': 12, 'words_per_chapter': 7500},
            'epic': {'words': 140000, 'chapters': 18, 'words_per_chapter': 7800}
        }
        
        config = length_config.get(length, length_config['short'])
        num_chapters = config['chapters']
        words_per_chapter = config['words_per_chapter']
        total_words = config['words']
        
        # Build enhanced theme with characters and setting
        enhanced_theme = theme
        if characters:
            enhanced_theme += f"\n\nMain Characters: {characters}"
        if setting:
            enhanced_theme += f"\n\nSetting: {setting}"
        
        # Generate chapter outline first
        print(f"Generating outline for {num_chapters} chapters...")
        chapter_outline = generate_chapter_outline(enhanced_theme, genre, num_chapters, total_words)
        
        # Store chapter outline in story metadata
        story.metadata = {'chapter_outline': chapter_outline}
        db.commit()
        
        # Generate chapters sequentially
        all_chapters = []
        context_summary = ""
        
        for i, chapter_info in enumerate(chapter_outline):
            chapter_num = i + 1
            chapter_title = chapter_info.get('title', f'Chapter {chapter_num}')
            
            print(f"\n=== Generating Chapter {chapter_num}/{num_chapters}: {chapter_title} ===")
            
            # Generate the chapter
            chapter_content = generate_chapter(
                chapter_title=chapter_title,
                subject=enhanced_theme + f"\n\nChapter Summary: {chapter_info.get('summary', '')}",
                genre=genre,
                style='sardonic and darkly humorous',
                context_summary=context_summary,
                target_word_count=words_per_chapter
            )
            
            all_chapters.append(chapter_content)
            
            # Update context summary with last 512 words from this chapter
            words = chapter_content.split()
            context_summary = ' '.join(words[-512:]) if len(words) > 512 else chapter_content
            
            # Save progress to database after each chapter
            story.content = '\n\n---\n\n'.join(all_chapters)
            story.chapters_completed = chapter_num
            story.total_chapters = num_chapters
            story.word_count = len(story.content.split())
            story.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(story)
            
            print(f"Chapter {chapter_num} completed and saved. Total words: {story.word_count}")
        
        # Generate title if none exists
        if not story.title or story.title == 'Untitled Story':
            title = generate_title(genre, theme, all_chapters[0][:500])
            story.title = title
        
        # Mark as completed
        story.status = 'completed'
        story.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(story)
        
        print(f"Story generation completed for ID: {story_id}")
        print(f"Final word count: {story.word_count} words across {num_chapters} chapters")
        return story
        
    except Exception as e:
        print(f"ERROR: Story generation failed: {str(e)}")
        print(f"ERROR: Exception type: {type(e).__name__}")
        import traceback
        print(f"ERROR: Traceback: {traceback.format_exc()}")
        
        # Update story status to failed
        try:
            story = db.query(Story).filter(Story.id == story_id).first()
            if story:
                story.status = 'failed'
                story.error_message = str(e)
                db.commit()
                print(f"DEBUG: Updated story status to failed with error: {str(e)}")
        except Exception as db_error:
            print(f"ERROR: Error updating story status: {str(db_error)}")
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
    Build the prompt for story generation (legacy, kept for compatibility)
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
            user_id=story_data['user_id'],
            story_type='fiction',
            title=story_data.get('title', 'Untitled Story'),
            genre=story_data.get('genre'),
            theme=story_data.get('theme'),
            characters=story_data.get('characters'),
            setting=story_data.get('setting'),
            length=story_data.get('length', 'short'),
            status='pending',
            chapters_completed=0,
            total_chapters=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(story)
        db.commit()
        db.refresh(story)
        
        print(f"Created story record with ID: {story.id}")
        return story
        
    except Exception as e:
        print(f"Error creating story record: {str(e)}")
        db.rollback()
        raise
