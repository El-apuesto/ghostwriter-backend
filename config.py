from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database - PostgreSQL (Neon) for production
    database_url: str = "postgresql://user:password@host/dbname"
    
    # LLM Configuration (Text Generation)
    llm_provider: str = "groq"  # "ollama", "groq", or "xai"
    ollama_base_url: str = "http://localhost:11434"
    groq_api_key: Optional[str] = None  # Will be loaded from GROQ_API_KEY environment variable
    xai_api_key: Optional[str] = None  # Used for xAI Grok text generation and AI covers
    
    # Model Selection (varies by provider)
    creative_model: str = "llama-3.3-70b-versatile"      # For creative fiction (Groq) or grok-2-1212 (xAI)
    structured_model: str = "llama-3.3-70b-versatile"    # For outlines/structure (Groq) or grok-2-1212 (xAI)
    dialogue_model: str = "llama-3.3-70b-versatile"      # For dialogue (Groq) or grok-2-1212 (xAI)
    biography_model: str = "llama-3.3-70b-versatile"     # For biographies (Groq) or grok-2-1212 (xAI)
    
    # Authentication
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_days: int = 7
    
    # Stripe
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_webhook_secret: str
    
    # App Settings
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    
    # Generation Settings
    max_tokens_per_request: int = 4000
    temperature: float = 0.8
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Credit costs
CREDIT_COSTS = {
    # Fiction
    "fiction_sample": 0,
    "fiction_novella": 130,
    "fiction_novel": 210,
    
    # Premium Fiction
    "fiction_premium_novella": 150,
    "fiction_premium_novel": 230,
    
    # Biography
    "biography_sample": 0,
    "biography_short_memoir": 130,
    "biography_standard": 130,
    
    # Extras
    "ebook_cover": 10,
    "print_cover": 15,
    "epub_export": 5,
    "mobi_export": 5,
    "kdp_pdf": 10,
    "blurb": 5,
    "author_bio": 3,
}

# Credit packs (price in cents, credits amount)
CREDIT_PACKS = {
    "top_up": {"price": 500, "credits": 50, "name": "Top-Up Pack"},
}

settings = Settings()