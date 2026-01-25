# GhostWriter Production Deployment Checklist

## ✅ COMPLETED FEATURES

Your app already has more working than you think:

- ✅ User authentication (JWT tokens)
- ✅ Story generation with chapter-by-chapter iteration (just updated)
- ✅ Biography generation endpoint
- ✅ Cover generation system (`cover_generator.py`)
- ✅ Export system (`export_system.py`) - EPUB/PDF/MOBI
- ✅ Extras generation (`extras_generation.py`) - blurbs/author bios
- ✅ Stripe webhooks handler (`webhooks.py`)
- ✅ Database models with proper relationships
- ✅ Frontend React app with Vite
- ✅ Deployed backend on Render
- ✅ Deployed frontend on Vercel

## 🔧 CRITICAL FIXES NEEDED

### 1. Database Migration (DO THIS FIRST)

**What:** Your Story model just got updated with new fields:
- `chapters_completed` (Integer)
- `total_chapters` (Integer)
- `theme` (Text)
- `metadata` (JSON)

**How to migrate on Render:**

```python
# Create file: migrate_db.py
from database import engine
from models import Base
from sqlalchemy import text

def add_missing_columns():
    with engine.connect() as conn:
        # Add new columns if they don't exist
        try:
            conn.execute(text("ALTER TABLE stories ADD COLUMN chapters_completed INTEGER DEFAULT 0"))
            print("✓ Added chapters_completed")
        except:
            print("chapters_completed already exists")
        
        try:
            conn.execute(text("ALTER TABLE stories ADD COLUMN total_chapters INTEGER DEFAULT 0"))
            print("✓ Added total_chapters")
        except:
            print("total_chapters already exists")
        
        try:
            conn.execute(text("ALTER TABLE stories ADD COLUMN theme TEXT"))
            print("✓ Added theme")
        except:
            print("theme already exists")
        
        try:
            conn.execute(text("ALTER TABLE stories ADD COLUMN metadata JSON"))
            print("✓ Added metadata")
        except:
            print("metadata already exists")
        
        conn.commit()

if __name__ == "__main__":
    add_missing_columns()
    print("\n✅ Database migration complete!")
```

**Run on Render:**
1. Push this file to your repo
2. In Render dashboard, go to Shell
3. Run: `python migrate_db.py`

### 2. Wire Up Existing Features to Routes

You already have the code for covers, exports, and extras - just need to add routes!

**Create `routes_features.py`:**

```python
"""
Routes for covers, exports, and extras
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from auth import get_current_user
from models import User, Story

# Import your existing modules
from cover_generator import generate_basic_cover, generate_ai_cover, generate_print_cover
from export_system import export_to_epub, export_to_pdf, export_to_mobi
from extras_generation import generate_blurb, generate_author_bio

router = APIRouter(prefix="/api", tags=["features"])


# COVER GENERATION
@router.post("/stories/{story_id}/cover/basic")
async def create_basic_cover(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate basic programmatic cover (free)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.status != 'completed':
        raise HTTPException(status_code=400, detail="Story must be completed first")
    
    # Generate cover using existing function
    cover_path = generate_basic_cover(story.title, story.genre or "Fiction")
    
    return {"success": True, "cover_url": cover_path}


@router.post("/stories/{story_id}/cover/ai")
async def create_ai_cover(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI cover with Grok-2 (10 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Check credits
    if current_user.credits_balance < 10:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 10)")
    
    # Deduct credits
    current_user.deduct_credits(10)
    db.commit()
    
    # Generate AI cover
    cover_options = generate_ai_cover(story.title, story.content[:1000], story.genre)
    
    return {"success": True, "covers": cover_options, "credits_charged": 10}


@router.post("/stories/{story_id}/cover/print")
async def create_print_cover(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate print-ready cover with spine (15 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Check credits
    if current_user.credits_balance < 15:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 15)")
    
    # Deduct credits
    current_user.deduct_credits(15)
    db.commit()
    
    # Generate print cover
    cover_path = generate_print_cover(story.title, story.word_count)
    
    return {"success": True, "cover_url": cover_path, "credits_charged": 15}


# EXPORTS
@router.post("/stories/{story_id}/export/epub")
async def export_epub(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export to EPUB (5 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if current_user.credits_balance < 5:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 5)")
    
    current_user.deduct_credits(5)
    db.commit()
    
    file_path = export_to_epub(story)
    
    return {"success": True, "download_url": file_path, "credits_charged": 5}


@router.post("/stories/{story_id}/export/pdf")
async def export_pdf(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export to PDF for KDP (10 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if current_user.credits_balance < 10:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 10)")
    
    current_user.deduct_credits(10)
    db.commit()
    
    file_path = export_to_pdf(story)
    
    return {"success": True, "download_url": file_path, "credits_charged": 10}


@router.post("/stories/{story_id}/export/mobi")
async def export_mobi(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export to MOBI (5 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if current_user.credits_balance < 5:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 5)")
    
    current_user.deduct_credits(5)
    db.commit()
    
    file_path = export_to_mobi(story)
    
    return {"success": True, "download_url": file_path, "credits_charged": 5}


# EXTRAS
@router.post("/stories/{story_id}/blurb")
async def create_blurb(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate marketing blurb (5 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if current_user.credits_balance < 5:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 5)")
    
    current_user.deduct_credits(5)
    db.commit()
    
    blurb = generate_blurb(story.content, story.genre)
    
    return {"success": True, "blurb": blurb, "credits_charged": 5}


@router.post("/stories/{story_id}/author-bio")
async def create_author_bio(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate author bio (3 credits)"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user.id
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if current_user.credits_balance < 3:
        raise HTTPException(status_code=402, detail="Insufficient credits (need 3)")
    
    current_user.deduct_credits(3)
    db.commit()
    
    bio = generate_author_bio(current_user.full_name, story.genre)
    
    return {"success": True, "author_bio": bio, "credits_charged": 3}
```

