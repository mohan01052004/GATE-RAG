import os
from dotenv import load_dotenv

load_dotenv()

def _as_bool(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyA7wNAGUvh-2fXeYPmA0K1TTIWYTdsjmqM")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HUGGINGFACE_EMBEDDING_MODEL = os.getenv("HUGGINGFACE_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
HUGGINGFACE_LLM_MODEL = os.getenv("HUGGINGFACE_LLM_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
DATABASE_URL = os.getenv("DATABASE_URL")
