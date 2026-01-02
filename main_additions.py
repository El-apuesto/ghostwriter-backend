# ADD THESE IMPORTS TO MAIN.PY AT THE TOP:
from auth import create_access_token, get_current_user
from models import User, Story, Transaction, StoryExtra, CreditPack
from schemas import (
    UserSignup, UserLogin, TokenResponse, UserProfile,
    GenerateExtraRequest, ExtraResponse, CreditPackPurchase,
    TransactionHistory, StoryDetail
)

# ADD THESE CREDIT COSTS CONSTANTS AFTER IMPORTS:
CREDIT_COSTS = {
    "fiction": {"sample": 0, "novella": 50, "novel": 100},
    "biography": {"sample": 0, "short_memoir": 50, "standard_biography": 75, "comprehensive": 125},
    "extras": {
        "ebook_cover": 10,
        "print_cover": 15,
        "epub_export": 5,
        "mobi_export": 5,
        "kdp_pdf": 10,
        "blurb": 5,
        "author_bio": 3
    }
}

CREDIT_PACKS = {
    "micro": {"price": 5.00, "credits": 20},
    "small": {"price": 10.00, "credits": 40},
    "medium": {"price": 15.00, "credits": 60},
    "starter": {"price": 25.00, "credits": 100},
    "value": {"price": 60.00, "credits": 250},
    "pro": {"price": 120.00, "credits": 550},
    "ultimate": {"price": 240.00, "credits": 1200}
}

# ===== AUTHENTICATION ENDPOINTS =====

@app.post("/api/auth/signup", response_model=TokenResponse)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """Create new user account"""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name
    )
    user.set_password(user_data.password)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create token
    access_token = create_access_token(data={"user_id": user.id, "email": user.email})
    
    return TokenResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "credits_balance": user.credits_balance
        }
    )

@app.post("/api/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not user.check_password(credentials.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password. The ghosts refuse to let you in."
        )
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create token
    access_token = create_access_token(data={"user_id": user.id, "email": user.email})
    
    return TokenResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "credits_balance": user.credits_balance
        }
    )

@app.get("/api/auth/me", response_model=UserProfile)
def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

# ===== CREDIT ENDPOINTS =====

@app.get("/api/credits/balance")
def get_credit_balance(current_user: User = Depends(get_current_user)):
    """Get user's credit balance"""
    return {
        "credits_balance": current_user.credits_balance,
        "total_purchased": current_user.total_credits_purchased,
        "total_spent": current_user.total_credits_spent
    }

@app.get("/api/credits/packs")
def get_credit_packs():
    """Get available credit packs"""
    return {
        "packs": [
            {"id": k, "name": k.title(), "price": v["price"], "credits": v["credits"]}
            for k, v in CREDIT_PACKS.items()
        ]
    }

@app.post("/api/credits/purchase")
def purchase_credits(
    pack_data: CreditPackPurchase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout for credit purchase"""
    if pack_data.pack_type not in CREDIT_PACKS:
        raise HTTPException(400, "Invalid credit pack")
    
    pack = CREDIT_PACKS[pack_data.pack_type]
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{pack_data.pack_type.title()} Credit Pack',
                        'description': f'{pack["credits"]} credits for GhostWriter',
                    },
                    'unit_amount': int(pack["price"] * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{settings.frontend_url}/dashboard?credits_added=true',
            cancel_url=f'{settings.frontend_url}/dashboard?credits_cancelled=true',
            customer_email=current_user.email,
            metadata={
                'user_id': current_user.id,
                'pack_type': pack_data.pack_type,
                'credits': pack["credits"]
            }
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(500, f"Payment failed: {str(e)}")

@app.get("/api/transactions", response_model=List[TransactionHistory])
def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get user's transaction history"""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.created_at.desc()).limit(limit).all()
    
    return transactions

# ===== STORY ENDPOINTS (CREDIT-GATED) =====

@app.post("/api/generate/fiction")
def generate_fiction_with_credits(
    request: FictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate fiction story (requires credits)"""
    credits_required = CREDIT_COSTS["fiction"][request.story_length.value]
    
    # Check if sample (free)
    if request.story_length.value == "sample":
        story = generate_fiction(request, db, current_user.id)
        return {"story": story, "message": "Your free sample awaits..."}
    
    # Check credits
    if current_user.credits_balance < credits_required:
        raise HTTPException(
            400,
            f"Insufficient credits. Need {credits_required}, have {current_user.credits_balance}"
        )
    
    # Deduct credits
    if not current_user.deduct_credits(credits_required):
        raise HTTPException(400, "Failed to deduct credits")
    
    # Generate story
    try:
        story = generate_fiction(request, db, current_user.id)
        
        # Log transaction
        transaction = Transaction(
            user_id=current_user.id,
            transaction_type="story_generation",
            credits_amount=-credits_required,
            description=f"Generated {request.story_length.value} fiction",
            status="completed",
            story_id=story["story_id"]
        )
        db.add(transaction)
        db.commit()
        
        return {"story": story, "credits_remaining": current_user.credits_balance}
    
    except Exception as e:
        # Refund credits on error
        current_user.add_credits(credits_required)
        db.commit()
        raise HTTPException(500, f"Generation failed: {str(e)}")

@app.post("/api/generate/biography")
def generate_biography_with_credits(
    request: BiographyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate biography (requires credits)"""
    credits_required = CREDIT_COSTS["biography"][request.story_length.value]
    
    # Check if sample (free)
    if request.story_length.value == "sample":
        story = generate_biography(request, db, current_user.id)
        return {"story": story, "message": "Your free biography sample awaits..."}
    
    # Check credits
    if current_user.credits_balance < credits_required:
        raise HTTPException(
            400,
            f"Insufficient credits. Need {credits_required}, have {current_user.credits_balance}"
        )
    
    # Deduct credits
    current_user.deduct_credits(credits_required)
    
    # Generate biography
    try:
        story = generate_biography(request, db, current_user.id)
        
        # Log transaction
        transaction = Transaction(
            user_id=current_user.id,
            transaction_type="story_generation",
            credits_amount=-credits_required,
            description=f"Generated {request.story_length.value} biography",
            status="completed",
            story_id=story["story_id"]
        )
        db.add(transaction)
        db.commit()
        
        return {"story": story, "credits_remaining": current_user.credits_balance}
    
    except Exception as e:
        # Refund credits on error
        current_user.add_credits(credits_required)
        db.commit()
        raise HTTPException(500, f"Generation failed: {str(e)}")

@app.get("/api/stories", response_model=List[StoryResponse])
def get_user_stories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all stories for current user"""
    stories = db.query(Story).filter(
        Story.user_id == current_user.id
    ).order_by(Story.created_at.desc()).all()
    
    return stories

@app.get("/api/stories/{story_id}", response_model=StoryDetail)
def get_story_detail(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed story with all extras"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(404, "Story not found")
    
    return story
