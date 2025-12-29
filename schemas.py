from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

# ===== AUTHENTICATION SCHEMAS =====

class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserProfile(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    credits_balance: int
    total_credits_purchased: int
    total_credits_spent: int
    created_at: datetime
    
    class Config:
        from_attributes = True

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

# ===== STORY RESPONSE SCHEMAS =====

class StoryResponse(BaseModel):
    story_id: int
    title: str
    story_type: str
    status: str
    credits_cost: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class StoryDetail(BaseModel):
    id: int
    title: str
    story_type: str
    length_type: str
    content: Any  # Can be JSON or string
    metadata: Dict
    credits_cost: int
    has_ebook_cover: bool
    has_print_cover: bool
    has_epub: bool
    has_mobi: bool
    has_pdf: bool
    has_blurb: bool
    has_author_bio: bool
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# ===== EXTRAS SCHEMAS =====

class ExtraType(str, Enum):
    EBOOK_COVER = "ebook_cover"
    PRINT_COVER = "print_cover"
    EPUB = "epub_export"
    MOBI = "mobi_export"
    KDP_PDF = "kdp_pdf"
    BLURB = "blurb"
    AUTHOR_BIO = "author_bio"

class GenerateExtraRequest(BaseModel):
    story_id: int
    extra_type: ExtraType
    options: Optional[Dict[str, Any]] = None  # For cover customization, etc.

class ExtraResponse(BaseModel):
    extra_id: int
    story_id: int
    extra_type: str
    credits_cost: int
    download_url: Optional[str] = None
    content: Optional[str] = None  # For text-based extras like blurb
    created_at: datetime

# ===== CREDITS SCHEMAS =====

class CreditPackPurchase(BaseModel):
    pack_type: str  # micro, small, medium, starter, value, pro, ultimate

class CreditPackResponse(BaseModel):
    name: str
    price_usd: float
    credits: int
    bonus_percentage: int
    checkout_url: str

class TransactionHistory(BaseModel):
    id: int
    transaction_type: str
    amount_usd: Optional[float]
    credits_amount: int
    description: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
