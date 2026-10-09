"""Ask one question: python app.py --question '...'"""
import argparse
import json
import logging
from ingestion import load_documents, flatten_documents
from retrieval import BM25Index
from pipeline import run_question
from prompting import load_env_key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    parser.add_argument("--docs", default="docs")
    parser.add_argument("--provider", choices=("extractive", "deepseek", "auto"), default="extractive")
    parser.add_argument("--env-file")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    index = BM25Index(flatten_documents(load_documents(args.docs)))
    result = run_question(args.question, index, args.provider, load_env_key(args.env_file))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["validation"]["valid"] or result["provider_error"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
