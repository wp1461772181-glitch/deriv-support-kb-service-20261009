"""Replaceable extractive and DeepSeek JSON generators."""
import json
import time
import urllib.error
import urllib.request
from retrieval import tokenize
from prompting import build_prompt

STOPWORDS = set("a an the is are was were do does did can could would should how what when where who which many much soon per for to of in on at by from and or my your users user account please tell me about allowed limit policy standard after within".split())
ALIASES = {"expiry":"expire", "expires":"expire", "expiration":"expire", "validity":"expire", "valid":"expire", "remain":"expire", "stays":"expire", "stay":"expire", "long":"expire", "duration":"expire", "hours":"hour", "minutes":"minute", "emails":"email", "permitted":"allow", "requests":"request", "quotas":"quota", "limits":"limit", "fees":"fee", "charges":"fee", "cost":"fee", "required":"require", "requires":"require", "requirements":"require", "documents":"id", "document":"id", "geographic":"country", "countries":"country", "region":"country", "insurance":"insurance"}

def norm(term):
    term = ALIASES.get(term, term)
    if len(term) > 4 and term.endswith("ies"): return term[:-3] + "y"
    if len(term) > 4 and term.endswith("s") and not term.endswith("ss"): return term[:-1]
    return term

def extractive_generate(question: str, chunks: list[dict], min_score: float = 0.35) -> dict:
    refusal = {"supported": False, "answer": "The available documents do not provide enough evidence to answer this question.", "citations": []}
    if not chunks or chunks[0]["score"] < min_score: return refusal
    qraw = {norm(x) for x in tokenize(question)}
    qterms = qraw - {norm(x) for x in STOPWORDS}
    if not qterms: return refusal
    # These terms impose specific dimensions that must occur in the evidence.
    candidates = []
    for chunk in chunks:
        for line in chunk["text"].splitlines():
            if line.lstrip().startswith("#"): continue
            for sentence in line.split(". "):
                sentence = sentence.strip().rstrip(".")
                terms = {norm(x) for x in tokenize(sentence)}
                if not qterms.issubset(terms):
                    continue
                numeric_request = bool(qraw & {"many", "much", "number", "amount", "rate", "percentage", "how", "long"})
                has_numeric = any(x.isdigit() for x in terms) or bool(terms & {"one","two","three","four","five","six","seven","eight","nine","ten","once"})
                if numeric_request and not has_numeric: continue
                candidates.append((len(qterms), chunk, sentence))
    if not candidates: return refusal
    _, chunk, sentence = max(candidates, key=lambda x: (x[0], -len(x[2])))
    return {"supported": True, "answer": sentence + ".", "citations": [{"doc_id": chunk["doc_id"], "chunk_id": chunk["chunk_id"], "quote": sentence}]}

def deepseek_generate(question: str, chunks: list[dict], api_key: str, model: str = "deepseek-flash", timeout: int = 25) -> dict:
    payload = {"model": model, "messages": [{"role": "user", "content": build_prompt(question, chunks)}],
               "response_format": {"type": "json_object"}, "max_tokens": 1400, "stream": False, "thinking": {"type": "disabled"}}
    request = urllib.request.Request("https://api.deepseek.com/chat/completions", data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    last = "provider error"
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response: body = json.loads(response.read().decode())
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip(): raise ValueError("empty content")
            result = json.loads(content)
            if not isinstance(result, dict): raise ValueError("content is not an object")
            return result
        except urllib.error.HTTPError as exc:
            last = "HTTPError"
            if attempt == 0 and (exc.code == 429 or 500 <= exc.code < 600): time.sleep(0.1); continue
            break
        except json.JSONDecodeError as exc:
            last = "JSONDecodeError"
            if attempt == 0: time.sleep(0.1); continue
            break
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, IndexError, TypeError) as exc:
            last = type(exc).__name__
            if attempt == 0: time.sleep(0.1); continue
            break
    raise RuntimeError(f"DeepSeek request failed ({last})") from None

def generate(question: str, chunks: list[dict], provider: str = "extractive", api_key: str | None = None) -> tuple[dict, str, dict | None]:
    if provider == "deepseek":
        if not api_key: raise RuntimeError("DeepSeek provider requires DEEPSEEK_API_KEY")
        return deepseek_generate(question, chunks, api_key), "deepseek", None
    if provider == "auto" and api_key:
        try: return deepseek_generate(question, chunks, api_key), "deepseek", None
        except RuntimeError as exc: return extractive_generate(question, chunks), "extractive", {"provider":"deepseek", "reason":str(exc)}
    return extractive_generate(question, chunks), "extractive", None
