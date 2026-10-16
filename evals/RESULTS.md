# Evaluation results

The six cases and expected behaviors are synthetic and hand-authored. The saved-fixture run passed 6/6 ([report](results-saved.json)). The Python suite passed 54 tests.

The first live run against `glm-5.3-flash` passed 3/6 cases in 2 minutes 19 seconds ([initial report](results-live-initial.json)). It missed a clean-intake fact expectation, a tire-pressure follow-up, and returned an empty or incomplete explicit-correction result; the pipeline correctly withheld that handoff.

The later live run returned valid pipeline results for all six cases and passed 5/6 assertions in 2 minutes 29 seconds ([raw report](results-live.json)). The only assertion mismatch was the warning value "tire pressure warning is showing on the dash" versus the expected phrase "tire pressure warning." After allowing expected phrases inside longer free-text fact values, Promptfoo regraded the same outputs 6/6 ([regraded report](results-live-regraded.json)); this made no model calls, and the raw live report remains unchanged. Mileage comparison stays numeric, identifiers must match exactly, and correction and conflict values keep their stricter comparisons.

The vehicle-context case exercises the pipeline filter that removes questions already answered by supplied vehicle data; it does not test the model alone. Exact quote matching proves that a quote occurs in the named turn and speaker, not that it semantically supports the extracted claim. These selected cases do not establish broad reliability or service-time savings.

## Reproduce

From the repository root, install the pinned evaluator and activate the Python environment so Promptfoo can import the provider:

```sh
npm ci
source .venv/bin/activate
npm run eval -- --output evals/results-saved.json
```

A fresh live run requires `INTAKE_API_KEY` in the environment and sends six requests to the configured provider:

```sh
INTAKE_EVAL_MODE=live npm run eval -- --output evals/results-live.json
```
