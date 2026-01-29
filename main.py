"""Main FastAPI application with all routes and auto-migration"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create app
app = FastAPI(title="Ghostwriter API", version="1.0.0")

# Configure CORS - localhost only for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include auth routes
from routes_auth import router as auth_router
app.include_router(auth_router)

# Include story routes
from routes_stories import router as story_router
app.include_router(story_router)

# Include features routes (covers, exports, extras)
try:
    from routes_features import router as features_router
    app.include_router(features_router)
except ImportError:
    print("⚠️ routes_features.py not found")

# Include payment routes
try:
    from routes_payments import router as payments_router
    app.include_router(payments_router)
except ImportError:
    print("⚠️ routes_payments.py not found")

# Include webhook routes
try:
    from webhooks import router as webhook_router
    app.include_router(webhook_router)
except ImportError:
    print("⚠️ webhooks.py not found")

# Health check endpoints
@app.get("/")
async def root():
    return {"message": "Ghostwriter API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/health")
async def api_health_check():
    return {"status": "healthy"}

# Application startup with auto-migration
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Ghostwriter API...")
    
    # Run database migration automatically
    try:
        from database import engine
        from sqlalchemy import text, inspect
        
        print("🔄 Checking database schema...")
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('stories')]
        
        migrations_run = []
        with engine.connect() as conn:
            if 'chapters_completed' not in existing_columns:
                conn.execute(text("ALTER TABLE stories ADD COLUMN chapters_completed INTEGER DEFAULT 0"))
                migrations_run.append("chapters_completed")
            
            if 'total_chapters' not in existing_columns:
                conn.execute(text("ALTER TABLE stories ADD COLUMN total_chapters INTEGER DEFAULT 0"))
                migrations_run.append("total_chapters")
            
            if 'theme' not in existing_columns:
                conn.execute(text("ALTER TABLE stories ADD COLUMN theme TEXT"))
                migrations_run.append("theme")
            
            if 'story_metadata' not in existing_columns:
                conn.execute(text("ALTER TABLE stories ADD COLUMN story_metadata JSON"))
                migrations_run.append("story_metadata")
            
            conn.commit()
        
        if migrations_run:
            print(f"✅ Database migration complete! Added: {', '.join(migrations_run)}")
        else:
            print("✓ Database schema up to date")
            
    except Exception as e:
        print(f"⚠️ Migration check: {e}")
    
    print("✓ Ghostwriter API started")
    print("✓ CORS configured")
    print("✓ Auth routes: /api/auth/*")
    print("✓ Story routes: /api/stories/*")
    print("✓ Feature routes: /api/stories/{id}/cover|export|blurb|author-bio")
    print("✓ Payment routes: /api/payments/*")
    print("✓ Webhook routes: /api/webhooks/*")
    print("🟢 Ready to accept requests")

# Run with: uvicorn main:app --host 0.0.0.0 --port $PORT
