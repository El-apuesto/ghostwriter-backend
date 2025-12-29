import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict

import stripe
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import settings
from models import Base, User, Story
from schemas import FictionRequest, BiographyRequest, StoryResponse, FictionLength, BiographyLength
from llm_client import llm, GHOSTWRITER_FICTION, GHOSTWRITER_BIOGRAPHY

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Stripe setup
stripe.api_key = settings.stripe_secret_key

# FastAPI app
app = FastAPI(
    title="GhostWriter API",
    description="AI-powered fiction and biography generator with sarcastic wit",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== STORY GENERATION FUNCTIONS =====

def generate_fiction(request: FictionRequest, db: Session) -> Dict:
    """Generate fiction story"""
    word_counts = {"sample": 1500, "novella": 30000, "novel": 80000}
    target = word_counts[request.story_length]
    
    logger.info(f"Generating fiction: {request.premise[:50]}...")
    
    # Step 1: Generate outline
    outline_prompt = f"""Create a story outline for:
Premise: {request.premise}
Length: {target} words
Style: {request.style.value if request.style else 'sarcastic_deadpan'}
Genre: {request.genre.value if request.genre else 'choose best fit'}
Setting: {request.setting or 'choose atmospheric setting'}
{f'Characters: {json.dumps([c.dict() for c in request.characters])}' if request.characters else ''}
{f'Themes: {request.themes}' if request.themes else ''}

Generate JSON with: title, chapters (array with title, synopsis), characters, themes"""
    
    outline_text = llm.generate(outline_prompt, GHOSTWRITER_FICTION, settings.structured_model)
    
    try:
        outline = json.loads(outline_text)
    except:
        # If JSON parsing fails, create a simple outline
        outline = {
            "title": request.title or "Untitled Story",
            "chapters": [{"title": "Chapter 1", "synopsis": request.premise}],
            "themes": request.themes or []
        }
    
    # Step 2: Generate chapters (limit for sample)
    max_chapters = 2 if request.story_length == FictionLength.SAMPLE else len(outline.get("chapters", []))
    chapters = []
    context = ""
    
    for i, ch_spec in enumerate(outline.get("chapters", [])[:max_chapters]):
        logger.info(f"Generating chapter {i+1}/{max_chapters}")
        chapter_prompt = f"""Write Chapter: {ch_spec.get('title', f'Chapter {i+1}')}
Synopsis: {ch_spec.get('synopsis', '')}
Previous context: {context[-1000:]}
Write 2000-3000 words in {request.style.value if request.style else 'sarcastic_deadpan'} style."""
        
        content = llm.generate(chapter_prompt, GHOSTWRITER_FICTION, settings.creative_model)
        chapters.append({
            "number": i+1,
            "title": ch_spec.get('title', f'Chapter {i+1}'),
            "content": content
        })
        context = content
    
    # Step 3: Save
    story = Story(
        user_email=request.email,
        story_type="fiction",
        title=outline.get("title", request.title or "Untitled"),
        length_type=request.story_length.value,
        content=json.dumps(chapters),
        metadata=json.dumps({
            "premise": request.premise,
            "style": request.style.value if request.style else "sarcastic_deadpan",
            "genre": request.genre.value if request.genre else None
        }),
        generation_status="complete",
        completed_at=datetime.utcnow()
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    
    return {
        "story_id": story.id,
        "title": story.title,
        "chapters": chapters,
        "word_count": sum(len(ch['content'].split()) for ch in chapters)
    }

def generate_biography(request: BiographyRequest, db: Session) -> Dict:
    """Generate biography"""
    word_counts = {"sample": 2000, "short_memoir": 15000, "standard_biography": 40000, "comprehensive": 80000}
    target = word_counts[request.story_length]
    
    logger.info(f"Generating biography: {request.subject_names}")
    
    # Build detailed prompt
    details = []
    if request.birth_details:
        details.append(f"Birth: {json.dumps(request.birth_details)}")
    if request.family_background:
        details.append(f"Family: {json.dumps(request.family_background)}")
    if request.career:
        details.append(f"Career: {json.dumps(request.career)}")
    if request.major_events:
        details.append(f"Major Events: {json.dumps([e.dict() for e in request.major_events])}")
    if request.personality:
        details.append(f"Personality: {json.dumps(request.personality)}")
    
    bio_prompt = f"""Write a {request.biography_type.value} about: {request.subject_names}
Time Period: {request.time_period_start} to {request.time_period_end}
Target Length: {target} words
Narrative Voice: {request.narrative_voice.value if request.narrative_voice else 'third_person_limited'}

Details provided:
{chr(10).join(details) if details else 'Limited information - infer from context and create plausible, contextually appropriate details'}

Create a compelling life story. Fill in missing details with historically accurate, contextually appropriate content.
Structure as chapters covering different life periods. Make it engaging and human."""
    
    content = llm.generate(bio_prompt, GHOSTWRITER_BIOGRAPHY, settings.biography_model)
    
    # Save
    story = Story(
        user_email=request.email,
        story_type="biography",
        title=f"The Life of {request.subject_names}",
        length_type=request.story_length.value,
        content=content,
        metadata=json.dumps({
            "subject": request.subject_names,
            "type": request.biography_type.value,
            "time_period": f"{request.time_period_start} - {request.time_period_end}"
        }),
        generation_status="complete",
        completed_at=datetime.utcnow()
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    
    return {
        "story_id": story.id,
        "title": story.title,
        "content": content,
        "word_count": len(content.split())
    }

# ===== API ROUTES =====

@app.get("/")
def root():
    return {
        "message": "👻 GhostWriter API - Hauntingly good stories",
        "version": "1.0.0",
        "endpoints": [
            "/api/generate-fiction-sample",
            "/api/generate-biography-sample",
            "/api/create-checkout",
            "/api/create-subscription",
            "/api/story/{story_id}"
        ]
    }

@app.get("/health")
def health_check():
    return {"status": "alive", "llm_provider": settings.llm_provider}

@app.post("/api/generate-fiction-sample")
def fiction_sample(request: FictionRequest, db: Session = Depends(get_db)):
    if request.story_length != FictionLength.SAMPLE:
        raise HTTPException(400, "This endpoint only generates free samples")
    
    try:
        story = generate_fiction(request, db)
        return {"story": story, "message": "Your ghostly tale awaits..."}
    except Exception as e:
        logger.error(f"Fiction generation failed: {str(e)}")
        raise HTTPException(500, f"The spirits are being difficult: {str(e)}")

@app.post("/api/generate-biography-sample")
def biography_sample(request: BiographyRequest, db: Session = Depends(get_db)):
    if request.story_length != BiographyLength.SAMPLE:
        raise HTTPException(400, "This endpoint only generates free samples")
    
    try:
        story = generate_biography(request, db)
        return {"story": story, "message": "Your life story has been summoned..."}
    except Exception as e:
        logger.error(f"Biography generation failed: {str(e)}")
        raise HTTPException(500, f"The spirits are uncooperative: {str(e)}")

@app.post("/api/create-checkout")
def create_checkout(story_type: str, email: str):
    prices = {
        "novella": 999,
        "novel": 1999,
        "short_memoir": 999,
        "standard_biography": 1499,
        "comprehensive": 2499
    }
    
    if story_type not in prices:
        raise HTTPException(400, f"Invalid story type: {story_type}")
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'GhostWriter {story_type.replace("_", " ").title()}',
                        'description': 'AI-generated story with sarcastic wit',
                    },
                    'unit_amount': prices[story_type],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{settings.frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{settings.frontend_url}/cancel',
            customer_email=email,
            metadata={'story_type': story_type}
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(500, f"Payment portal failed: {str(e)}")

@app.post("/api/create-subscription")
def create_subscription(email: str):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'GhostWriter Unlimited',
                        'description': 'Unlimited story generation',
                    },
                    'unit_amount': 2999,
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'{settings.frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{settings.frontend_url}/cancel',
            customer_email=email,
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(500, f"Subscription failed: {str(e)}")

@app.post("/api/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except Exception as e:
        raise HTTPException(400, f"Webhook error: {str(e)}")
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        email = session['customer_email']
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, stripe_customer_id=session['customer'])
            db.add(user)
        
        if session['mode'] == 'subscription':
            user.subscription_status = 'active'
            user.subscription_end = datetime.utcnow() + timedelta(days=30)
        
        user.stories_generated += 1
        db.commit()
    
    return {"status": "success"}

@app.get("/api/story/{story_id}")
def get_story(story_id: int, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(404, "Story vanished into the ether")
    
    content = json.loads(story.content) if story.story_type == "fiction" else story.content
    
    return {
        "story_id": story.id,
        "title": story.title,
        "story_type": story.story_type,
        "content": content,
        "metadata": json.loads(story.metadata),
        "created_at": story.created_at.isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