**Add to `main.py`:**

```python
# Add after story_router
from routes_features import router as features_router
app.include_router(features_router)
```

### 3. Stripe Integration

You already have `webhooks.py` - just need to wire it up and add checkout routes.

**Add to `main.py`:**

```python
from webhooks import router as webhook_router
app.include_router(webhook_router)
```

**Create `routes_payments.py`:**

```python
"""
Stripe payment routes
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
    "starter": {"credits": 100, "price": 999, "product_name": "Starter Pack"},
    "creator": {"credits": 300, "price": 2499, "product_name": "Creator Pack"},
    "professional": {"credits": 1000, "price": 6999, "product_name": "Professional Pack"},
}


@router.post("/create-checkout-session")
async def create_checkout_session(
    package: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session for credit purchase"""
    
    if package not in CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    pkg = CREDIT_PACKAGES[package]
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': pkg['product_name'],
                        'description': f"{pkg['credits']} GhostWriter credits",
                    },
                    'unit_amount': pkg['price'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=os.getenv('FRONTEND_URL') + '/credits?success=true',
            cancel_url=os.getenv('FRONTEND_URL') + '/credits?canceled=true',
            client_reference_id=str(current_user.id),
            metadata={
                'user_id': current_user.id,
                'credits': pkg['credits'],
                'package': package
            }
        )
        
        return {"checkout_url": checkout_session.url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/packages")
async def get_credit_packages():
    """Get available credit packages"""
    return CREDIT_PACKAGES
```

**Add to `main.py`:**

```python
from routes_payments import router as payments_router
app.include_router(payments_router)
```

### 4. Environment Variables

Add these to your Render environment:

```bash
# Already have:
GROQ_API_KEY=your_key
DATABASE_URL=your_postgres_url
JWT_SECRET_KEY=your_secret

# Need to add:
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
XAI_API_KEY=your_grok_key  # For AI covers
FRONTEND_URL=https://ghostwriter-frontend-tawny.vercel.app
```

### 5. Biography Chapter Generation

Update `routes_stories.py` to use iterative generation for biographies too:

**Replace the `generate_biography_content` function with:**

```python
def generate_biography_content(db: Session, story_id: int):
    """
    Background task to generate biography with chapter iteration
    """
    from story_generation import generate_chapter, generate_chapter_outline
    from groq import Groq
    import os
    
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        return
    
    try:
        story.status = 'generating'
        db.commit()
        
        # Determine chapter structure
        length_config = {
            'sample': {'words': 1500, 'chapters': 1, 'words_per_chapter': 1500},
            'short_memoir': {'words': 30000, 'chapters': 5, 'words_per_chapter': 6000},
            'standard_biography': {'words': 70000, 'chapters': 10, 'words_per_chapter': 7000},
            'comprehensive': {'words': 100000, 'chapters': 15, 'words_per_chapter': 6667}
        }
        
        config = length_config.get(story.length, length_config['sample'])
        
        # Build comprehensive prompt from all biography fields
        theme = build_biography_theme(story)
        
        # Generate chapter outline
        chapter_outline = generate_chapter_outline(
            subject=theme,
            genre='Biography',
            num_chapters=config['chapters'],
            total_words=config['words']
        )
        
        # Generate chapters iteratively
        all_chapters = []
        context_summary = ""
        
        for i, chapter_info in enumerate(chapter_outline):
            chapter_content = generate_chapter(
                chapter_title=chapter_info['title'],
                subject=theme + f"\n\nChapter focus: {chapter_info['summary']}",
                genre='Biography',
                style='truthful and narrative-driven',
                context_summary=context_summary,
                target_word_count=config['words_per_chapter']
            )
            
            all_chapters.append(chapter_content)
            
            # Update context
            words = chapter_content.split()
            context_summary = ' '.join(words[-512:])
            
            # Save progress
            story.content = '\n\n---\n\n'.join(all_chapters)
            story.chapters_completed = i + 1
            story.total_chapters = config['chapters']
            story.word_count = len(story.content.split())
            db.commit()
        
        # Generate title if needed
        if not story.title:
            client = Groq(api_key=os.getenv('GROQ_API_KEY'))
            title_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Create 2-6 word biography title"},
                    {"role": "user", "content": f"Title for: {all_chapters[0][:500]}"}
                ],
                temperature=0.7,
                max_tokens=20
            )
            story.title = title_response.choices[0].message.content.strip().strip('"').strip("'")
        
        story.status = 'completed'
        story.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        story.status = 'failed'
        story.error_message = str(e)
        db.commit()


def build_biography_theme(story: Story) -> str:
    """Build comprehensive theme from biography fields"""
    parts = [
        f"Write a {story.biography_type} about {story.subject_names}.",
        f"Time period: {story.time_period_start} to {story.time_period_end}."
    ]
    
    if story.birth_details:
        bd = story.birth_details
        if bd.get('date') or bd.get('place'):
            parts.append(f"Born: {bd.get('date', '')} in {bd.get('place', '')}")
    
    if story.family_background:
        parts.append(f"Family: {story.family_background.get('text', '')[:200]}")
    
    if story.career:
        parts.append(f"Career: {story.career.get('text', '')[:200]}")
    
    if story.achievements:
        parts.append(f"Achievements: {story.achievements.get('text', '')[:200]}")
    
    if story.themes:
        parts.append(f"Themes: {', '.join(story.themes)}")
    
    voice = story.narrative_voice or 'third_person_limited'
    tone = story.tone or 'balanced and respectful'
    parts.append(f"Voice: {voice.replace('_', ' ')}. Tone: {tone}.")
    
    return '\n'.join(parts)
```

