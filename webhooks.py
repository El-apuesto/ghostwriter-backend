import logging
import stripe
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from config import settings, CREDIT_PACKS
from models import User, Transaction

logger = logging.getLogger(__name__)

async def handle_stripe_webhook(request: Request, db: Session):
    """Handle Stripe webhook events"""
    
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        raise HTTPException(400, "Invalid signature")
    
    # Handle checkout.session.completed
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        user_id = session['metadata'].get('user_id')
        pack_type = session['metadata'].get('pack_type')
        credits = int(session['metadata'].get('credits', 0))
        
        if not user_id or not pack_type:
            logger.error(f"Missing metadata in webhook: {session['metadata']}")
            return {"status": "error", "message": "Missing metadata"}
        
        # Get user
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return {"status": "error", "message": "User not found"}
        
        # Get pack details
        pack = CREDIT_PACKS.get(pack_type)
        if not pack:
            logger.error(f"Invalid pack type: {pack_type}")
            return {"status": "error", "message": "Invalid pack type"}
        
        # Add credits to user
        user.add_credits(credits)
        
        # Update Stripe customer ID if not set
        if not user.stripe_customer_id:
            user.stripe_customer_id = session.get('customer')
        
        # Create transaction record
        transaction = Transaction(
            user_id=user.id,
            transaction_type="credit_purchase",
            amount_usd=pack['price'] / 100,  # Convert cents to dollars
            credits_amount=credits,
            description=f"Purchased {pack['name']} ({credits} credits)",
            stripe_payment_intent_id=session.get('payment_intent'),
            stripe_session_id=session['id'],
            status="completed"
        )
        db.add(transaction)
        
        db.commit()
        
        logger.info(f"Credits added: User {user.id} received {credits} credits")
        
        return {
            "status": "success",
            "user_id": user.id,
            "credits_added": credits,
            "new_balance": user.credits_balance
        }
    
    # Handle payment_intent.succeeded
    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        logger.info(f"Payment succeeded: {payment_intent['id']}")
        return {"status": "received"}
    
    # Handle payment_intent.payment_failed
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        logger.warning(f"Payment failed: {payment_intent['id']}")
        return {"status": "payment_failed"}
    
    else:
        logger.info(f"Unhandled event type: {event['type']}")
        return {"status": "ignored"}
