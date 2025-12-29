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

settings = Settings()
