import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from io import BytesIO
from ingestion import load_documents, flatten_documents
from retrieval import BM25Index
from generation import extractive_generate, deepseek_generate
from pipeline import run_question, evaluate, read_questions
from validation import validate_answer

ROOT=Path(__file__).resolve().parents[1]

class PipelineTests(unittest.TestCase):
    def setUp(self): self.index=BM25Index(flatten_documents(load_documents(ROOT/"docs")))

    def test_original_nine_expected_behavior_and_facts(self):
        for q in json.loads((ROOT/"questions.json").read_text()):
            result=run_question(q["question"],self.index)
            self.assertEqual(result["supported"],q["expected_behavior"]=="answerable",q["id"])
            if result["supported"]:
                for phrase in q["expected_evidence"]: self.assertIn(phrase.lower(),result["answer"].lower(),q["id"])

    def test_unknown_qualifiers_and_partial_multipart_refused(self):
        for q in ("What is the identity verification fee?","How many API requests are allowed per hour?","What is the enterprise API quota?","Does insurance cover identity verification in Singapore?","What documents are required and what is the fee?"):
            self.assertFalse(run_question(q,self.index)["supported"],q)

    def test_paraphrase_and_verified_readme_question(self):
        r=run_question("How long do reset links remain valid?",self.index)
        self.assertTrue(r["supported"]); self.assertIn("30 minutes",r["answer"])

    def test_txt_ingestion_and_duplicate_stem_chunk_ids(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,"alpha.txt").write_text("Retention is 45 days.\n\nSecond policy paragraph.",encoding="utf-8")
            Path(d,"alpha.md").write_text("Separate rules apply to contractors.",encoding="utf-8")
            chunks=flatten_documents(load_documents(d,24)); self.assertTrue(any(c["doc_id"]=="alpha.txt" for c in chunks))
            self.assertEqual(len({(c["doc_id"],c["chunk_id"]) for c in chunks}),len(chunks))
            self.assertEqual(BM25Index(chunks).search("retention 45 days")[0]["doc_id"],"alpha.txt")

    def test_invalid_corpus_and_questions(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): load_documents(d)
            Path(d,"empty.txt").write_text(" ")
            with self.assertRaises(ValueError): load_documents(d)
            with self.assertRaises(ValueError): load_documents(d,max_chars=0)
            qp=Path(d,"q.json"); qp.write_text('[{"id":"x","question":"x"},{"id":"x","question":"y"}]')
            with self.assertRaises(ValueError): read_questions(qp)

    def test_validation_failures_preserved_and_numeric_mismatch(self):
        c=[{"doc_id":"a.md","chunk_id":"a_1","text":"Limit is 120 requests per minute."}]
        answer={"supported":True,"answer":"999 requests per minute","citations":[{"doc_id":"a.md","chunk_id":"a_1","quote":c[0]["text"]}]}
        self.assertFalse(validate_answer(answer,c)["valid"])
        with patch("pipeline.generate",return_value=({"supported":"false","answer":"bad","citations":[]},"fake",None)):
            out=run_question("requests",BM25Index(c)); self.assertFalse(out["validation"]["generation_validation"]["valid"]); self.assertTrue(out["validation"]["final_validation"]["valid"])

    def test_orchestration_preserves_schema_and_citation_failures(self):
        c=[{"doc_id":"a.md","chunk_id":"a_1","text":"Limit is 120 requests per minute.","score":2.0}]
        bad_results=[None,{"supported":True,"answer":"120 requests","citations":"bad"},{"supported":True,"answer":"120 requests","citations":[{"doc_id":"fake.md","chunk_id":"x","quote":"Limit is 120 requests per minute."}]}]
        for bad in bad_results:
            with patch("pipeline.generate",return_value=(bad,"mock",None)):
                result=run_question("API requests per minute",BM25Index(c))
            self.assertFalse(result["validation"]["generation_validation"]["valid"])
            self.assertTrue(result["validation"]["final_validation"]["valid"])
            self.assertFalse(result["supported"])

    def test_malformed_provider_full_report_and_retry_payload(self):
        response=BytesIO(b'{"choices":[{"message":{"content":"not-json"}}]}')
        with patch("urllib.request.urlopen",side_effect=[response,BytesIO(b'{"choices":[{"message":{"content":"not-json"}}]}')]) as call:
            with self.assertRaisesRegex(RuntimeError,"JSONDecodeError"): deepseek_generate("q",[],"placeholder")
            payload=json.loads(call.call_args.args[0].data); self.assertEqual(payload["thinking"],{"type":"disabled"}); self.assertGreaterEqual(payload["max_tokens"],1200)
        with tempfile.TemporaryDirectory() as d:
            qp=Path(d,"q.json"); qp.write_text('[{"id":"x","question":"known API requests per minute?","expected_behavior":"answerable"}]')
            with patch("pipeline.generate",side_effect=RuntimeError("DeepSeek request failed (URLError)")):
                summary=evaluate(ROOT/"docs",qp,d,"deepseek")
            report=json.loads(Path(d,"validation_report.json").read_text()); self.assertEqual(summary["validations_passed"],0); self.assertIn("URLError",report["checks"][0]["provider_error"])

    def test_custom_txt_end_to_end_does_not_match_unrelated_policy(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,"policy.txt").write_text("Contractor access requires manager approval.")
            index=BM25Index(flatten_documents(load_documents(d)))
            self.assertTrue(run_question("Does contractor access require manager approval?",index)["supported"])
            self.assertFalse(run_question("What is the contractor access fee?",index)["supported"])

if __name__=="__main__": unittest.main()
