from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import List, Optional, Dict, Literal
from datetime import date

class FileUpload(BaseModel):
    filename: str
    content_type: str
    file_content: bytes

class GeneralResponse(BaseModel):
    message: str
    status: Literal["success", "error"]
    details: Optional[Dict] = None

class JobDescriptionInput(BaseModel):
    """
    Input schema for uploading a new Job Description.
    Either provide raw_text or file_upload, but not both.
    """
    job_title: str = Field(..., description="The official title of the job role.")
    company_id: str = Field(..., description="Unique identifier for the company posting this job.")
    raw_text: Optional[str] = Field(None, description="The raw text content of the job description.")
    file_upload: Optional[FileUpload] = Field(None, description="Details of the uploaded job description file.")

class JobDescriptionData(BaseModel):
    """
    Structured data extracted from a Job Description.
    This is what the LLM will output after parsing the raw JD text.
    """
    job_id: str = Field(..., description="Unique identifier generated for this job description.")
    company_id: str = Field(..., description="Unique identifier for the company that owns this job.")
    title: str = Field(..., description="The official job title.")
    location: Optional[str] = Field(None, description="Geographic location of the job (e.g., 'New York, NY', 'Remote').")
    summary: Optional[str] = Field(None, description="A brief summary or mission statement of the role.")
    responsibilities: List[str] = Field(default_factory=list, description="List of key responsibilities for the role.")
    required_skills: List[str] = Field(default_factory=list, description="List of hard and soft skills required for the role.")
    preferred_skills: List[str] = Field(default_factory=list, description="List of preferred but not mandatory skills.")
    qualifications: List[str] = Field(default_factory=list, description="List of educational or certification qualifications.")
    experience_level: Optional[str] = Field(None, description="E.g., 'Entry-level', 'Mid-level', 'Senior', 'Manager'.")
    technologies: List[str] = Field(default_factory=list, description="Specific programming languages, frameworks, tools.")
    benefits: List[str] = Field(default_factory=list, description="List of benefits offered for the role.")
  
class Skill(BaseModel):
    """
    Represents a skill from a candidate's resume.
    """
    name: str = Field(..., description="Name of the skill (e.g., 'Python', 'Leadership', 'AWS Lambda').")
    level: Optional[str] = Field(None, description="Proficiency level (e.g., 'Expert', 'Proficient', 'Familiar').")
    years_of_experience: Optional[float] = Field(None, description="Years of experience with this skill.")

class Project(BaseModel):
    """
    Represents a project a candidate worked on.
    """
    name: str
    description: Optional[str] = Field(None, description="Brief description of the project.")
    technologies_used: List[str] = Field(default_factory=list)
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class Education(BaseModel):
    """
    Represents an education entry from a candidate's resume.
    """
    degree: str = Field(..., description="Degree obtained (e.g., 'B.S. Computer Science', 'Ph.D. Physics').")
    major: Optional[str] = None
    institution: str = Field(..., description="Name of the educational institution.")
    graduation_date: Optional[str] = None
    gpa: Optional[str] = Field(None, description="Grade Point Average, if available.")

class Experience(BaseModel):
    """
    Represents a work experience entry from a candidate's resume.
    """
    title: str = Field(..., description="Job title.")
    company: str = Field(..., description="Company name.")
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None # "Present" if current
    duration: Optional[str] = None # e.g., "2 years 6 months"
    responsibilities: List[str] = Field(default_factory=list, description="List of responsibilities or duties.")

class ResumeData(BaseModel):
    """
    Structured data extracted from a Candidate's Resume.
    This is what the LLM will output after parsing the raw resume text.
    """
    resume_id: str = Field(..., description="Unique identifier generated for this resume.")
    name: str = Field(..., description="Full name of the candidate.")
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin: Optional[HttpUrl] = None
    github: Optional[HttpUrl] = None
    portfolio: Optional[HttpUrl] = None
    summary: Optional[str] = Field(None, description="A brief professional summary or objective statement.")
    skills: List[Skill] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)

class InterviewSessionInput(BaseModel):
    """
    Input schema to initiate an interview session.
    """
    candidate_id: str = Field(..., description="Unique identifier for the candidate.")
    job_id: str = Field(..., description="Unique identifier for the job description the candidate is applying for.")
    session_type: Literal["live", "practice"] = Field("live", description="Type of interview session.")
    initial_question: Optional[str] = Field(None, description="An optional first question to start the interview.")


class CandidateAnswer(BaseModel):
    """
    Schema for a candidate's answer during an interview turn.
    """
    session_id: str = Field(..., description="Unique ID for the ongoing interview session.")
    turn_number: int = Field(..., description="The sequential number of this conversation turn.")
    answer_text: str = Field(..., description="The candidate's response in plain text.")
 
class InterviewQuestion(BaseModel):
    """
    Schema for a question generated by the AI Interviewer.
    """
    session_id: str
    turn_number: int
    question_text: str
    question_type: Literal["behavioral", "technical", "situational", "follow-up", "cultural_fit", "other"] = Field("other", description="Category of the question.")
    target_skills: List[str] = Field(default_factory=list, description="Skills this question aims to assess.")
 
class InterviewEvaluation(BaseModel):
    """
    Structured output for evaluating a single candidate answer.
    """
    score: int = Field(..., ge=0, le=5, description="Overall score for the answer (0-5).")
    relevance_score: int = Field(..., ge=0, le=5, description="How relevant the answer was to the question/topic (0-5).")
    depth_score: int = Field(..., ge=0, le=5, description="How deep the understanding demonstrated was (0-5).")
    clarity_score: int = Field(..., ge=0, le=5, description="How clearly the answer was communicated (0-5).")
    justification: str = Field(..., description="Brief reasoning for the scores.")
    follow_up_needed: bool = Field(..., description="True if the answer was incomplete/vague, requiring further probing.")
    confidence_assessment: Optional[str] = Field(None, description="AI's assessment of candidate's confidence (e.g., 'High', 'Medium', 'Low').")
    sentiment: Optional[str] = Field(None, description="AI's assessment of candidate's emotional tone (e.g., 'Positive', 'Neutral', 'Hesitant').")


class InterviewProgress(BaseModel):
    """
    Overview of the interview's current progress and overall assessment.
    """
    session_id: str
    current_turn: int
    time_elapsed_seconds: int
    critical_skills_covered: Dict[str, float] = Field(default_factory=dict, description="Mapping of critical skill to coverage score (0.0-1.0).")
    overall_performance_score: Optional[float] = Field(None, description="Cumulative score for the entire interview so far.")
    status: Literal["ongoing", "concluding", "terminated_early", "completed"] = Field("ongoing")
    termination_reason: Optional[str] = Field(None, description="Reason for termination, if applicable.")
