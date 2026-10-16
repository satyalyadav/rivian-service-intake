# Service intake

Turns a service call into a technician write-up where every extracted detail (reported facts, corrections, and unresolved conflicts) cites the words that support it. Anything the call left unknown becomes an open question. It does not diagnose a vehicle or make repair, coverage, or scheduling decisions.

Demo: <https://rivian-service-intake.streamlit.app>. Four synthetic conversations work without a model key, and the "Your own" pill takes a pasted call.

## Run it locally

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1
```

Live analysis uses DeepSeek V4.1 Flash through OpenCode Go's OpenAI-compatible endpoint. To turn it on locally, set `INTAKE_API_KEY` in the environment or in `.streamlit/secrets.toml`. Change `INTAKE_MODEL` for a different model, or `INTAKE_BASE_URL` for a different OpenAI-compatible provider. Without a key, the four saved conversations still work.

## Tests

`python -m pytest tests/ -q` checks the saved conversations end to end, the quote and correction rules, and the UI flows. `npm ci && npm run eval -- --output evals/results-saved.json` runs the same conversations through the promptfoo suite; set `INTAKE_EVAL_MODE=live` to call the model instead.

Exact quote matching proves a quote appears under the named speaker and turn; it does not prove the quote supports the claim. A live analysis takes roughly 10 to 60 seconds.
