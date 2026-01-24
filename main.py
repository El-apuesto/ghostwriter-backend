"""
Complete main.py with CORS and Story Routes integrated
Replace your entire main.py with this file
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from story_routes import router as story_router

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

# Include story routes
from story_routes import router as story_router
app.include_router(story_router)

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Ghostwriter API is running"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

# Application startup
@app.on_event("startup")
async def startup_event():
    print("✓ Ghostwriter API started")
    print("✓ CORS configured")
    print("✓ Story routes available at /api/stories")

# Run with: uvicorn main:app --host 0.0.0.0 --port $PORT
