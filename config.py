from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./ghostwriter.db"
    
    # LLM Configuration
    llm_provider: str = "ollama"  # or "groq"
    ollama_base_url: str = "http://localhost:11434"
    groq_api_key: Optional[str] = None
    
    # Model Selection
    creative_model: str = "dolphin-mixtral"      # For creative fiction
    structured_model: str = "deepseek-coder-v2"  # For outlines/structure
    dialogue_model: str = "wizard-vicuna-uncensored"  # For dialogue
    biography_model: str = "qwen2.5:32b"         # For biographies
    
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
    "fiction_novella": 50,
    "fiction_novel": 100,
    
    # Biography
    "biography_sample": 0,
    "biography_short_memoir": 50,
    "biography_standard": 75,
    "biography_comprehensive": 125,
    
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
    "micro": {"price": 500, "credits": 20, "name": "Micro Top-Up"},
    "small": {"price": 1000, "credits": 40, "name": "Small Top-Up"},
    "medium": {"price": 1500, "credits": 60, "name": "Medium Top-Up"},
    "starter": {"price": 2500, "credits": 100, "name": "Starter Pack"},
    "value": {"price": 6000, "credits": 250, "name": "Value Pack", "bonus": 4},
    "pro": {"price": 12000, "credits": 550, "name": "Pro Pack", "bonus": 15},
    "ultimate": {"price": 24000, "credits": 1200, "name": "Ultimate Pack", "bonus": 25},
}

settings = Settings()
