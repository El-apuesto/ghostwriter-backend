"""Main FastAPI application with auth and story routes"""
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

# Include auth routes (THIS WAS MISSING - CAUSING 404)
from routes_auth import router as auth_router
app.include_router(auth_router)

# Include story routes
from story_routes import router as story_router
app.include_router(story_router)

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

# Run with: uvicorn main:app --host 0.0.0.0 --port $PORT
