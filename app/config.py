from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_EMBEDDING_MODEL: str = "mxbai-embed-large"
    
    CHROMA_HNSW_M: int = 32       
    CHROMA_HNSW_EF_CONSTRUCTION: int = 128
    CHROMA_HNSW_EF_SEARCH: int = 64 
    
    CHUNK_SIZE: int = 768   
    CHUNK_OVERLAP: int = 128   
    TOP_K_RESULTS: int = 4  
    
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"

    class Config:
        env_file = ".env"

settings = Settings()
