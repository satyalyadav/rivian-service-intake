# Service intake

Turns a service call into a technician write-up where every extracted detail (reported facts, corrections, and unresolved conflicts) cites the words that support it. The advisor reviews the draft before passing it on, and anything the call left unknown becomes an open question. It does not diagnose a vehicle or make repair, coverage, or scheduling decisions.

Live demo: <https://rivian-service-intake.streamlit.app>. Four synthetic conversations run without a model key, and the "Your own" pill takes a pasted conversation with a live model key set on the server.

## Run locally

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1
```

## Live analysis

Set these in the server environment, or in the Streamlit secrets box when deployed:

| Variable | Default | Purpose |
| --- | --- | --- |
| `INTAKE_API_KEY` | unset | Provider key. Without it the four saved conversations still work and live analysis is disabled. |
| `INTAKE_MODEL` | `deepseek-v4.1-flash` | Model ID on the OpenAI-compatible endpoint. |
| `INTAKE_BASE_URL` | `https://opencode.ai/inference/go/openai/v1` | Endpoint. |
| `INTAKE_PROCESS_REQUEST_LIMIT` | `24` | Live requests per Python process. |

Live requests go to the configured provider under that provider's data policy; the default provider documents 0-day retention for this model. Use synthetic data. The app caps conversations at 12,000 characters and 100 turns, holds calls to a 90-second read timeout, and saves no transcripts.

## Hosting

Streamlit Community Cloud, entry file `app.py`, key in the app's secrets box. Free apps sleep after 12 idle hours; the next visit shows a wake button and takes about a minute.

## Tests and checks

```sh
python -m pytest tests/ -q                                   # 22 focused checks
npm ci && npm run eval -- --output evals/results-saved.json   # promptfoo, 4 saved cases
INTAKE_EVAL_MODE=live npm run eval -- --output evals/results-live.json  # one model call per case
```

The Python checks cover the saved conversations end to end, the quote and correction rules, input limits, provider request shape and failure handling, and the UI flows. Both promptfoo modes pass; raw reports are in `evals/`.

Exact quote matching proves a quote appears under the named speaker and turn; it does not prove the quote supports the claim. Known limits: a live analysis takes roughly 10 to 60 seconds, and it rejects a correction when the call states the new value before the old one.
