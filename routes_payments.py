"""
Stripe payment routes for credit purchases
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import stripe
import os

from database import get_db
from auth import get_current_user
from models import User

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Credit package definitions
CREDIT_PACKAGES = {
    "starter": {
        "credits": 100,
        "price": 999,  # $9.99 in cents
        "product_name": "Starter Pack",
        "description": "Perfect for trying out GhostWriter"
    },
    "creator": {
        "credits": 300,
        "price": 2499,  # $24.99 in cents
        "product_name": "Creator Pack",
        "description": "Best value for regular writers"
    },
    "professional": {
        "credits": 1000,
        "price": 6999,  # $69.99 in cents
        "product_name": "Professional Pack",
        "description": "For serious authors and publishers"
    },
}


@router.get("/packages")
async def get_credit_packages():
    """
    Get available credit packages
    
    Returns pricing and credit amounts for all available packages.
    """
    return {
        "packages": CREDIT_PACKAGES,
        "currency": "USD"
    }


@router.post("/create-checkout-session")
async def create_checkout_session(
    package: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create Stripe checkout session for credit purchase
    
    Args:
        package: Package name (starter, creator, or professional)
    
    Returns:
        Checkout URL for Stripe payment page
    """
    
    # Validate package
    if package not in CREDIT_PACKAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid package. Choose from: {', '.join(CREDIT_PACKAGES.keys())}"
        )
    
    pkg = CREDIT_PACKAGES[package]
    
    # Check if Stripe is configured
    if not stripe.api_key:
        raise HTTPException(
            status_code=500,
            detail="Payment system not configured. Please contact support."
        )
    
    # Get frontend URL from environment
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    
    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': pkg['product_name'],
                        'description': f"{pkg['credits']} GhostWriter credits - {pkg['description']}",
                    },
                    'unit_amount': pkg['price'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{frontend_url}/credits?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/credits?canceled=true",
            client_reference_id=str(current_user.id),
            metadata={
                'user_id': current_user.id,
                'user_email': current_user.email,
                'credits': pkg['credits'],
                'package': package
            }
        )
        
        return {
            "success": True,
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Payment system error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Checkout creation failed: {str(e)}"
        )


@router.get("/verify-session/{session_id}")
async def verify_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Verify a Stripe checkout session
    
    Used by frontend to confirm payment completion.
    """
    
    if not stripe.api_key:
        raise HTTPException(
            status_code=500,
            detail="Payment system not configured"
        )
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Verify this session belongs to the current user
        if session.client_reference_id != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail="This session does not belong to you"
            )
        
        return {
            "success": True,
            "payment_status": session.payment_status,
            "amount_total": session.amount_total,
            "credits": session.metadata.get('credits'),
            "package": session.metadata.get('package')
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Session verification failed: {str(e)}"
        )
