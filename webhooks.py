import logging
import stripe
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy import and_

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
        session_id = session['id']
        
        try:
            user_id = session['metadata'].get('user_id')
            pack_type = session['metadata'].get('pack_type')
            credits = int(session['metadata'].get('credits', 0))
            
            if not user_id or not pack_type:
                logger.error(f"Missing metadata in webhook: {session['metadata']}")
                raise HTTPException(400, "Missing metadata")
            
            # Check if transaction already exists (idempotency)
            existing_transaction = db.query(Transaction).filter(
                Transaction.stripe_session_id == session_id,
                Transaction.status == "completed"
            ).first()
            
            if existing_transaction:
                logger.info(f"Transaction already processed: {session_id}")
                return {"status": "success", "message": "Transaction already processed"}
            
            # Get user
            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                logger.error(f"User {user_id} not found")
                raise HTTPException(400, "User not found")
            
            # Validate pack
            pack = CREDIT_PACKS.get(pack_type)
            if not pack:
                logger.error(f"Invalid pack type: {pack_type}")
                raise HTTPException(400, "Invalid pack type")
            
            # Verify credits match
            if credits != pack['credits']:
                logger.error(f"Credit mismatch: expected {pack['credits']}, got {credits}")
                raise HTTPException(400, "Credit amount mismatch")
            
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
                stripe_session_id=session_id,
                status="completed"
            )
            db.add(transaction)
            
            # Commit transaction
            db.commit()
            
            logger.info(f"✓ Payment verified: User {user.id} received {credits} credits | Balance: {user.credits_balance}")
            
            return {
                "status": "success",
                "user_id": user.id,
                "credits_added": credits,
                "new_balance": user.credits_balance,
                "message": "Payment verified and credits added"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing checkout.session.completed: {str(e)}", exc_info=True)
            db.rollback()
            raise HTTPException(500, f"Payment processing error: {str(e)}")
    
    # Handle payment_intent.succeeded
    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        logger.info(f"✓ Payment intent succeeded: {payment_intent['id']}")
        return {"status": "success", "message": "Payment intent received"}
    
    # Handle payment_intent.payment_failed
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        logger.warning(f"✗ Payment failed: {payment_intent['id']}")
        
        # Try to find and mark transaction as failed
        try:
            transaction = db.query(Transaction).filter(
                Transaction.stripe_payment_intent_id == payment_intent['id']
            ).first()
            if transaction:
                transaction.status = "failed"
                db.commit()
                logger.info(f"Transaction marked as failed: {transaction.id}")
        except Exception as e:
            logger.error(f"Error marking transaction as failed: {str(e)}")
            db.rollback()
        
        return {"status": "success", "message": "Payment failure recorded"}
    
    else:
        logger.info(f"Unhandled event type: {event['type']}")
        return {"status": "success", "message": "Event ignored"}
