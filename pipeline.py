"""Evaluation and single-question orchestration."""
import json, logging
from pathlib import Path
from ingestion import load_documents, flatten_documents
from retrieval import BM25Index
from generation import generate
from validation import validate_answer

LOG = logging.getLogger("support_kb")
REFUSAL = {"supported":False,"answer":"The generated response could not be validated against the retrieved evidence.","citations":[]}

def read_questions(path):
    questions = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(questions, list) or not questions: raise ValueError("questions must be a nonempty JSON array")
    ids=set()
    for item in questions:
        if not isinstance(item,dict) or not isinstance(item.get("id"),str) or not item["id"].strip() or not isinstance(item.get("question"),str) or not item["question"].strip(): raise ValueError("each question requires nonempty id and question")
        if item["id"] in ids: raise ValueError(f"duplicate question id: {item['id']}")
        ids.add(item["id"])
    return questions

def run_question(question, index, provider="extractive", api_key=None):
    if not isinstance(question,str) or not question.strip(): raise ValueError("question must be nonempty")
    chunks=index.search(question); LOG.info(json.dumps({"stage":"retrieval","count":len(chunks)}))
    error=None; fallback=None; used=provider
    try: answer, used, fallback = generate(question,chunks,provider,api_key)
    except Exception as exc:
        error=str(exc) if isinstance(exc,RuntimeError) else f"generation failed ({type(exc).__name__})"
        answer=dict(REFUSAL); used=provider
    initial=validate_answer(answer,chunks)
    checked=initial
    if not initial["valid"]:
        answer=dict(REFUSAL); checked=validate_answer(answer,chunks)
    evidence=[{"doc_id":c["doc_id"],"chunk_id":c["chunk_id"],"quote":c["text"]} for c in chunks]
    LOG.info(json.dumps({"stage":"generation","provider":used,"valid":initial["valid"],"error":error,"fallback":fallback},ensure_ascii=False))
    LOG.info(json.dumps({"stage":"validation","valid":checked["valid"],"initial_valid":initial["valid"]}))
    return {"question":question,**answer,"provider":used,"provider_error":error,"fallback":fallback,"retrieved_sources":chunks,"evidence":evidence,"validation":{"valid":checked["valid"],"errors":checked["errors"],"generation_validation":initial,"final_validation":checked}}

def evaluate(corpus, questions_path, output_dir, provider="extractive", api_key=None, log_file=None):
    docs=load_documents(corpus); chunks=flatten_documents(docs); index=BM25Index(chunks)
    questions=read_questions(questions_path)
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    if log_file:
        target=Path(log_file); target.parent.mkdir(parents=True,exist_ok=True)
        handler=logging.FileHandler(target,encoding="utf-8"); handler.setFormatter(logging.Formatter("%(message)s")); LOG.addHandler(handler)
    LOG.info(json.dumps({"stage":"ingestion","documents":len(docs),"chunks":len(chunks)}))
    retrieval_results=[]; answers=[]; validations=[]
    for item in questions:
        retrieved=index.search(item["question"])
        try: result=run_question(item["question"],index,provider,api_key)
        except Exception as exc:
            result={"question":item["question"],**REFUSAL,"provider":provider,"provider_error":f"evaluation error ({type(exc).__name__})","fallback":None,"retrieved_sources":retrieved,"evidence":[],"validation":{"valid":False,"errors":[f"evaluation error ({type(exc).__name__})"],"generation_validation":{"valid":False,"errors":[]},"final_validation":{"valid":False,"errors":[]}}}
        retrieval_results.append({"question_id":item["id"],"retrieved_chunks":retrieved})
        actual="error" if result["provider_error"] else ("answerable" if result["supported"] else "refused")
        expected=item.get("expected_behavior")
        match=None if expected not in ("answerable","partial","unanswerable") else ((result["supported"] if expected=="answerable" else not result["supported"]) if actual!="error" else False)
        answers.append({"question_id":item["id"],"answer":result["answer"],"citations":[c["doc_id"] for c in result["citations"]],"evidence":result["evidence"],"supported":result["supported"],"provider":result["provider"],"provider_error":result["provider_error"],"fallback":result["fallback"],"expected_behavior":expected,"actual_behavior":actual,"expectation_match":match})
        validations.append({"question_id":item["id"],**result["validation"],"provider_error":result["provider_error"]})
    for name,data in (("retrieval_results.json",retrieval_results),("answers.json",answers),("validation_report.json",{"checks":validations,"all_valid":all(x["valid"] and not x["provider_error"] for x in validations),"count":len(validations)})):
        (out/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return {"documents":len(docs),"chunks":len(chunks),"questions":len(questions),"validations_passed":sum(v["valid"] and not v["provider_error"] for v in validations),"behavior_matches":sum(a["expectation_match"] is True for a in answers),"behavior_mismatches":sum(a["expectation_match"] is False for a in answers),"output_dir":str(out)}
