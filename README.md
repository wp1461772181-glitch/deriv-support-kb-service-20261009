# Local Support Knowledge Base

A small Python 3.10+ support assistant with local Markdown ingestion, BM25 retrieval, replaceable generation and deterministic citation checks. Runtime uses only the standard library.

## Quick start

```bash
python3 run_pipeline.py
```

`python3` must resolve to Python 3.10 or newer. The verified environment used Python 3.12; an executable named exactly `python3.10` is not required.

This reads `docs/` and `questions.json`, then writes `retrieval_results.json`, `answers.json` and `validation_report.json` in the current output directory. Logs go to stderr; stdout contains only the run summary JSON.

Ask a verified question offline:

```bash
python3 app.py --question "How long do reset links remain valid?"
```

The CLI prints answer, citations, validation and retrieved source chunks as JSON. Use `--docs PATH` with another `.md` or `.txt` corpus. Evaluation supports `--questions PATH`, `--output-dir PATH`, and `--log-file PATH` (default `logs/pipeline.jsonl`). Stdout contains JSON only; operational logs go to stderr and the JSONL file. A provider or generation failure returns a refusal and a nonzero CLI status.

## DeepSeek (optional)

Offline extractive mode is the default and requires no network or key. To use DeepSeek, provide `DEEPSEEK_API_KEY` in the environment or pass an explicit env file; `.env.example` is a placeholder only. The key is read in process memory and is never written to output or logs.

```bash
python3 run_pipeline.py --provider deepseek --env-file /path/to/local.env --output-dir artifacts/deepseek
python3 app.py --provider deepseek --env-file /path/to/local.env --question "How many API requests are allowed per minute?"
```

`--provider auto` attempts DeepSeek when a key is present and falls back to extractive generation on provider failure; the attempted provider and safe failure reason are recorded. DeepSeek requests disable thinking and allow a bounded retry for transient/network/empty/malformed responses. The DeepSeek request settings follow the [official API reference](https://api-docs.deepseek.com/) and [JSON output mode](https://api-docs.deepseek.com/guides/json_mode).

## Architecture

```text
docs/*.md -> ingestion.py -> chunk metadata -> retrieval.py (BM25)
                                             -> prompting.py -> generation.py
Question ------------------------------------^                    |
                                              validation.py <-----+
```

- `ingestion.py`: deterministic Markdown loading and paragraph-aware chunks with document and chunk IDs.
- `retrieval.py`: dependency-free BM25 top-k search.
- `prompting.py`: separate, injection-aware prompt and explicit key loading.
- `generation.py`: conservative local extractive generator or DeepSeek JSON mode.
- `validation.py`: strict boolean/schema, retrieved citation membership, and exact evidence quote checks.
- `pipeline.py`: evaluation orchestration and artifact output; `app.py` exposes one-question CLI.

## Grounding and refusal

Local answers select a sentence from retrieved text and require coverage of every normalized material question term; quantity questions also need numeric evidence. A small general alias map handles ordinary inflections and paraphrases. This errs toward refusal when evidence uses materially different terminology. DeepSeek is instructed to refuse incomplete questions and cite exact quotations. Both paths pass the same deterministic validator; malformed or unsupported citations fail closed to a refusal. Generation validation errors remain visible even when the final fallback refusal validates.

Validation proves that cited chunks were retrieved and quotes literally occur in them. It rejects answer numbers missing from the quote, but it does **not** prove full semantic entailment. Expected behavior labels are only used for evaluation comparison, never as inference input. Public evaluation citations are document ID strings; the evidence field contains all retrieved passages. Exact model-selected quote checks are performed internally and are returned by the one-question CLI, but are not retained as exact selected quotes in evaluation outputs.

## Practical improvement (Stretch)

The offline extractive path includes a weak-retrieval refusal gate: if the top raw BM25 score is below `min_score=0.35`, it refuses before selecting a sentence. This bounded, dependency-free safeguard was chosen to reduce unsupported answers when lexical retrieval is weak, while keeping the project runnable offline without vector infrastructure. The score is not calibrated confidence and the gate is not applied as a pre-generation check to DeepSeek. See [DESIGN_NOTES.md](DESIGN_NOTES.md) for the as-built design, acceptance trace, and limitations.

## Tests and tradeoffs

```bash
python3 -m unittest discover -s tests
python3 package_artifacts.py
```

BM25 keeps setup simple and replaceable, but lexical retrieval can miss synonyms. There is no database, hosted service, persistent index, or semantic entailment model. A real deployment would need stronger claim-level entailment checks and operational controls. `requirements.txt` documents the no-runtime-dependency setup.
