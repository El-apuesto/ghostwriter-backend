from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import bcrypt

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    
    # Credits system
    credits_balance = Column(Integer, default=0)
    total_credits_purchased = Column(Integer, default=0)
    total_credits_spent = Column(Integer, default=0)
    
    # Account status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    
    # Stripe
    stripe_customer_id = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    stories = relationship("Story", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    
    def set_password(self, password: str):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Verify password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def add_credits(self, amount: int):
        """Add credits to user balance"""
        self.credits_balance += amount
        self.total_credits_purchased += amount
    
    def deduct_credits(self, amount: int) -> bool:
        """Deduct credits if user has enough"""
        if self.credits_balance >= amount:
            self.credits_balance -= amount
            self.total_credits_spent += amount
            return True
        return False


class Story(Base):
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Story details
    story_type = Column(String)  # fiction, biography
    title = Column(String)
    length_type = Column(String)  # sample, novella, novel, etc.
    content = Column(Text)  # JSON string for chapters or full text
    metadata = Column(Text)  # JSON string with premise, style, genre, etc.
    
    # Generation
    generation_status = Column(String, default="pending")  # pending, generating, complete, error
    credits_cost = Column(Integer, default=0)
    
    # Extras generated
    has_ebook_cover = Column(Boolean, default=False)
    has_print_cover = Column(Boolean, default=False)
    has_epub = Column(Boolean, default=False)
    has_mobi = Column(Boolean, default=False)
    has_pdf = Column(Boolean, default=False)
    has_blurb = Column(Boolean, default=False)
    has_author_bio = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="stories")
    extras = relationship("StoryExtra", back_populates="story")


class StoryExtra(Base):
    __tablename__ = "story_extras"
    
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=False)
    
    extra_type = Column(String)  # ebook_cover, print_cover, epub, mobi, pdf, blurb, author_bio
    content = Column(Text)  # File path, URL, or text content
    credits_cost = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    story = relationship("Story", back_populates="extras")


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Transaction details
    transaction_type = Column(String)  # credit_purchase, story_generation, extra_generation
    amount_usd = Column(Float, nullable=True)  # For purchases
    credits_amount = Column(Integer)  # Credits added or spent
    description = Column(String)
    
    # Stripe
    stripe_payment_intent_id = Column(String, nullable=True)
    stripe_session_id = Column(String, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # pending, completed, failed, refunded
    
    # Related story if applicable
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="transactions")


class CreditPack(Base):
    __tablename__ = "credit_packs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)  # Micro, Small, Medium, Starter, Value, Pro, Ultimate
    price_usd = Column(Float)
    credits = Column(Integer)
    bonus_percentage = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    stripe_price_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
