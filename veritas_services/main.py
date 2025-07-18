# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from veritas_services.api.endpoints import jobs # Import your jobs router
from dotenv import load_dotenv

load_dotenv()
# Initialize FastAPI app
app = FastAPI(
    title="AI Interview Agent API",
    description="Backend API for the personalized AI Interview Agent.",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc"
)

# --- CORS Configuration ---
# This is crucial for your React frontend to communicate with this backend.
# Adjust `allow_origins` in a production environment to be more restrictive.
origins = [
    "http://localhost",
    "http://localhost:3000",  # Assuming your React app runs on port 3000
    # Add your frontend's production URL here when deployed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- Include API Routers ---
app.include_router(jobs.router, prefix="/api/v1", tags=["Job Management"])
# You will add other routers here as you build them, e.g.:
# from app.api.endpoints import candidates
# app.include_router(candidates.router, prefix="/api/v1", tags=["Candidate Management"])
# from app.api.endpoints import interviews
# app.include_router(interviews.router, prefix="/api/v1", tags=["Interview Sessions"])


@app.get("/api/v1/health", summary="Health Check")
async def health_check():
    """
    Basic health check endpoint to confirm the API is running.
    """
    return {"status": "ok", "message": "AI Interview Agent API is running."}