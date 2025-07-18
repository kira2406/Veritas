import io
import os
from typing import List, Optional, Dict, Any
import chromadb
import fitz
import docx
import numpy as np
from typing import Callable
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from veritas_services.schemas import JobDescriptionData

load_dotenv()
openai_api_key = os.getenv("OPENAI_APIKEY")

OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
CHROMA_DB_PATH = "./chroma_db"
JD_COLLECTION_NAME = "job_descriptions"

try:
    embeddings_model = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=openai_api_key) # type: ignore
except Exception as e:
    print(f"Error initializing OpenAIEmbeddings: {e}")
    print("Please ensure OPENAI_API_KEY is set in your environment variables.")
    embeddings_model = None

try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    jd_collection = chroma_client.get_or_create_collection(name=JD_COLLECTION_NAME)
    print(f"ChromaDB client and collection '{JD_COLLECTION_NAME}' initialized successfully.")
except Exception as e:
    print(f"Error initializing ChromaDB: {e}")
    chroma_client = None
    jd_collection = None

def get_job_descriptions_collection():
    # You might want to pass an embedding function here if not relying on default
    # return client.get_or_create_collection(name="job_descriptions", embedding_function=openai_ef)
    return chroma_client.get_or_create_collection(name="job_descriptions") # type:ignore

def extract_text_from_file(file_content_bytes: bytes, file_type: str) -> Optional[str]:
    """
    Extracts plain text from a given file's content bytes.
    Supports 'application/pdf' and 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'.
    """
    if file_type == "application/pdf":
        try:
            # PyMuPDF works with bytes directly
            doc = fitz.open(stream=file_content_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text() # type: ignore
            doc.close()
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return None
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        try:
            # python-docx needs a file-like object
            doc = docx.Document(io.BytesIO(file_content_bytes))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
            return text
        except Exception as e:
            print(f"Error extracting text from DOCX: {e}")
            return None
    else:
        print(f"Unsupported file type for text extraction: {file_type}")
        return None
    
def clean_text(text: str) -> str:
    """
    Performs basic cleaning on extracted text.
    """
    if not text:
        return ""
    # Collapse multiple newlines/spaces
    text = os.linesep.join([s for s in text.splitlines() if s.strip()])
    text = " ".join(text.split())
    return text.strip()

def mock_embed_query(text: str, dim: int = 1536) -> list[float]:
    # Deterministic mock using hash seed
    seed = hash(text) % (2**32)
    rng = np.random.default_rng(seed)
    return rng.random(dim).tolist()

def get_embedding(text: str, mock: bool = False, dim: int = 1536) -> list[float]:
    if mock:
        return mock_embed_query(text, dim)
    return embeddings_model.embed_query(text) # type:ignore

def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generates an embedding vector for the given text using OpenAI's model.
    """
    if not embeddings_model:
        print("Embeddings model not initialized. Cannot generate embedding.")
        return None
    if not text.strip():
        print("Cannot generate embedding for empty text.")
        return None

    try:
        # OpenAIEmbeddings.embed_query handles the API call
        # embedding = embeddings_model.embed_query(text)
        embedding = get_embedding(text, mock=True)
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None
    
def add_jd_to_chroma(
    job_id: str,
    job_title: str,
    company_id: str,
    cleaned_jd_text: str,
    jd_embedding: List[float],
    parsed_jd_data_dict: Dict[str, Any]
) -> bool:
    try:
        collection = get_job_descriptions_collection()
        collection.add(
            documents=[cleaned_jd_text],
            embeddings=[jd_embedding],
            metadatas=[parsed_jd_data_dict], # Store the parsed data here
            ids=[job_id]
        )
        print(f"Successfully added job {job_id} to ChromaDB with structured metadata.")
        return True
    except Exception as e:
        print(f"Error adding job to ChromaDB: {e}")
        return False

def to_flat_metadata(jd: JobDescriptionData) -> dict:
    metadata = {}
    for k, v in jd.dict().items():
        if isinstance(v, list):
            metadata[k] = "\n".join(v)  # Or ", ".join(v) depending on your query needs
        else:
            metadata[k] = v
    return metadata

def get_jd_from_chroma(job_id: str) -> Optional[Dict[str, Any]]:
    collection = get_job_descriptions_collection()
    results = collection.get(
        ids=[job_id],
        include=['documents', 'metadatas', 'embeddings'] # Request metadata as well
    )
    if results and results['ids']:
        return {
            "id": results['ids'][0],
            "document": results['documents'][0], # type: ignore
            "metadata": results['metadatas'][0], # This will be your structured data # type: ignore
            "embedding": results['embeddings'][0] # type: ignore
        }
    return None

def query_jds_by_skills(query_embedding: List[float], required_skill: str) -> List[Dict[str, Any]]:
    collection = get_job_descriptions_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=10,
        where={
            "required_skills": {"$contains": required_skill} # Example of filtering on metadata
        }, # type: ignore
        include=['documents', 'metadatas']
    )
    # Process results to return a cleaner list
    queried_jds = []
    if results and results['ids']:
        for i in range(len(results['ids'])):
            queried_jds.append({
                "id": results['ids'][i],
                "document": results['documents'][i], # type: ignore
                "metadata": results['metadatas'][i] # type: ignore
            })
    return queried_jds