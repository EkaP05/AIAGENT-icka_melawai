# Intelligent Corporate Knowledge Assistant API

A lightweight Retrieval-Augmented Generation (RAG) backend designed to
answer employee questions about internal corporate policies such as
leave, benefits, WFO/WFA, overtime, and the use of generative AI. The
system operates on PDF-based HR policy documents and provides grounded,
traceable answers.

------------------------------------------------------------------------

## Technology Stack

-   **Language:** Python 3.10.12
-   **Web Framework:** FastAPI
-   **LLM Runtime:** Ollama (local LLM server)
-   **LLM Models:** `llama3.2:3b` `qwen2.5:3b`
-   **Vector Database:** Local Chroma (via a custom
    `VectorStore` wrapper with on-disk persistence)
-   **ASGI Server:** Uvicorn

------------------------------------------------------------------------

## Setup and Running the Service

### 1. Prerequisites

-   Python 3.10 or newer
-   Git
-   Ollama installed on your machine (Linux, macOS, or WSL)

### 2. Install Ollama and Pull Models

Install Ollama from the official website for your operating system and
ensure the Ollama service is running.

Pull the required models:

``` bash
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
```

Verify that Ollama is responsive:

``` bash
curl http://localhost:11434/api/tags
```

A list of available models should be returned.

### 3. Clone the Repository and Create a Virtual Environment

