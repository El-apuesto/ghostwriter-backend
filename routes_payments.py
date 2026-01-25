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

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

router = APIRouter(prefix="/api/payments", tags=["payments"])

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
        "description": "Best value for regular users"
    },
    "professional": {
        "credits": 1000,
        "price": 6999,  # $69.99 in cents
        "product_name": "Professional Pack",
        "description": "For serious authors"
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
    
    Frontend should redirect user to the returned checkout_url
    """
    if package not in CREDIT_PACKAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid package. Choose from: {', '.join(CREDIT_PACKAGES.keys())}"
        )
    
    pkg = CREDIT_PACKAGES[package]
    
    try:
        # Get frontend URL from env or default
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        
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
                'user_id': str(current_user.id),
                'credits': str(pkg['credits']),
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
            detail=f"Stripe error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Payment error: {str(e)}"
        )


@router.get("/packages")
async def get_credit_packages():
    """
    Get available credit packages with pricing
    
    Returns packages with prices formatted for display
    """
    formatted_packages = {}
    
    for key, pkg in CREDIT_PACKAGES.items():
        formatted_packages[key] = {
            **pkg,
            "price_display": f"${pkg['price'] / 100:.2f}",
            "price_per_credit": f"${pkg['price'] / 100 / pkg['credits']:.3f}"
        }
    
    return {
        "packages": formatted_packages,
        "currency": "USD"
    }


@router.get("/history")
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's credit purchase history
    
    TODO: Implement transaction history table to track purchases
    For now, returns summary from user model
    """
    return {
        "total_purchased": current_user.total_credits_purchased,
        "total_spent": current_user.total_credits_spent,
        "current_balance": current_user.credits_balance,
        "transactions": []  # TODO: Add Transaction model and query
    }
