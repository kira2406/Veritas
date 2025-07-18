from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession # Import AsyncSession
from sqlalchemy import select # Import select for async queries
from sqlalchemy.orm import selectinload # Import selectinload for eager loading
from typing import List

from database import get_db
import models
import schemas

# Create an APIRouter instance for job-related routes.
router = APIRouter()

# Endpoint to create a new job.
@router.post("/", response_model=schemas.JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(job: schemas.JobCreate, db: AsyncSession = Depends(get_db)): # Made async, db type AsyncSession
    result = await db.execute(select(models.User).filter(models.User.id == job.owner_id))
    owner = result.scalars().first()
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner (User) not found"
        )
    # Check if the owner's role is 'recruiter'
    if owner.role != models.RoleEnum.recruiter:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only recruiters can create jobs"
        )

    db_job = models.Job(
        title=job.title,
        description=job.description,
        owner_id=job.owner_id
    )
    db.add(db_job)
    await db.commit() # Await commit
    await db.refresh(db_job) # Await refresh
    # To ensure owner relationship and owner's jobs relationship are loaded for response
    result = await db.execute(
        select(models.Job)
        .filter(models.Job.id == db_job.id)
        .options(
            selectinload(models.Job.owner).selectinload(models.User.jobs) # Nested eager loading
        )
    )
    db_job = result.scalars().first()
    return db_job

# Endpoint to get all jobs.
@router.get("/", response_model=List[schemas.JobResponse])
async def read_jobs(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)): # Made async, db type AsyncSession
    # Eagerly load the 'owner' relationship and the owner's 'jobs' relationship
    result = await db.execute(
        select(models.Job)
        .options(
            selectinload(models.Job.owner).selectinload(models.User.jobs) # Nested eager loading
        )
        .offset(skip)
        .limit(limit)
    )
    jobs = result.scalars().all()
    return jobs

# Endpoint to get a specific job by ID.
@router.get("/{job_id}", response_model=schemas.JobResponse)
async def read_job(job_id: int, db: AsyncSession = Depends(get_db)): # Made async, db type AsyncSession
    # Eagerly load the 'owner' relationship and the owner's 'jobs' relationship
    result = await db.execute(
        select(models.Job)
        .options(
            selectinload(models.Job.owner).selectinload(models.User.jobs) # Nested eager loading
        )
        .filter(models.Job.id == job_id)
    )
    job = result.scalars().first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job

# Endpoint to update a job by ID.
@router.put("/{job_id}", response_model=schemas.JobResponse)
async def update_job(job_id: int, job_update: schemas.JobCreate, db: AsyncSession = Depends(get_db)): # Made async, db type AsyncSession
    result = await db.execute(select(models.Job).filter(models.Job.id == job_id))
    db_job = result.scalars().first()
    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if job_update.owner_id != db_job.owner_id:
        new_owner_result = await db.execute(select(models.User).filter(models.User.id == job_update.owner_id))
        new_owner = new_owner_result.scalars().first()
        if new_owner is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New owner (User) not found"
            )

    db_job.title = job_update.title
    db_job.description = job_update.description
    db_job.owner_id = job_update.owner_id

    await db.commit() # Await commit
    # Refresh with eager loading to ensure the response model can serialize 'owner' and its 'jobs'
    await db.refresh(db_job, attribute_names=["owner"]) # Refresh specific attribute
    # Re-fetch with nested selectinload to ensure all required relationships are loaded for the response
    result = await db.execute(
        select(models.Job)
        .options(
            selectinload(models.Job.owner).selectinload(models.User.jobs) # Nested eager loading
        )
        .filter(models.Job.id == db_job.id)
    )
    db_job = result.scalars().first()
    return db_job

# Endpoint to delete a job by ID.
@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db)): # Made async, db type AsyncSession
    result = await db.execute(select(models.Job).filter(models.Job.id == job_id))
    db_job = result.scalars().first()
    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    await db.delete(db_job) # Await delete
    await db.commit() # Await commit
    return {"message": "Job deleted successfully"}