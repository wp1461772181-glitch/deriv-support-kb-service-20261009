"""Run the local question evaluation corpus."""
import argparse
import json
import logging
from pipeline import evaluate
from prompting import load_env_key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", default="docs")
    parser.add_argument("--questions", default="questions.json")
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--provider", choices=("extractive", "deepseek", "auto"), default="extractive")
    parser.add_argument("--env-file")
    parser.add_argument("--log-file", default="logs/pipeline.jsonl")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    summary = evaluate(args.docs, args.questions, args.output_dir, args.provider, load_env_key(args.env_file), args.log_file)
    print(json.dumps(summary, indent=2))
    if summary["validations_passed"] != summary["questions"] or summary["behavior_mismatches"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
