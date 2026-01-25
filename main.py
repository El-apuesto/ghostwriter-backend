"""Main FastAPI application with all routes"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create app
app = FastAPI(title="Ghostwriter API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://ghostwriter-frontend-tawny.vercel.app",
        "https://*.vercel.app",  # Allow all Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
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
from routes_features import router as features_router
app.include_router(features_router)

# Include payment routes
from routes_payments import router as payments_router
app.include_router(payments_router)

# Include webhook routes
from webhooks import router as webhook_router
app.include_router(webhook_router)

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Ghostwriter API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/health")
async def api_health_check():
    return {"status": "healthy"}

# Application startup
@app.on_event("startup")
async def startup_event():
    print("✓ Ghostwriter API started")
    print("✓ CORS configured")
    print("✓ Auth routes available at /api/auth")
    print("✓ Story routes available at /api/stories")
    print("✓ Feature routes available at /api/stories/{id}/cover|export|blurb|author-bio")
    print("✓ Payment routes available at /api/payments")
    print("✓ Webhook routes available at /api/webhooks")

# Run with: uvicorn main:app --host 0.0.0.0 --port $PORT
