import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Tuple
import requests
from app.config import settings

class VectorStore:
    def __init__(self, persist_dir: str, ollama_base_url: str, embedding_model: str):
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.ollama_url = ollama_base_url.rstrip("/")
        self.embedding_model = embedding_model
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={
                "hnsw:space": "cosine",
                "hnsw:M": settings.CHROMA_HNSW_M,
                "hnsw:construction_ef": settings.CHROMA_HNSW_EF_CONSTRUCTION,
                "hnsw:search_ef": settings.CHROMA_HNSW_EF_SEARCH
            }
        )
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            resp = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text},
                timeout=30,
            )
            resp.raise_for_status()
            embeddings.append(resp.json()["embedding"])
        return embeddings
    
    def add_documents(self, texts: List[str], metadatas: List[dict], doc_id: str) -> int:
        if not texts:
            return 0
        ids = [f"{doc_id}_{i}" for i in range(len(texts))]
        embeddings = self._get_embeddings(texts)
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )
        return len(texts)
    
    def search(self, query: str, top_k: int) -> Tuple[List[str], List[str]]:
        query_embedding = self._get_embeddings([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        filtered_docs = []
        filtered_sources = []
        filtered_metas = []
        for i, dist in enumerate(distances):
            if dist < 0.5 and len(filtered_docs) < settings.TOP_K_RESULTS:  # 0.25 → 0.5
                filtered_docs.append(docs[i])
                filtered_metas.append(metas[i])
        
        sources = [f"{m['source']} (page {m['page']})" for m in filtered_metas]
        return filtered_docs, sources

    
    def clear(self):
        self.client.delete_collection("knowledge_base")
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={
                "hnsw:space": "cosine",
                "hnsw:M": settings.CHROMA_HNSW_M,
                "hnsw:construction_ef": settings.CHROMA_HNSW_EF_CONSTRUCTION,
                "hnsw:search_ef": settings.CHROMA_HNSW_EF_SEARCH
            }
        )
    
    def count(self) -> int:
        return self.collection.count()
