"""Local Markdown/text loading and paragraph-aware chunking."""
from pathlib import Path
import re


def load_documents(directory: str | Path, max_chars: int = 900) -> list[dict]:
    if max_chars <= 0:
        raise ValueError("chunk size must be positive")
    root = Path(directory)
    if not root.is_dir():
        raise ValueError(f"corpus directory does not exist: {root}")
    docs = []
    paths = sorted((*root.glob("*.md"), *root.glob("*.txt")))
    if not paths:
        raise ValueError(f"corpus contains no .md or .txt documents: {root}")
    seen_ids = set()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            continue
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks, current = [], ""
        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) + 1 > max_chars:
                chunks.append(current)
                current = ""
            if len(paragraph) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(paragraph[i:i + max_chars] for i in range(0, len(paragraph), max_chars))
            else:
                current = f"{current}\n{paragraph}" if current else paragraph
        if current:
            chunks.append(current)
        stem = path.stem
        if stem in seen_ids:
            stem = f"{stem}_{path.suffix[1:]}"
        seen_ids.add(path.stem)
        docs.append({"doc_id": path.name, "chunks": [
            {"doc_id": path.name, "chunk_id": f"{stem}_{i}", "text": chunk}
            for i, chunk in enumerate(chunks, 1)]})
    if not docs:
        raise ValueError(f"corpus contains no nonempty documents: {root}")
    return docs


def flatten_documents(documents: list[dict]) -> list[dict]:
    return [chunk for doc in documents for chunk in doc["chunks"]]