``` bash
git clone <YOUR_REPO_URL>.git
cd intelligent-knowledge-assistant

python -m venv venv
source venv/bin/activate   

pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file (or configure equivalent environment variables)
with values similar to the following:

``` text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b or qwen2.5:3b
CHROMA_PERSIST_DIR=./data/vector_store
CHUNK_SIZE=800
CHUNK_OVERLAP=200
TOP_K_RESULTS=3
```

Adjust model names and paths as needed for your local setup.

### 5. Start the API Server

``` bash
uvicorn app.main:app --reload
```

Key URLs:

-   **Root:** http://localhost:8000/
-   **OpenAPI / Swagger UI:** http://localhost:8000/docs

------------------------------------------------------------------------

## API Endpoints

### 1. `POST /ingest` -- Ingest HR Policy Documents

Uploads an HR policy PDF, splits it into chunks, and stores embeddings
in the vector database.

**Input:** `multipart/form-data` with a single file field (PDF).

**Processing Steps:**

1.  Save the uploaded file under `./data/documents/`.
2.  Extract text and split it into overlapping chunks using `CHUNK_SIZE`
    and `CHUNK_OVERLAP`.
3.  Generate embeddings via Ollama and persist them to the vector store
    at `CHROMA_PERSIST_DIR`.

**Example Request:**

``` bash
curl -X POST "http://localhost:8000/ingest" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@PT-TMD-BUKU-SAKU-KEBIJAKAN-SUMBER-DAYA-MANUSIA.pdf"
```

**Example Response:**

``` json
{
  "status": "success",
  "document_id": "pt-tmd-buku-saku-kebijakan-sdm-2025",
  "chunks_created": 42,
  "message": "Document 'PT-TMD-BUKU-SAKU-KEBIJAKAN-SUMBER-DAYA-MANUSIA.pdf' successfully ingested with 42 chunks"
}
```

**Additional Database Endpoints:**

-   `GET /db/stats` -- Returns basic statistics (e.g., number of stored
    chunks or documents).\
-   `DELETE /clear` -- Clears the entire vector store (useful for local
    experiments or resets).

------------------------------------------------------------------------

### 2. `POST /chat` -- Ask HR Policy Questions via RAG

Resolves a user question against the ingested HR documents and returns a
context-grounded answer.

**Input:** JSON body

``` json
{
  "question": "berapa claim kacamata untuk seorang manager?"
}
```

**Processing Steps:**

1.  Normalize the question text (for example, converting informal slang
    such as "gu/gw/gue" to "saya", or abbreviations like "thn" to
    "tahun") to improve embedding quality.
2.  Retrieve the top `TOP_K_RESULTS` most relevant chunks from the
    vector store.\
3.  Construct a prompt consisting of:
    -   A domain-specific system prompt for HR policies
    -   Retrieved context chunks
    -   The normalized user question
4.  Invoke the LLM through Ollama and return the answer along with
    source metadata.

**Example Request:**

``` bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "berapa claim kacamata untuk seorang manager?"}'
```

**Example Response:**

``` json
{
  "answer": "Klaim kacamata untuk level Lead–Manager maksimal Rp 2.500.000 setiap 2 tahun sekali.",
  "sources": [
    {
      "document_id": "pt-tmd-buku-saku-kebijakan-sdm-2025",
      "section": "BAB III, 3.1 Klaim Kacamata (Optical)"
    }
  ],
  "is_relevant": true
}
```

------------------------------------------------------------------------

### Guardrail Example (Out-of-Domain Question)

The service is intentionally limited to internal corporate policies. If
a question is unrelated to the ingested documents, the API responds
politely without hallucinating.

**Example Request:**

``` bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "Siapa presiden Amerika?"}'
```

**Example Response:**

``` json
{
  "answer": "Maaf, saya hanya dapat membantu menjawab pertanyaan terkait kebijakan internal perusahaan.",
  "sources": [],
  "is_relevant": false
}
```

This behavior is implemented using a lightweight keyword-based relevance
check prior to invoking the LLM.

------------------------------------------------------------------------

## Chunking Strategy and Vector Store

### Chunking

-   **Approach:** Fixed-size chunks with overlap\
-   **Configurable Parameters:**
    -   `CHUNK_SIZE` -- typically around 800 characters or tokens\
    -   `CHUNK_OVERLAP` -- typically around 200

**Rationale:**

HR policies are structured as sections and articles. This chunk size
ensures that most rules remain within one or two chunks, reducing the
risk of splitting a single policy across many fragments. Overlap
preserves context across boundaries while keeping the overall prompt
length manageable for the LLM.

### Vector Store

The vector store is implemented as a local Chroma/FAISS-style index with
on-disk persistence under `CHROMA_PERSIST_DIR`.

Each chunk is stored with:

-   A document identifier
-   Optional metadata (for example, section name or page number)
-   A vector embedding for similarity search

This design satisfies the requirement for a simple, local vector
database while remaining extensible.

------------------------------------------------------------------------

## System Prompt (Summary)

The LLM is guided by a concise system prompt that:

-   Defines the assistant's role as a helper for PT Teknologi Masa
    Depan's HR policies\
-   Instructs the model to answer strictly based on the provided
    document context\
-   Encourages explicit mention of:
    -   Numeric values (days, years, currency amounts)\
    -   Units\
    -   Key conditions such as tenure or job level\
-   Prompts the model to address all parts of multi-fact questions in a
    single response\
-   Provides a short fallback message when the requested information is
    not found in the available policies

This ensures consistent, grounded, and policy-aligned answers.

------------------------------------------------------------------------

## Scaling Considerations (Azure / Microsoft Fabric)

The architecture intentionally separates concerns to support future
scaling or migration:

### Document Storage

-   **Current:** Local filesystem (`./data/documents`)
-   **Future:** Azure Blob Storage or Microsoft Fabric Lakehouse

### Vector Index

-   **Current:** Local Chroma/FAISS-style index
-   **Future:** Azure AI Search or a vector index within Fabric

### LLM Backend

-   **Current:** Ollama with local models
-   **Future:** Azure OpenAI Service or internal enterprise endpoints
    (using the same `LLMService` interface with different configuration)

### API Layer

-   **Current:** FastAPI with Uvicorn
-   **Future:** Containerized deployment to Azure App Service, Azure
    Container Apps, or AKS with minimal code changes

This approach provides a clear path from a local prototype to a
production-ready deployment on Azure or Microsoft Fabric while
preserving the existing `/ingest` and `/chat` API contracts.
