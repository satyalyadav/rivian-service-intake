# Service intake review

This prototype turns a service conversation into sourced details, correction history, unresolved conflicts, follow-up questions, and a draft technician handoff. The advisor reviews the draft before using it. It does not diagnose a vehicle or make repair, coverage, or scheduling decisions.

Six synthetic examples work without a model key. They are hand-authored fixtures, not model results. Editing a transcript requires a fresh request and a server-side key.

## Run the app

Use Python 3.12 or newer to run the app.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1
```

## Configure live processing

Set these variables in the server environment before starting Streamlit:

| Variable | Default | Purpose |
| --- | --- | --- |
| `INTAKE_API_KEY` | unset | Server-side provider key. Live processing stays disabled without it. |
| `INTAKE_BASE_URL` | `https://opencode.ai/inference/go/openai/v1` | OpenAI-compatible API base URL. |
| `INTAKE_MODEL` | `glm-5.3-flash` | Provider model ID. |
| `INTAKE_PROCESS_REQUEST_LIMIT` | `24` | Maximum live requests handled by one Python process, from 1 to 500. |

OpenCode Go currently documents the direct OpenAI-compatible endpoint and lists `glm-5.3-flash` as a model ID. Its docs say Go is designed primarily for OpenCode and similar coding-agent traffic. They do not confirm service-intake use as a supported workload, so verify that fit with the provider before wider use. See the [OpenCode Go documentation](https://opencode.ai/v2/docs/console/go/).

The app limits transcripts to 12,000 characters and 100 turns. Vehicle context has bounded fields. Provider calls have a 90 second read timeout and a 64 KB response limit. The Python process cap resets when the process restarts. The app does not save submitted transcripts, but live requests go to the configured provider and follow that provider's data policies. Use synthetic data for this demo.

## Run evaluations and tests

The app does not require Node.js. Promptfoo evaluation uses Node.js 22.22 or newer. Activate the project Python environment in the shell where you run Promptfoo so its Python provider can import the app dependencies, then install the pinned evaluator:

```sh
source .venv/bin/activate
npm ci
npm run eval -- --output evals/results-saved.json
```

The evaluation command sets one worker and disables cache, sharing, and database writes. To call the configured model for each case, set `INTAKE_EVAL_MODE=live` and `INTAKE_API_KEY` in the environment, then run:

```sh
npm run eval -- --output evals/results-live.json
```

Live mode never falls back to fixtures. See the [Promptfoo Python integration guide](https://www.promptfoo.dev/docs/integrations/python/).

## Verification

The Python suite passed 54 tests. Saved fixtures passed 6 of 6 cases. In the latest live run, all six pipeline results were valid; the original assertions passed 5 of 6, then the same captured outputs passed 6 of 6 after the checker allowed expected phrases inside longer free-text fact values. That regrade made no model calls. See [evaluation results](evals/RESULTS.md) and the linked reports.

- Native T3 browser review confirmed evidence selection including both correction quotes, stale-edit removal of the handoff and download, and handoff blocking on malformed input. A fresh, unseen screen-black transcript edited with a known VIN produced a valid sourced note and three neutral questions; its 562-byte download matched the rendered note.
- Escaped `<img>` text did not create an image or execute. A 390-pixel viewport had no horizontal overflow with a 300-character unbroken string, and Windows checks of `localhost` and `127.0.0.1` both returned HTTP 200.
- The clipboard button reported `Copied`, but browser permissions blocked readback with `NotAllowedError`, so clipboard contents were not byte-verified.

These checks cover six selected synthetic behaviors and strict structure/evidence boundaries. Exact quote matching proves that a quote appears under the named speaker and turn; it does not prove semantic support for the extracted claim. The examples do not establish broad reliability or operational time savings.

## Hosting

This prototype remains local for review. Public hosting is not configured.
