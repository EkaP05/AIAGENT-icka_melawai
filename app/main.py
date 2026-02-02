from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import shutil
import os
from pathlib import Path
import re


from app.config import settings
from app.models.schemas import *
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStore
from app.services.llm_service import LLMService


vector_store = None
document_processor = None
llm_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store, document_processor, llm_service
    
    Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    Path("./data/documents").mkdir(parents=True, exist_ok=True)
    
    vector_store = VectorStore(
        settings.CHROMA_PERSIST_DIR,
        settings.OLLAMA_BASE_URL,
        settings.OLLAMA_EMBEDDING_MODEL,
    )
    document_processor = DocumentProcessor(settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    llm_service = LLMService(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
    
    yield
    

app = FastAPI(
    title="Intelligent Corporate Knowledge Assistant API",
    description="RAG-based API for answering corporate policy questions",
    version="1.0.0",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "Intelligent Corporate Knowledge Assistant",
        "status": "running",
        "endpoints": ["/ingest", "/chat", "/health", "/db/stats", "/clear"]
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "vector_store": "connected"}


@app.get("/db/stats")
async def db_stats():
    return {"total_documents": vector_store.count()}


@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    file_path = f"./data/documents/{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        texts, metadatas, doc_id = document_processor.process_pdf(file_path)
        chunks_count = vector_store.add_documents(texts, metadatas, doc_id)
        
        return IngestResponse(
            status="success",
            document_id=doc_id,
            chunks_created=chunks_count,
            message=f"Document '{file.filename}' successfully ingested with {chunks_count} chunks"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        context_docs, sources = vector_store.search(request.question, settings.TOP_K_RESULTS)
        llm_service.update_keywords_from_docs(context_docs)
        answer, is_relevant = llm_service.generate_answer(request.question, context_docs)
        
        return ChatResponse(answer=answer, sources=sources, is_relevant=is_relevant)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")


@app.delete("/clear")
async def clear_database():
    try:
        vector_store.clear()
        return {"status": "success", "message": "Vector database cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing database: {str(e)}")
