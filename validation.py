"""Strict schema and deterministic citation/evidence checks."""

class ValidationError(ValueError):
    pass


def validate_answer(result: dict, retrieved: list[dict]) -> dict:
    errors = []
    if not isinstance(result, dict):
        return {"valid": False, "errors": ["result must be a JSON object"]}
    if set(result) != {"supported", "answer", "citations"}:
        errors.append("answer object must contain exactly supported, answer, and citations")
    if type(result.get("supported")) is not bool:
        errors.append("supported must be a boolean")
    answer = result.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        errors.append("answer must be a nonempty string")
    citations = result.get("citations")
    if not isinstance(citations, list):
        errors.append("citations must be an array")
        citations = []
    by_id = {(c["doc_id"], c["chunk_id"]): c for c in retrieved}
    if result.get("supported") is True and not citations:
        errors.append("supported answer requires citations")
    for citation in citations:
        if not isinstance(citation, dict) or not all(isinstance(citation.get(k), str) and citation[k] for k in ("doc_id", "chunk_id", "quote")):
            errors.append("each citation requires nonempty doc_id, chunk_id, and quote")
            continue
        if set(citation) != {"doc_id", "chunk_id", "quote"}:
            errors.append("citation object contains unexpected fields")
        chunk = by_id.get((citation["doc_id"], citation["chunk_id"]))
        if chunk is None:
            errors.append("citation is not in retrieved chunks")
        elif citation["quote"] not in chunk["text"]:
            errors.append("citation quote is not an exact substring of cited evidence")
        elif result.get("supported") is True:
            import re
            answer_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", answer)
            evidence_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", citation["quote"])
            if any(number not in evidence_numbers for number in answer_numbers):
                errors.append("answer contains a number absent from cited evidence")
    if result.get("supported") is False and not isinstance(answer, str) or (result.get("supported") is False and isinstance(answer, str) and not any(x in answer.lower() for x in ("not", "unknown", "insufficient", "cannot", "don't", "does not", "unable"))):
        errors.append("unsupported answer must clearly state a refusal or gap")
    return {"valid": not errors, "errors": errors}
