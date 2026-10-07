# Hosting

Deploy on Streamlit Community Cloud using Python 3.12, branch `main`, entry point `cloud_app.py`.
No secrets or owner API key are needed. Visitors can use the scripted walkthrough without a key.
Gemini mode requires the visitor's own key and explicit consent. Cloud mode sends that key to
the app server for the provider request; it is never included in exported reviews or saved to disk.
Uploaded documents are processed on the hosting server and temporary files are removed after review.
Do not upload confidential material. There is no local Ollama option in the hosted app.

The hosted demo is a preview. Live model quality, held-out evaluation, and comparison against
the original fixed retrieval pipeline remain to be measured. Synthetic tests verify the
application, not factual reliability of model-generated reviews.

See https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy.
