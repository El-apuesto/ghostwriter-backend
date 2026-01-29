"""
Authentication routes for user signup and login
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserSignup, UserLogin, TokenResponse
from auth import create_access_token, get_current_user
import bcrypt
import secrets
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/signup", response_model=TokenResponse)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """
    Create new user account
    
    - Email must be unique
    - Password must be at least 8 characters
    - Returns JWT token and user info
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered. The ghosts remember you."
        )
    
    try:
        # Create new user
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            is_active=True,
            credits_balance=0,  # New users start with 0 credits
            total_credits_purchased=0,
            total_credits_spent=0
        )
        user.set_password(user_data.password)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create access token
        access_token = create_access_token(
            data={"user_id": user.id, "email": user.email}
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "credits_balance": user.credits_balance
            }
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create account: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login user
    
    - Validates email and password
    - Returns JWT token and user info
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password. The ghosts don't recognize you."
        )
    
    # Check password
    if not user.check_password(credentials.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password. The spirits are unconvinced."
        )
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is inactive. Your ghost has been exorcised."
        )
    
    try:
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create access token
        access_token = create_access_token(
            data={"user_id": user.id, "email": user.email}
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "credits_balance": user.credits_balance
            }
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me")
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user profile
    
    Requires valid JWT token in Authorization header
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "credits_balance": current_user.credits_balance,
        "total_credits_purchased": current_user.total_credits_purchased,
        "total_credits_spent": current_user.total_credits_spent,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }


@router.post("/forgot-password")
async def forgot_password(email_data: dict, db: Session = Depends(get_db)):
    """
    Send password reset link to user's email
    """
    email = email_data.get("email")
    
    # Check if user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token (valid for 1 hour)
    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    
    # For now, just return success (you can add email sending later)
    return {"message": "Password reset link has been sent to your email"}


@router.post("/reset-password")
async def reset_password(reset_data: dict, db: Session = Depends(get_db)):
    """
    Reset password using token
    """
    token = reset_data.get("token")
    new_password = reset_data.get("password")
    
    # Find user with valid token
    user = db.query(User).filter(
        User.reset_token == token,
        User.reset_token_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Update password
    user.set_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return {"message": "Password has been reset successfully"}
