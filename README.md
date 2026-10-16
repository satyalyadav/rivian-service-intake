# Service intake review

This prototype turns a service call into a technician write-up. Every line in the write-up points back to the words in the conversation, the advisor reviews the draft before passing it on, and anything the call left unknown becomes an open question. It does not diagnose a vehicle or make repair, coverage, or scheduling decisions.

Four synthetic conversations work without a model key. Their saved results came from real runs of the same pipeline on those conversations, and they pass the same validation the live path uses. Editing a conversation enables a live model request when the server has a key.

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
| `INTAKE_MODEL` | `deepseek-v4.1-flash` | Provider model ID. |
| `INTAKE_PROCESS_REQUEST_LIMIT` | `24` | Maximum live requests handled by one Python process, from 1 to 500. |

The default model ID comes from the OpenCode Go model list. The OpenCode Go documentation describes that service as designed primarily for OpenCode and similar coding-agent traffic and does not confirm service-intake use as a supported workload. The same documentation lists 0-day data retention for DeepSeek V4.1 Flash. Verify the workload fit and the current terms with the provider before wider use. See the [OpenCode Go documentation](https://opencode.ai/v2/docs/console/go/).

The app limits conversations to 12,000 characters and 100 turns. Vehicle context has bounded fields. Provider calls have a 90 second read timeout and a 64 KB response limit. The process cap resets when the process restarts. The app does not save submitted conversations, but live requests go to the configured provider and follow that provider's data policies. Use synthetic data for this demo.

## Hosting

The app runs on Streamlit Community Cloud at <https://rivian-service-intake.streamlit.app>. Connect this repository, set the entry file to `app.py`, and paste the provider key into the app's secrets box:

```toml
INTAKE_API_KEY = "..."
```

The app reads `INTAKE_MODEL`, `INTAKE_BASE_URL`, and `INTAKE_PROCESS_REQUEST_LIMIT` from Streamlit secrets when the environment does not set them. Free Community Cloud apps sleep after 12 hours without traffic; the next visit shows a wake button and takes about a minute to come back.

## Run evaluations and tests

The Python suite covers parsing, validation, rendering, provider behavior, and the UI:

```sh
source .venv/bin/activate
python -m pytest tests/ -q
```

Promptfoo evaluation uses Node.js 22.22 or newer. Activate the project Python environment in the shell where you run Promptfoo so its Python provider can import the app dependencies, then install the pinned evaluator:

```sh
source .venv/bin/activate
npm ci
npm run eval -- --output evals/results-saved.json
```

Saved mode checks the four conversations against expectations written before the model runs. To call the configured model for each case, set `INTAKE_EVAL_MODE=live` and `INTAKE_API_KEY`, then run:

```sh
npm run eval -- --output evals/results-live.json
```

Live mode never falls back to saved results. See the [Promptfoo Python integration guide](https://www.promptfoo.dev/docs/integrations/python/).

## Verification

State as of 2026-10-16, on the current conversations and prompt:

- The Python suite passed 51 tests.
- Saved fixtures passed 4 of 4 checks. A live run of the same four cases passed 4 of 4 and is saved in `evals/results-live.json`.
- Browser review of the deployed layout confirmed that the Streamlit toolbar and menu are hidden, the write-up renders with line references, and clicking a source quote highlights those words in the conversation.
- The deployed app completed a live model run on an edited conversation and rendered the fresh write-up (checked 2026-10-16).

Exact quote matching proves that a quote appears under the named speaker and turn; it does not prove semantic support for the extracted claim. The four conversations do not establish broad reliability or operational time savings.

Known limits: a live analysis takes roughly 10 to 60 seconds, and the validator rejects a correction when the call states the new value before the old one, because correction history must read in the order the statements were made.
