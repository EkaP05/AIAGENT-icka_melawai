import re
import requests
from typing import List, Tuple, Set


class LLMService:
    def __init__(self, ollama_base_url: str, ollama_model: str):
        self.base_url = ollama_base_url.rstrip("/")
        self.model = ollama_model
        self.system_prompt = (
            "Anda adalah asisten kebijakan internal perusahaan PT Teknologi Masa Depan (TMD).\n\n"
            "TUGAS:\n"
            "- Jawab pertanyaan tentang kebijakan HR (jam kerja, WFO/WFA, cuti, klaim, tunjangan, penggunaan AI, dll.).\n"
            "- Gunakan HANYA informasi yang ada di konteks dokumen yang diberikan.\n"
            "- Jika pertanyaan mengandung beberapa bagian (misalnya nominal, syarat, batas maksimal), JAWAB SEMUA bagian tersebut secara eksplisit.\n"
            "- Selalu sebutkan angka, satuan (hari, tahun, rupiah), dan syarat utama (masa kerja, level jabatan) jika tersedia di konteks.\n\n"
            "JANGAN:\n"
            "- Jangan menjawab 'Maaf, saya hanya dapat membantu...' jika informasi yang diminta sebenarnya ada di konteks.\n"
            "- Jangan mengarang atau menambahkan kebijakan yang tidak ada di dokumen.\n\n"
            "JIKA BENAR-BENAR tidak ada di konteks:\n"
            "- Jawab singkat: 'Informasi tersebut tidak tercantum dalam kebijakan HR yang saya miliki.'\n\n"
            "Format jawaban:\n"
            "1) Satu paragraf jawaban langsung yang ringkas dan spesifik.\n"
            "2) Jika perlu, kalimat kedua menjelaskan syarat/batasan.\n"
        )
        self.policy_keywords: Set[str] = set()

    def normalize_query(self, q: str) -> str:
        q_norm = q.lower()
        slang_map = {
            r"\bgu\b": "saya",
            r"\bgw\b": "saya",
            r"\bgue\b": "saya",
            r"\bgwe\b": "saya",
            r"\btaon\b": "tahun",
            r"\bthn\b": "tahun",
            r"libur tahunan": "cuti tahunan",
            r"\bwfo\b": "work from office",
            r"\bwfa\b": "work from anywhere",
        }
        for pattern, repl in slang_map.items():
            q_norm = re.sub(pattern, repl, q_norm)
        return q_norm

    def update_keywords_from_docs(self, docs: List[str]):
        keywords = set()
        patterns = [
            r'\b(cuti|klaim|tunjangan|lembur|wfo|wfa|asuransi|kacamata)\b',
            r'\b(staff|manager|senior|lead|vp|c-level)\b',
            r'\b(kebijakan|prosedur|wajib|maksimal|minimal)\b'
        ]

        for doc in docs:
            for pattern in patterns:
                matches = re.findall(pattern, doc.lower())
                keywords.update(matches)

        self.policy_keywords = keywords - {'dan', 'atau', 'yang', 'dari', 'pada'}

    def is_relevant_question(self, question: str) -> bool:
        normalized = self.normalize_query(question)

        if not self.policy_keywords:
            keywords = {
                "cuti", "klaim", "tunjangan", "lembur",
                "wfo", "wfa", "work", "office", "anywhere",
                "manager", "staff", "senior", "vp",
                "kebijakan", "prosedur", "asuransi", "kacamata", "softlens",
                "jam", "core", "hours",
                "chatgpt", "ai", "tmd-gpt", "data", "nasabah",
            }
        else:
            keywords = self.policy_keywords

        q_words = set(re.findall(r'\b[a-zA-Z]{2,}\b', normalized))
        return bool(q_words & keywords)

    def _build_context(self, context_docs: List[str]) -> str:
        parts = []
        for i, doc in enumerate(context_docs):
            parts.append(f"[Dokumen {i+1}]\n{doc}")
        return "\n\n---\n\n".join(parts)

    def generate_answer(self, question: str, context_docs: List[str]) -> Tuple[str, bool]:
        normalized_question = self.normalize_query(question)

        if not self.is_relevant_question(normalized_question):
            return (
                "Maaf, saya hanya dapat membantu menjawab pertanyaan terkait kebijakan internal perusahaan.",
                False,
            )

        if not context_docs:
            return (
                "Maaf, saya tidak menemukan informasi yang relevan dalam dokumen kebijakan HR yang saya miliki.",
                False,
            )

        context = self._build_context(context_docs)
        prompt = (
            f"{self.system_prompt}\n\n"
            f"Konteks dokumen:\n{context}\n\n"
            f"Pertanyaan pengguna:\n{normalized_question}\n\n"
            f"Jawab berdasarkan konteks di atas."
        )

        resp = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
            },
            timeout=120,
        )
        resp.raise_for_status()
        answer = resp.json().get("response", "").strip()
        return answer, True
