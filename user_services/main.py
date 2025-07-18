from fastapi import FastAPI
from routes import users, jobs
from database import Base, async_engine

app = FastAPI(
    title="FastAPI Job Board API",
    description="A simple API for managing users and job postings.",
    version="1.0.0",
)

@app.on_event("startup")
async def on_startup(): # Made async
    print("Creating database tables...")
    # This will create all tables defined in models.py if they don't already exist.
    async with async_engine.begin() as conn: # Use async_engine for DDL
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created (if they didn't exist).")


app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])