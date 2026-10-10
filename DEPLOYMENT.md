# Hosting

Live preview: https://document-review-agent.streamlit.app/
Repository: https://github.com/MehdiMarzban-eng/document-review-agent

Deployed and checked October 7, 2026. The public scripted review completed and the citation
inspector switched between source reports. All 14 automated tests passed locally and the
GitHub Actions Linux test workflow passed. No live Gemini or Ollama quality run established.

Later October 7 update: the user added a host Gemini key in Streamlit Secrets and authorized
live tests. Shared-key support is deployed; three Gemini development checks completed
successfully as documented in `docs/live-check-2026-10-07.md`. Eighteen local tests passed.
This supersedes the earlier absence of live Gemini examples, but is not a general benchmark.

Deploy on Streamlit Community Cloud using Python 3.12, branch `main`, entry point `cloud_app.py`.
The web UI defaults to Gemini; it requires a host or visitor API key and explicit consent. The scripted no-model walkthrough remains CLI-only. Optional Streamlit Secrets for shared Gemini access:

```toml
GEMINI_API_KEY = "your-key"
GEMINI_MODEL = "gemini-3.5-flash-lite"
```

Never commit a real `secrets.toml`. The model setting is optional. The host key stays server-side;
visitors must consent to sending their retrieved text. Shared access is bounded to 15 requests
per minute, 100 per rolling day and 30 per session. Counters reset on server restart and do not
guarantee zero charges; use provider quotas and the free tier as appropriate.

With a host key, demo access is the default. Visitors can choose **Review settings → Gemini API access → Use my own key**. Visitor access uses their provider quota/billing, bypasses the demo allowance and never falls back to the host key. Switching access clears findings, the entered key and consent. Clear documents and review also restores demo access. Without a host key, Gemini mode uses the visitor's own key and explicit consent. Cloud mode sends that key to
the app server for the provider request; it is never included in exported reviews or saved to disk.
Uploaded documents are processed on the hosting server and temporary files are removed after review.
Do not upload confidential material. There is no local Ollama option in the hosted app.

The hosted demo is a preview. Live model quality, held-out evaluation, and comparison against
the original fixed retrieval pipeline remain to be measured. Synthetic tests verify the
application, not factual reliability of model-generated reviews.

See https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy.

October 9 UI update: removed the sidebar and scripted web mode. Gemini defaults to an upload-first three-step flow; fictional reports are an optional explained example. Current-session clear control added. This does not make the preview suitable for private research. See docs/privacy-and-security.md.

October 9 API-access update: optional visitor-key selection alongside host-key default. All 20 automated tests passed, including credential selection, consent reset and demo-allowance isolation with mocked providers. No live provider requests were made for this update.
