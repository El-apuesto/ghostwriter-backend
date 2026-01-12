import os
import json
import logging
from datetime import datetime
from typing import List

import stripe
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session

from config import settings, CREDIT_COSTS, CREDIT_PACKS
from models import Base, User, Story, Transaction, StoryExtra, CreditPack
from schemas import (
    UserSignup, UserLogin, TokenResponse, UserProfile,
    FictionRequest, BiographyRequest,
    StoryResponse, StoryDetail,
    GenerateExtraRequest, ExtraResponse,
    CreditPackPurchase, TransactionHistory
)
from auth import create_access_token, get_current_user
from story_generation import generate_fiction_story, generate_biography_story
from extras_generation import (
    generate_book_cover, generate_epub_export,
    generate_mobi_export, generate_kdp_pdf,
    generate_blurb, generate_author_bio
)
from webhooks import handle_stripe_webhook

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
    title="GhostWriter API v2",
    description="AI-powered story generator with credit system and Llama 70B",
    version="2.0.0"
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

# Initialize credit packs in database
@app.on_event("startup")
def init_credit_packs():
    db = SessionLocal()
    try:
        for pack_key, pack_data in CREDIT_PACKS.items():
            existing = db.query(CreditPack).filter(CreditPack.name == pack_key).first()
            if not existing:
                credit_pack = CreditPack(
                    name=pack_key,
                    price_usd=pack_data["price"] / 100,
                    credits=pack_data["credits"],
                    bonus_percentage=pack_data.get("bonus", 0)
                )
                db.add(credit_pack)
        db.commit()
        logger.info("Credit packs initialized")
    finally:
        db.close()

# ===== ROOT & HEALTH =====

@app.get("/")
def root():
    return {
        "message": "👻 GhostWriter API v2 - Credit System with Llama 70B",
        "version": "2.0.0",
        "features": [
            "User authentication",
            "Credit system (7 packs)",
            "Fiction & Biography generation",
            "Book covers (eBook + Print)",
            "Exports (ePub, MOBI, PDF)",
            "Marketing content (Blurbs, Bios)"
        ],
        "pricing": "100 credits = $12 | Novel = 100 credits"
    }

@app.get("/health")
def health_check():
    return {
        "status": "alive",
        "llm_provider": settings.llm_provider,
        "model": "Llama 3.3 70B"
    }

# ===== AUTHENTICATION =====

@app.post("/api/auth/signup", response_model=TokenResponse)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")
    
    user = User(email=user_data.email, full_name=user_data.full_name)
    user.set_password(user_data.password)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token({"user_id": user.id, "email": user.email})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "credits_balance": user.credits_balance
        }
    }

@app.post("/api/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not user.check_password(credentials.password):
        raise HTTPException(401, "Invalid email or password")
    
    if not user.is_active:
        raise HTTPException(403, "Account is inactive")
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    token = create_access_token({"user_id": user.id, "email": user.email})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "credits_balance": user.credits_balance
        }
    }

@app.get("/api/auth/me", response_model=UserProfile)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return current_user

# ===== CREDITS =====

@app.get("/api/credits/packs")
def get_credit_packs(db: Session = Depends(get_db)):
    return [{"key": k, **v} for k, v in CREDIT_PACKS.items()]

@app.post("/api/credits/purchase")
def purchase_credits(
    pack_request: CreditPackPurchase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pack = CREDIT_PACKS.get(pack_request.pack_type)
    if not pack:
        raise HTTPException(400, "Invalid credit pack")
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"GhostWriter {pack['name']}",
                        'description': f"{pack['credits']} credits for story generation",
                    },
                    'unit_amount': pack['price'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{settings.frontend_url}/dashboard?purchase=success",
            cancel_url=f"{settings.frontend_url}/credits?purchase=cancelled",
            customer_email=current_user.email,
            metadata={
                'user_id': current_user.id,
                'pack_type': pack_request.pack_type,
                'credits': pack['credits']
            }
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(500, f"Payment failed: {str(e)}")

@app.get("/api/credits/balance")
def get_balance(current_user: User = Depends(get_current_user)):
    return {
        "credits_balance": current_user.credits_balance,
        "total_purchased": current_user.total_credits_purchased,
        "total_spent": current_user.total_credits_spent
    }

@app.get("/api/credits/transactions")
def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(desc(Transaction.created_at)).limit(limit).all()
    return transactions

# ===== STORY GENERATION =====

@app.post("/api/generate/fiction")
def create_fiction(
    request: FictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = generate_fiction_story(request, current_user, db)
        return {
            "success": True,
            "story": result,
            "message": f"Your {request.story_length.value} has been summoned!",
            "credits_remaining": current_user.credits_balance
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/generate/biography")
def create_biography(
    request: BiographyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = generate_biography_story(request, current_user, db)
        return {
            "success": True,
            "story": result,
            "message": f"Life story of {request.subject_names} is ready!",
            "credits_remaining": current_user.credits_balance
        }
    except Exception as e:
        raise HTTPException(500, str(e))

# ===== STORY LIBRARY =====

@app.get("/api/stories")
def get_my_stories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    stories = db.query(Story).filter(
        Story.user_id == current_user.id
    ).order_by(desc(Story.created_at)).offset(offset).limit(limit).all()
    return stories

@app.get("/api/stories/{story_id}")
def get_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(404, "Story not found")
    
    # Parse content
    content = json.loads(story.content) if story.story_type == "fiction" else story.content
    metadata = json.loads(story.metadata) if story.metadata else {}
    
    return {
        "id": story.id,
        "title": story.title,
        "story_type": story.story_type,
        "length_type": story.length_type,
        "content": content,
        "metadata": metadata,
        "credits_cost": story.credits_cost,
        "has_ebook_cover": story.has_ebook_cover,
        "has_print_cover": story.has_print_cover,
        "has_epub": story.has_epub,
        "has_mobi": story.has_mobi,
        "has_pdf": story.has_pdf,
        "has_blurb": story.has_blurb,
        "has_author_bio": story.has_author_bio,
        "created_at": story.created_at,
        "completed_at": story.completed_at
    }

@app.delete("/api/stories/{story_id}")
def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(404, "Story not found")
    
    db.delete(story)
    db.commit()
    return {"success": True}

# ===== EXTRAS (COVERS, EXPORTS, MARKETING) =====

@app.post("/api/extras/cover")
def create_cover(
    story_id: int,
    cover_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = generate_book_cover(story_id, cover_type, current_user, db)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/extras/epub/{story_id}")
def create_epub(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = generate_epub_export(story_id, current_user, db)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/extras/mobi/{story_id}")
def create_mobi(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = generate_mobi_export(story_id, current_user, db)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/extras/pdf/{story_id}")
def create_pdf(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = generate_kdp_pdf(story_id, current_user, db)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/extras/blurb/{story_id}")
def create_blurb(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = generate_blurb(story_id, current_user, db)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/extras/author-bio")
def create_author_bio(
    bio_info: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = generate_author_bio(current_user, db, bio_info)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

# ===== STRIPE WEBHOOK =====

@app.post("/api/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        result = await handle_stripe_webhook(request, db)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
