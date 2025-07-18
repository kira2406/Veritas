from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async_engine = create_async_engine(DATABASE_URL, echo=True)

# Create an AsyncSessionLocal class. Each instance will be an asynchronous database session.
# The `autocommit=False` means that we will have to commit our changes explicitly.
# The `autoflush=False` means that the session will not flush changes to the database until commit or query.
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False # Recommended for async sessions
)

# Base class for our SQLAlchemy models.
Base = declarative_base()

# Dependency to get an asynchronous database session for each request.
# This function will be used in FastAPI path operations.
async def get_db() -> AsyncSession:
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()
