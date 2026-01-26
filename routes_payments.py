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
        "description": "100 credits - Perfect for getting started"
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


@router.get("/packages")
async def get_credit_packages():
    """Get available credit packages"""
    return {
        "packages": CREDIT_PACKAGES,
        "pricing": {
            package: {
                "credits": data["credits"],
                "price_usd": data["price"] / 100,
                "name": data["product_name"],
                "description": data["description"]
            }
            for package, data in CREDIT_PACKAGES.items()
        }
    }


@router.post("/create-checkout-session")
async def create_checkout_session(
    package: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session for credit purchase"""
    
    if package not in CREDIT_PACKAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid package. Choose from: {', '.join(CREDIT_PACKAGES.keys())}"
        )
    
    pkg = CREDIT_PACKAGES[package]
    
    # Check if Stripe is configured
    if not stripe.api_key or stripe.api_key == "your_stripe_secret_key":
        raise HTTPException(
            status_code=503,
            detail="Payment system not configured. Please contact support."
        )
    
    try:
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
            success_url=os.getenv('FRONTEND_URL', 'http://localhost:3000') + '/credits?success=true&session_id={CHECKOUT_SESSION_ID}',
            cancel_url=os.getenv('FRONTEND_URL', 'http://localhost:3000') + '/credits?canceled=true',
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
            detail=f"Payment processing error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create checkout session: {str(e)}"
        )


@router.get("/verify-session/{session_id}")
async def verify_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Verify a checkout session and return status"""
    
    if not stripe.api_key or stripe.api_key == "your_stripe_secret_key":
        raise HTTPException(
            status_code=503,
            detail="Payment system not configured"
        )
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        return {
            "success": True,
            "status": session.payment_status,
            "amount_total": session.amount_total / 100 if session.amount_total else 0,
            "customer_email": session.customer_details.email if session.customer_details else None
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify session: {str(e)}"
        )
