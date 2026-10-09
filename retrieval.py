"""Dependency-free BM25 retrieval."""
import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class BM25Index:
    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.tokens = [tokenize(c["text"]) for c in chunks]
        self.lengths = [len(t) for t in self.tokens]
        self.avg_length = sum(self.lengths) / max(len(self.lengths), 1)
        self.document_frequency = Counter(term for terms in self.tokens for term in set(terms))

    def search(self, question: str, top_k: int = 4) -> list[dict]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must be nonempty")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        terms = set(tokenize(question))
        scored = []
        for chunk, tokens, length in zip(self.chunks, self.tokens, self.lengths):
            counts = Counter(tokens)
            score = 0.0
            for term in terms:
                frequency = counts[term]
                if not frequency:
                    continue
                idf = math.log(1 + (len(self.chunks) - self.document_frequency[term] + 0.5) /
                               (self.document_frequency[term] + 0.5))
                score += idf * frequency * (self.k1 + 1) / (
                    frequency + self.k1 * (1 - self.b + self.b * length / max(self.avg_length, 1)))
            if score > 0:
                scored.append({**chunk, "score": round(score, 6)})
        return sorted(scored, key=lambda item: (-item["score"], item["doc_id"], item["chunk_id"]))[:top_k]
