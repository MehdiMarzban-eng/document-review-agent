# Hosting

Live preview: https://document-review-agent.streamlit.app/
Repository: https://github.com/MehdiMarzban-eng/document-review-agent

Deployed and checked October 7, 2026. The public scripted review completed and the citation
inspector switched between source reports. All 14 automated tests passed locally and the
GitHub Actions Linux test workflow passed. No live Gemini or Ollama quality run established.

Deploy on Streamlit Community Cloud using Python 3.12, branch `main`, entry point `cloud_app.py`.
No key is needed for the scripted walkthrough. Optional Streamlit Secrets for shared Gemini access:

```toml
GEMINI_API_KEY = "your-key"
GEMINI_MODEL = "gemini-3.5-flash-lite"
```

Never commit a real `secrets.toml`. The model setting is optional. The host key stays server-side;
visitors must consent to sending their retrieved text. Shared access is bounded to 15 requests
per minute, 100 per rolling day and 30 per session. Counters reset on server restart and do not
guarantee zero charges; use provider quotas and the free tier as appropriate.

Without a host key, Gemini mode uses the visitor's own key and explicit consent. Cloud mode sends that key to
the app server for the provider request; it is never included in exported reviews or saved to disk.
Uploaded documents are processed on the hosting server and temporary files are removed after review.
Do not upload confidential material. There is no local Ollama option in the hosted app.

The hosted demo is a preview. Live model quality, held-out evaluation, and comparison against
the original fixed retrieval pipeline remain to be measured. Synthetic tests verify the
application, not factual reliability of model-generated reviews.

See https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy.
