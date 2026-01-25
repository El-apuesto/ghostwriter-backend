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

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Initialize Stripe with API key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Credit packages configuration
CREDIT_PACKAGES = {
    "starter": {
        "credits": 100,
        "price": 999,  # $9.99 in cents
        "product_name": "Starter Pack",
        "description": "100 credits - Perfect for trying GhostWriter"
    },
    "creator": {
        "credits": 300,
        "price": 2499,  # $24.99 in cents
        "product_name": "Creator Pack",
        "description": "300 credits - Best value for regular creators"
    },
    "professional": {
        "credits": 1000,
        "price": 6999,  # $69.99 in cents
        "product_name": "Professional Pack",
        "description": "1000 credits - For serious authors"
    },
}


@router.post("/create-checkout-session")
async def create_checkout_session(
    package: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create Stripe checkout session for credit purchase
    
    Returns a checkout URL that redirects user to Stripe payment page.
    After successful payment, webhook will add credits to user account.
    """
    
    if package not in CREDIT_PACKAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid package. Choose from: {', '.join(CREDIT_PACKAGES.keys())}"
        )
    
    pkg = CREDIT_PACKAGES[package]
    
    try:
        # Get frontend URL from environment
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': pkg['product_name'],
                        'description': pkg['description'],
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
                'credits': pkg['credits'],
                'package': package,
                'user_email': current_user.email
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
            detail=f"Stripe error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create checkout session: {str(e)}"
        )


@router.get("/packages")
async def get_credit_packages():
    """
    Get available credit packages with pricing
    
    Returns all available credit packages for display on frontend.
    """
    return {
        "success": True,
        "packages": CREDIT_PACKAGES
    }


@router.get("/session/{session_id}")
async def get_checkout_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a checkout session
    
    Used to verify payment status after redirect from Stripe.
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Verify this session belongs to current user
        if session.client_reference_id != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail="This checkout session doesn't belong to you"
            )
        
        return {
            "success": True,
            "status": session.payment_status,
            "amount_total": session.amount_total,
            "credits": session.metadata.get('credits'),
            "package": session.metadata.get('package')
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve session: {str(e)}"
        )


@router.get("/balance")
async def get_credit_balance(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's credit balance
    """
    return {
        "success": True,
        "balance": current_user.credits_balance,
        "total_purchased": current_user.total_credits_purchased,
        "total_spent": current_user.total_credits_spent
    }
