from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from models import RoleEnum # Import RoleEnum from models.py

# Pydantic model for JobBase.
# This defines common fields for Job.
class JobBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100) # Job title, required, min/max length
    description: Optional[str] = Field(None, max_length=1000) # Job description, optional, max length

# Pydantic model for JobCreate.
# Used when creating a new job, inherits from JobBase.
class JobCreate(JobBase):
    owner_id: int # The ID of the user who owns this job, required for creation

# Pydantic model for JobResponse.
# Used when returning job data, includes the ID and owner relationship.
class JobResponse(JobBase):
    id: int # Job ID
    owner_id: int # Owner ID
    # Nested Pydantic model for the owner.
    # This ensures that when a Job is returned, its owner's basic info is also included.
    # Use 'from __future__ import annotations' or string literal for forward references if needed in complex cases.
    owner: "UserResponse" # Forward reference to UserResponse (defined below)

    class Config:
        from_attributes = True # Enable ORM mode for Pydantic v2

# Pydantic model for UserBase.
# Defines common fields for User.
class UserBase(BaseModel):
    email: EmailStr # Email address, validated as an email format
    first_name: str = Field(..., min_length=1, max_length=50) # First name, required
    last_name: str = Field(..., min_length=1, max_length=50) # Last name, required
    role: RoleEnum # User role, using the imported RoleEnum

# Pydantic model for UserCreate.
# Used when creating a new user, includes the password.
class UserCreate(UserBase):
    password: str = Field(..., min_length=8) # Password, required, min length

# Pydantic model for UserResponse.
# Used when returning user data, excludes the password and includes ID and jobs relationship.
class UserResponse(UserBase):
    id: int # User ID
    # Nested Pydantic model for jobs.
    # This ensures that when a User is returned, their associated jobs (without the owner field to prevent recursion) are also included.
    jobs: List[JobBase] = [] # List of jobs associated with the user

    class Config:
        from_attributes = True # Enable ORM mode for Pydantic v2

# New Pydantic model for User Login credentials
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Update the forward reference for JobResponse to resolve UserResponse
JobResponse.model_rebuild()