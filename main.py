"""
Main FastAPI application with CORS, Auth, and Story routes
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes_auth import router as auth_router
from routes_stories import router as story_router

# Create app
app = FastAPI(title="Ghostwriter API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://ghostwriter-frontend-tawny.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)      # /api/auth/*
app.include_router(story_router)     # /api/stories/*

# Health check endpoints
@app.get("/")
async def root():
    return {"message": "Ghostwriter API is running", "status": "alive"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "ghostwriter-backend"}

# Application startup
@app.on_event("startup")
async def startup_event():
    print("✓ Ghostwriter API started")
    print("✓ CORS configured for Vercel frontend")
    print("✓ Auth routes available at /api/auth")
    print("✓ Story routes available at /api/stories")

# Run with: uvicorn main:app --host 0.0.0.0 --port $PORT