## 📋 PRODUCTION DEPLOYMENT STEPS

### Step 1: Database Migration
1. Push updated `models.py` to GitHub (already done)
2. Create and push `migrate_db.py` (see above)
3. Run migration on Render Shell

### Step 2: Add New Routes
1. Create `routes_features.py` and `routes_payments.py`
2. Update `main.py` to include new routers
3. Update `routes_stories.py` with iterative biography generation
4. Push to GitHub

### Step 3: Configure Stripe
1. Create Stripe account
2. Get API keys (test mode first)
3. Add environment variables to Render
4. Configure webhook endpoint: `https://your-app.onrender.com/api/webhooks/stripe`

### Step 4: Test Everything
1. Test fiction generation (short, medium, long)
2. Test biography generation
3. Test credit purchases
4. Test cover generation
5. Test exports
6. Test extras

### Step 5: Frontend Updates

Add these API functions to `src/utils/api.js`:

```javascript
// Covers
export const coversAPI = {
  generateBasic: (storyId) => api.post(`/stories/${storyId}/cover/basic`),
  generateAI: (storyId) => api.post(`/stories/${storyId}/cover/ai`),
  generatePrint: (storyId) => api.post(`/stories/${storyId}/cover/print`),
};

// Exports
export const exportsAPI = {
  toEPUB: (storyId) => api.post(`/stories/${storyId}/export/epub`),
  toPDF: (storyId) => api.post(`/stories/${storyId}/export/pdf`),
  toMOBI: (storyId) => api.post(`/stories/${storyId}/export/mobi`),
};

// Extras
export const extrasAPI = {
  generateBlurb: (storyId) => api.post(`/stories/${storyId}/blurb`),
  generateAuthorBio: (storyId) => api.post(`/stories/${storyId}/author-bio`),
};

// Payments
export const paymentsAPI = {
  getPackages: () => api.get('/payments/packages'),
  createCheckout: (packageName) => api.post('/payments/create-checkout-session', { package: packageName }),
};
```

## 🚀 NICE-TO-HAVES (Not Critical)

- [ ] Email notifications for completed stories
- [ ] Real-time progress with WebSockets
- [ ] Error tracking (Sentry)
- [ ] Rate limiting
- [ ] Automated tests
- [ ] CI/CD pipeline
- [ ] Caching layer
- [ ] Background job queue (Celery)

## 📊 CURRENT STATUS

**Backend:**
- Story generation: ✅ Working (just upgraded)
- Biography generation: ✅ Working (needs upgrade)
- Authentication: ✅ Working
- Database: ✅ Working (needs migration)
- Cover system: ✅ Code exists (needs routes)
- Export system: ✅ Code exists (needs routes)
- Extras system: ✅ Code exists (needs routes)
- Payments: ⚠️ Webhook exists (needs checkout routes)

**Frontend:**
- UI: ✅ Working
- Auth: ✅ Working
- Story creation: ✅ Working
- Biography form: ✅ Working
- Story detail: ⚠️ Missing feature buttons
- Credits page: ⚠️ Hardcoded URLs

## 🎯 MINIMUM VIABLE PRODUCT

To launch, you ONLY need:

1. ✅ Database migration (5 minutes)
2. ✅ Wire up existing features to routes (30 minutes)
3. ✅ Add Stripe checkout routes (15 minutes)
4. ✅ Add environment variables (5 minutes)
5. ✅ Update frontend API calls (20 minutes)
6. ✅ Test end-to-end (30 minutes)

**Total time to production: ~2 hours**

## 💡 NEXT ACTIONS

1. Run database migration
2. Create `routes_features.py`
3. Create `routes_payments.py`
4. Update `main.py` to include new routers
5. Set up Stripe account and get keys
6. Add environment variables to Render
7. Update frontend API utils
8. Deploy and test

**You're way closer than you thought! Most of the hard work is already done.**
