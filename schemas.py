from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

# ===== FICTION SCHEMAS =====

class WritingStyle(str, Enum):
    SARCASTIC_DEADPAN = "sarcastic_deadpan"
    GOTHIC_HORROR = "gothic_horror"
    DARK_COMEDY = "dark_comedy"
    NOIR = "noir"
    CYBERPUNK = "cyberpunk"
    MODERN = "modern"
    CLASSIC = "classic"

class Genre(str, Enum):
    HORROR = "horror"
    MYSTERY = "mystery"
    THRILLER = "thriller"
    DARK_FANTASY = "dark_fantasy"
    SCIFI = "scifi"
    COMEDY = "comedy"
    SATIRE = "satire"

class FictionLength(str, Enum):
    SAMPLE = "sample"
    NOVELLA = "novella"
    NOVEL = "novel"

class Character(BaseModel):
    name: str
    role: Optional[str] = None
    description: Optional[str] = None
    quirks: Optional[List[str]] = None

class TimelineEvent(BaseModel):
    chapter: Optional[int] = None
    description: str
    mood: Optional[str] = None

class FictionRequest(BaseModel):
    premise: str = Field(..., min_length=10, max_length=2000)
    story_length: FictionLength
    email: str
    
    # Optional
    title: Optional[str] = None
    style: Optional[WritingStyle] = WritingStyle.SARCASTIC_DEADPAN
    genre: Optional[Genre] = None
    characters: Optional[List[Character]] = None
    timeline: Optional[List[TimelineEvent]] = None
    setting: Optional[str] = None
    tone: Optional[str] = None
    themes: Optional[List[str]] = None
    emulate_author: Optional[str] = None

# ===== BIOGRAPHY SCHEMAS =====

class BiographyType(str, Enum):
    AUTOBIOGRAPHY = "autobiography"
    BIOGRAPHY = "biography"
    MEMOIR = "memoir"
    FAMILY_HISTORY = "family_history"

class BiographyLength(str, Enum):
    SAMPLE = "sample"
    SHORT_MEMOIR = "short_memoir"
    STANDARD_BIOGRAPHY = "standard_biography"
    COMPREHENSIVE = "comprehensive"

class NarrativeVoice(str, Enum):
    FIRST_PERSON = "first_person"
    THIRD_PERSON_LIMITED = "third_person_limited"
    THIRD_PERSON_OMNISCIENT = "third_person_omniscient"
    CONVERSATIONAL = "conversational"
    FORMAL = "formal"
    JOURNALISTIC = "journalistic"

class LifeEvent(BaseModel):
    date: Optional[str] = None
    event_type: str
    description: str
    impact: Optional[str] = None
    emotional_weight: Optional[int] = Field(None, ge=1, le=10)

class BiographyRequest(BaseModel):
    # Required
    biography_type: BiographyType
    subject_names: str = Field(..., min_length=2)
    time_period_start: str
    time_period_end: str
    story_length: BiographyLength
    email: str
    
    # Core Information (Optional)
    birth_details: Optional[Dict[str, Any]] = None
    family_background: Optional[Dict[str, Any]] = None
    childhood: Optional[Dict[str, Any]] = None
    career: Optional[Dict[str, Any]] = None
    relationships: Optional[Dict[str, Any]] = None
    major_events: Optional[List[LifeEvent]] = None
    challenges: Optional[Dict[str, Any]] = None
    achievements: Optional[Dict[str, Any]] = None
    personality: Optional[Dict[str, Any]] = None
    historical_context: Optional[Dict[str, Any]] = None
    hobbies: Optional[Dict[str, Any]] = None
    philosophy: Optional[Dict[str, Any]] = None
    quotes: Optional[List[Dict[str, str]]] = None
    sources: Optional[Dict[str, Any]] = None
    
    # Writing Options
    narrative_voice: Optional[NarrativeVoice] = NarrativeVoice.THIRD_PERSON_LIMITED
    tone: Optional[str] = "balanced"
    writing_style: Optional[str] = "chronological"
    focus_areas: Optional[List[str]] = None
    themes: Optional[List[str]] = None

class StoryResponse(BaseModel):
    story_id: int
    title: str
    status: str
    message: str
