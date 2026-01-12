import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional

import stripe
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session

from config import settings, CREDIT_COSTS, CREDIT_PACKS
from models import Base, User, Story, Transaction, StoryExtra, CreditPack
from schemas import (
    UserSignup, UserLogin, TokenResponse, UserProfile,
    FictionRequest, BiographyRequest, FictionLength, BiographyLength,
    StoryResponse, StoryDetail, GenerateExtraRequest, ExtraResponse,
    CreditPackPurchase, TransactionHistory
)
from auth import create_access_token, get_current_user
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
    description="AI-powered story generator with credit system",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

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
    finally:
        db.close()

# ===== AUTHENTICATION ENDPOINTS =====

@app.post("/api/auth/signup", response_model=TokenResponse)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """Create new user account"""
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")
    
    user = User(
        email=user_data.email,
        full_name=user_data.full_name
    )
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
    """Login and get JWT token"""
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
def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

# ===== CREDIT SYSTEM ENDPOINTS =====

@app.get("/api/credits/packs")
def get_credit_packs(db: Session = Depends(get_db)):
    """Get available credit packs"""
    packs = db.query(CreditPack).filter(CreditPack.is_active == True).all()
    return [{"id": p.id, "name": p.name, "price_usd": p.price_usd, "credits": p.credits, "bonus_percentage": p.bonus_percentage} for p in packs]

@app.post("/api/credits/purchase")
def purchase_credits(
    pack_request: CreditPackPurchase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout for credit purchase"""
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
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        raise HTTPException(500, f"Payment failed: {str(e)}")

@app.get("/api/credits/balance")
def get_credit_balance(current_user: User = Depends(get_current_user)):
    """Get user's current credit balance"""
    return {
        "credits_balance": current_user.credits_balance,
        "total_purchased": current_user.total_credits_purchased,
        "total_spent": current_user.total_credits_spent
    }

@app.get("/api/credits/transactions", response_model=list[TransactionHistory])
def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get user's transaction history"""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(desc(Transaction.created_at)).limit(limit).all()
    
    return transactions

# Continued in next message due to length...
