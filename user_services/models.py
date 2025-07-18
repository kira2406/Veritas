from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base
import enum

# Define the RoleEnum using Python's enum module.
class RoleEnum(str, enum.Enum):
    recruiter = "recruiter"
    candidate = "candidate"

# User model definition.
class User(Base):
    __tablename__ = "users" # Table name in the database
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True) # Primary key, auto-incrementing
    email: Mapped[str] = mapped_column(String, unique=True, index=True) # Unique email, indexed for fast lookups
    password: Mapped[str] = mapped_column(String) # Hashed password
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum)) # Role of the user, using the custom enum
    first_name: Mapped[str] = mapped_column(String) # User's first name
    last_name: Mapped[str] = mapped_column(String) # User's last name

    # Define the relationship with the Job model.
    # 'jobs' will be a list of Job objects associated with this user.
    # back_populates ensures a bidirectional relationship.
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="owner")

# Job model definition.
class Job(Base):
    __tablename__ = "jobs" # Table name in the database
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True) # Primary key, auto-incrementing
    title: Mapped[str] = mapped_column(String) # Job title
    description: Mapped[str] = mapped_column(String) # Job description
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id")) # Foreign key linking to the User's id

    # Define the relationship with the User model.
    # 'owner' will be a User object associated with this job.
    # back_populates ensures a bidirectional relationship.
    owner: Mapped["User"] = relationship("User", back_populates="jobs")