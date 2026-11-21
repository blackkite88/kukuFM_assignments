"""BM25 legal chunk retriever over verified statutory statutes."""

import json
import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel
from rank_bm25 import BM25Okapi

KB_DIR = Path("kb")

CONCEPT_SYNONYMS = {
    "kiraya": "rent deposit tenancy landlord",
    "deposit": "security deposit advance refund tenancy section 11",
    "salary": "wages payment delayed deduction employee section 15 section 5",
    "vetan": "wages salary payment deduction employee section 15",
    "tanha": "wages salary payment deduction",
    "refund": "consumer goods defect return price compensation section 39",
    "kharaab": "defect deficiency consumer goods service section 2",
    "kharab": "defect deficiency consumer goods service",
    "defective": "defect goods quality warranty replacement refund section 2 section 39",
    "malik": "landlord employer opposite party",
    "makan": "premises house tenancy rent residential",
    "dokan": "commercial shop non-residential",
    "notice": "legal notice demand claim limitation section 35",
}


class LegalChunk(BaseModel):
    act: str
    section: str
    text: str
    source_url: str
    score: float = 0.0


def _tokenize(text: str) -> List[str]:
    raw_tokens = re.findall(r"\b\w+\b", text.lower())
    expanded: List[str] = []
    for tok in raw_tokens:
        expanded.append(tok)
        if tok in CONCEPT_SYNONYMS:
            expanded.extend(CONCEPT_SYNONYMS[tok].split())
    return expanded


class LegalRetriever:
    def __init__(self, kb_path: Optional[Path] = None):
        self.kb_dir = kb_path or KB_DIR
        self.chunks: List[LegalChunk] = []
        self._load_chunks()
        self.tokenized_corpus = [_tokenize(f"{c.act} {c.section} {c.text}") for c in self.chunks]
        self.bm25 = BM25Okapi(self.tokenized_corpus) if self.tokenized_corpus else None

    def _load_chunks(self) -> None:
        if not self.kb_dir.exists():
            return
        for json_file in sorted(self.kb_dir.glob("*.json")):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self.chunks.append(
                        LegalChunk(
                            act=item["act"],
                            section=item["section"],
                            text=item["text"],
                            source_url=item["source_url"],
                        )
                    )

    def retrieve(self, query: str, top_k: int = 4, threshold: float = 1.0) -> List[LegalChunk]:
        if not self.bm25 or not self.chunks:
            return []
        tokenized_query = _tokenize(query)
        if not tokenized_query:
            return []
        scores = self.bm25.get_scores(tokenized_query)
        scored_pairs = []
        for idx, score in enumerate(scores):
            if score >= threshold:
                c = self.chunks[idx].model_copy()
                c.score = round(float(score), 3)
                scored_pairs.append((c.score, c))
        scored_pairs.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored_pairs[:top_k]]
