# app/api/endpoints/jobs.py

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from typing import Optional
import uuid
import io
import os
import instructor
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from pydantic import ValidationError
load_dotenv()
openai_api_key = os.getenv("OPENAI_APIKEY")

from veritas_services.schemas import JobDescriptionInput, JobDescriptionData, GeneralResponse, FileUpload
from veritas_services.services import jd_processing # Import our JD processing functions

router = APIRouter()

client = instructor.from_openai(OpenAI(api_key=openai_api_key))



@router.post("/jobs/upload_jd", response_model=GeneralResponse, summary="Upload and Process a New Job Description")
async def upload_job_description(
    job_title: str = Form(..., description="The official title of the job role."),
    company_id: str = Form(..., description="Unique identifier for the company posting this job."),
    file: Optional[UploadFile] = File(None, description="Upload a job description file (PDF or DOCX)."),
    raw_text: Optional[str] = Form(None, description="Paste raw text content of the job description instead of uploading a file.")
):
    if not file and not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'file' or 'raw_text' must be provided."
        )
    if file and raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot provide both 'file' and 'raw_text'. Choose one."
        )
    extracted_text = None
    file_type = None

    if file:
        file_content_bytes = await file.read()
        file_type = file.content_type
        # Call the text extraction service
        extracted_text = jd_processing.extract_text_from_file(file_content_bytes, file_type) # type: ignore
        if not extracted_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not extract text from the provided file type: {file.content_type}. Please check the file or use raw text."
            )
    elif raw_text:
        extracted_text = raw_text

    # Clean the extracted text
    cleaned_jd_text = jd_processing.clean_text(extracted_text) # type: ignore
    if not cleaned_jd_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Extracted or provided text is empty after cleaning. Please ensure the job description has content."
        )

    # Generate a unique Job ID
    job_id = str(uuid.uuid4())

    parsed_jd_data: Optional[JobDescriptionData] = None
    try:
        # Use the LLM to parse the cleaned text into our Pydantic schema
        # instructor.from_openai(OpenAI()) allows passing response_model directly
        parsed_jd_data = client.chat.completions.create(
            model="gpt-4o-mini",  # Use a cost-effective model, or gpt-4o for higher accuracy
            response_model=JobDescriptionData, # This tells the LLM to output JSON conforming to this schema
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert HR assistant. Your task is to accurately extract all relevant information from a job description and structure it into the provided JSON format. If a field is not explicitly mentioned, leave it as null or an empty list as per the schema's default."
                },
                {
                    "role": "user",
                    "content": f"Please extract the following job description:\n\n{cleaned_jd_text}"
                }
            ]
        )
        parsed_jd_data.job_id = job_id
        parsed_jd_data.company_id = company_id
        parsed_jd_data.title = job_title
    # parsed_jd_data = "job_id='8403602a-780c-4a35-8959-05640864c936' company_id='SomeAICompany' title='Software Engineer' location='Remote – US' summary=\"At TechNova Inc., we're on a mission to revolutionize digital commerce with cutting-edge AI and data platforms\.\" responsibilities=['Design, build, and maintain scalable backend services using Python and Go.', 'Collaborate with cross-functional teams to define and deliver new features.', 'Optimize application performance and reliability.', 'Mentor junior developers and contribute to code reviews.', 'Participate in agile ceremonies and help refine product requirements.'] required_skills=['5+ years of professional experience in backend development.', 'Proficiency in Python and experience with Go or another compiled language.', 'Strong understanding of RESTful API design and microservices architecture.', 'Experience with PostgreSQL, Redis, and Docker.', 'Excellent problem-solving and communication skills.'] preferred_skills=['Experience with Kubernetes and cloud platforms (AWS/GCP).', 'Prior work in a fast-growing startup environment.', 'Familiarity with CI/CD tools like GitHub Actions or CircleCI.'] qualifications=['Bachelor’s or Master’s degree in Computer Science or a related field.'] experience_level='Senior' technologies=['Python', 'Go', 'PostgreSQL', 'Redis', 'Docker', 'Kubernetes', 'AWS', 'GitHub Actions'] benefits=['Competitive salary and equity', 'Fully remote work environment', 'Health, dental, and vision insurance', '401(k) with company match', 'Professional development stipend', 'Generous PTO and parental leave']" # type: ignore

    except ValidationError as e:
        # This occurs if the LLM outputted JSON that doesn't match the Pydantic schema
        print(f"Pydantic Validation Error during LLM parsing: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse job description with LLM due to schema mismatch. Details: {e.errors()}"
        )
    except Exception as e:
        # Catch other potential errors from the LLM API call
        print(f"Error calling LLM for structured parsing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract structured job description data using LLM."
        )

    # print("parsed_jd_data", parsed_jd_data)
    jd_metadata = jd_processing.to_flat_metadata(parsed_jd_data)
    # Generate embedding
    jd_embedding = jd_processing.generate_embedding(cleaned_jd_text)
    if not jd_embedding:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embedding for the job description. Check LLM service configuration."
        )

    # Store in ChromaDB
    success = jd_processing.add_jd_to_chroma(
        job_id=job_id,
        job_title=job_title,
        company_id=company_id,
        cleaned_jd_text=cleaned_jd_text, # Document for embedding
        jd_embedding=jd_embedding,
        parsed_jd_data_dict=jd_metadata # Structured data as metadata
    )

    if not success:
        # This can happen if job_id already exists (though uuid4 makes it unlikely)
        # or if ChromaDB initialization failed.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store job description and embedding in the database."
        )

    return GeneralResponse(
        message=f"Job Description '{parsed_jd_data.title}' (ID: {job_id}) uploaded, processed, and structured successfully.",
        status="success",
        details={
            "job_id": job_id,
            "job_title": parsed_jd_data.title,
            "company_id": parsed_jd_data.company_id,
            "parsed_data": parsed_jd_data.model_dump() # Return the full parsed data
        }
    )

# You could add other endpoints here, e.g., to retrieve a JD by ID
# @router.get("/jobs/{job_id}", response_model=JobDescriptionData, summary="Retrieve Job Description Details")
# async def get_job_description(job_id: str):
#     # In a full app, you'd fetch from your relational DB and potentially ChromaDB
#     # For POC, let's just show a placeholder or fetch from ChromaDB if needed
#     # For now, this is just a placeholder example
#     raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented yet.")