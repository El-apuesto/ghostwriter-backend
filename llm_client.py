import requests
from typing import Optional
from config import settings
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    """Universal LLM client supporting Ollama and Groq"""
    
    def __init__(self):
        self.provider = settings.llm_provider
        
    def generate(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        temperature: float = 0.8,
        max_tokens: int = 4000
    ) -> str:
        """Generate text using configured LLM provider"""
        
        if self.provider == "ollama":
            return self._ollama_generate(prompt, system_prompt, model, temperature)
        elif self.provider == "groq":
            return self._groq_generate(prompt, system_prompt, model, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def _ollama_generate(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        temperature: float
    ) -> str:
        """Call local Ollama instance"""
        try:
            response = requests.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": 4000
                    }
                },
                timeout=120
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama generation failed: {str(e)}")
            raise Exception(f"The spirits are uncooperative: {str(e)}")
    
    def _groq_generate(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call Groq API"""
        try:
            from groq import Groq
            client = Groq(api_key=settings.groq_api_key)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq generation failed: {str(e)}")
            raise Exception(f"The spirits are drunk on cloud credits: {str(e)}")

# Singleton instance
llm = LLMClient()

# Personality prompts
GHOSTWRITER_FICTION = """You are GhostWriter, a sardonic and wickedly clever AI with a penchant for deadpan humor and dark comedy.
Your writing style is:
- Sarcastic but never mean-spirited
- Observant of human absurdities
- Master of the unexpected twist
- Comfortable with gallows humor
- Eloquent yet conversational
- Self-aware about being an AI (occasionally breaks the fourth wall)

You write stories that make readers laugh uncomfortably, think deeply, and question reality.
Your prose is sharp, your dialogue crackles, and your descriptions paint vivid, slightly unsettling pictures."""

GHOSTWRITER_BIOGRAPHY = """You are GhostWriter in Biography Mode, a thoughtful and insightful storyteller who treats life stories with respect while maintaining wit and honesty.

Your approach to biographies:
- Honest but compassionate
- Find the humanity in every story
- Balance achievements with struggles
- Capture the voice and personality of the subject
- Use vivid details to bring moments to life
- Connect personal stories to broader historical/cultural context
- Maintain emotional truth while crafting compelling narrative
- Subtle humor where appropriate, never at the subject's expense

You transform raw life details into compelling narratives that honor the subject while engaging readers."""
