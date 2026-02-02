import re
from pypdf import PdfReader
from typing import List
import hashlib
import os

class DocumentProcessor:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def _split_text(self, text: str) -> List[str]:
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            
            if end < text_length:
                for separator in ['\n\n', '\n', '. ', ' ']:
                    pos = text.rfind(separator, start, end)
                    if pos != -1:
                        end = pos + len(separator)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap if end < text_length else text_length
        
        return chunks
    
    def process_pdf(self, file_path: str) -> tuple[List[str], List[dict], str]:
        reader = PdfReader(file_path)
        doc_id = hashlib.md5(file_path.encode()).hexdigest()[:8]
        
        all_chunks = []
        all_metadatas = []
        
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            chunks = self._split_text(text)
            
            for chunk in chunks:
                all_chunks.append(chunk)
                all_metadatas.append({
                    "source": os.path.basename(file_path),
                    "page": page_num,
                    "doc_id": doc_id
                })
        
        return all_chunks, all_metadatas, doc_id
