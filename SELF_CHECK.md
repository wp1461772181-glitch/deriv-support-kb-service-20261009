# Self check

The project targets Python 3.10 or newer. The recorded verification environment used Python 3.12.13; the host `/usr/bin/python3` was Python 3.9.6, so commands require `python3` to resolve to a compatible interpreter.

## Recorded verification

- Focused unit suite: 9 tests passed with Python 3.12.13.
- Offline evaluation: all 9 support/refusal expectations matched and all 9 structural checks passed.
- CLI demo: `python3 app.py --question "How long do reset links remain valid?"` returns the verified 30-minute fact.
- Primary-process DeepSeek acceptance: 9/9 behavior matches, 9/9 structural checks, zero provider errors, and zero fallbacks; three additional real checks passed (new HTTP 429, unknown identity fee, and partly supported documents-plus-fee).
- These results are recorded in `artifacts/acceptance_summary.json`. Root artifacts contain the successful DeepSeek run; `artifacts/offline/` and `artifacts/deepseek/` preserve path-specific outputs.
- An earlier worker-sandbox network attempt failed, but it is historical and superseded by the successful primary-process verification above; it is not evidence of a provider outage.

The extractive checker is intentionally conservative and lexical. It checks literal quotations and catches answer numbers absent from the cited quote, but it does not establish complete semantic entailment. See `DESIGN_NOTES.md` for implementation details and additional boundaries.
