from pydantic import BaseModel, Field
from typing import Optional, List

class IngestRequest(BaseModel):
    document_id: Optional[str] = Field(None, description="Optional document identifier")

class IngestResponse(BaseModel):
    status: str
    document_id: str
    chunks_created: int
    message: str

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    is_relevant: bool
