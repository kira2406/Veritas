from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession # Import AsyncSession
from sqlalchemy import select # Import select for async queries
from typing import List
from sqlalchemy.orm import selectinload

from database import get_db
import models
import schemas
from passlib.context import CryptContext

# Create an APIRouter instance for user-related routes.
router = APIRouter()

# Password hashing utilities (re-defined or imported from a common utility file if preferred)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Endpoint to create a new user.
@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)): # Made async, db type AsyncSession
    # Use await db.execute(select(...)) for async queries
    result = await db.execute(select(models.User).filter(models.User.email == user.email))
    db_user = result.scalars().first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        password=hashed_password,
        role=user.role,
        first_name=user.first_name,
        last_name=user.last_name
    )
    db.add(db_user)
    await db.commit() # Await commit
    await db.refresh(db_user) # Await refresh
    # To ensure jobs relationship is loaded for response, refresh with selectinload
    await db.execute(select(models.User).filter(models.User.id == db_user.id).options(selectinload(models.User.jobs)))
    return db_user

# Endpoint to get all users.
# Endpoint to get all users.
@router.get("/", response_model=List[schemas.UserResponse])
async def read_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)): # Made async, db type AsyncSession
    # Eagerly load the 'jobs' relationship to prevent MissingGreenlet error during serialization
    result = await db.execute(select(models.User).options(selectinload(models.User.jobs)).offset(skip).limit(limit))
    users = result.scalars().all()
    return users

# Endpoint to get a specific user by ID.
@router.get("/{user_id}", response_model=schemas.UserResponse)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)): # Made async, db type AsyncSession
    # Eagerly load the 'jobs' relationship
    result = await db.execute(select(models.User).options(selectinload(models.User.jobs)).filter(models.User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

# Endpoint to update a user by ID.
@router.put("/{user_id}", response_model=schemas.UserResponse)
async def update_user(user_id: int, user_update: schemas.UserCreate, db: AsyncSession = Depends(get_db)): # Made async, db type AsyncSession
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    db_user = result.scalars().first()
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user_update.email != db_user.email:
        existing_user_result = await db.execute(select(models.User).filter(models.User.email == user_update.email))
        existing_user = existing_user_result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered by another user"
            )

    db_user.email = user_update.email
    db_user.password = get_password_hash(user_update.password)
    db_user.role = user_update.role
    db_user.first_name = user_update.first_name
    db_user.last_name = user_update.last_name

    await db.commit() # Await commit
    # Refresh with eager loading to ensure the response model can serialize 'jobs'
    await db.refresh(db_user, attribute_names=["jobs"]) # Refresh specific attribute
    # Re-fetch with selectinload to ensure the jobs are loaded for the response
    result = await db.execute(select(models.User).options(selectinload(models.User.jobs)).filter(models.User.id == db_user.id))
    db_user = result.scalars().first()
    return db_user

# Endpoint to delete a user by ID.
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)): # Made async, db type AsyncSession
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    db_user = result.scalars().first()
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    await db.delete(db_user) # Await delete
    await db.commit() # Await commit
    return {"message": "User deleted successfully"}

# New login endpoint
@router.post("/login/")
async def login_user(user_credentials: schemas.UserLogin, db: AsyncSession = Depends(get_db)): # Made async, db type AsyncSession
    # Eagerly load the 'jobs' relationship for the logged-in user
    result = await db.execute(select(models.User).options(selectinload(models.User.jobs)).filter(models.User.email == user_credentials.email))
    db_user = result.scalars().first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(user_credentials.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # You might want to return the user object or a token here in a real app
    return {"message": "Login successful!", "user": schemas.UserResponse.model_validate(db_user)}