import re
from collections import Counter
from typing import List, Set

class DynamicKeywordExtractor:
    def __init__(self):
        self.policy_patterns = [
            r'\b(cuti|izin|libur|klaim|claim|tunjangan|lembur|wfo|wfa|hybrid|core hours)\b',
            r'\b(staff|manager|senior|lead|vp|c-level)\b',
            r'\b(kebijakan|policy|prosedur|aturan|wajib)\b',
            r'\b(rp\s*\d+(?:\.\d+)?|maksimal|minimal)\b'
        ]
    
    def extract_from_docs(self, docs: List[str]) -> Set[str]:
        keywords = set()
        
        for doc in docs:
            for pattern in self.policy_patterns:
                matches = re.findall(pattern, doc.lower())
                keywords.update(matches)
            
            sentences = re.split(r'[.!?]+', doc)
            for sent in sentences:
                words = re.findall(r'\b[a-zA-Z]{4,}\b', sent.lower())
                if len(words) >= 2:
                    keywords.update(words[:5])
        
        return keywords - {'dan', 'atau', 'yang', 'dari', 'pada', 'untuk', 'dengan'}
