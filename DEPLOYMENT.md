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

October 9 local-edition preview: `local/launcher.py` supplies a loopback setup page, explicit first-run downloads with engine checksum validation, progress, a private model directory, cloud-disabled Ollama on port 11435, forced local-only app mode and a stop control. `local-packages.yml` builds Windows x64, Mac Apple silicon/Intel and Linux x64 packages with private Python runtimes; tagged builds publish prerelease assets. Twenty-five local tests passed. This does not establish successful model setup/inference or signed-install readiness. See docs/local-edition.md.

`local-preview-v0.1.0` was published successfully: all four package jobs passed tests, runtime imports and dependency checks. Public release assets and SHA-256 sidecars were verified via GitHub release metadata. The hosted app links directly to these preview downloads. First-run model installation, real local inference and offline end-to-end review remain unverified; the website labels the packages as unsigned previews.

Desktop preview update: Windows and both Mac architecture package jobs passed all 26 tests, bundled runtime/dependency checks and native Qt window smoke checks. Small EXE/DMG bootstrappers replace primary archive downloads; the app opens in a separate window with concise setup text. Linux desktop dependency failures prompted the user's decision to defer Linux and remove it from current release builds and website links. Model installation, real local inference, offline review and confidential-use readiness remain unverified.

Public local-preview-v0.2.2 assets verified through release metadata: Windows EXE14,848 bytes; Mac DMG71,943 bytes; internal Windows payload399,318,254 bytes, Mac ARM604,443,729 bytes and Mac Intel608,306,517 bytes. Website primary downloads are EXE/DMG; archive payloads remain release assets for installers. Linux is not published in this release.

Windows installer v0.2.3 fixes legacy .NET path limits using .NET4.8 path handling, guarded extended paths and a shorter install directory. All28 Windows tests passed, including extraction beyond260 characters and traversal/alternate-stream rejection. The full checksum-verified399MB v0.2.2 payload extracted successfully with the new installer, and its native setup window rendered in CI. The hotfix reuses that payload; model installation/inference remains unverified. Website and installer disclose Windows~6.6GB/Mac~5.5GB setup download totals, distinguish14GB free setup space, and identify Ollama/Qwen2.5 7B.

October 10 native replacement: v0.3.1 replaces the Qt/Streamlit local wrapper with Tk controls and automatic setup-to-review transition. Local payloads are approximately39MB Windows/43MB Mac before Ollama/model downloads. Existing engine/model reuse is covered by regression checks. All28 Windows tests pass; v0.3.0 native GUI smoke passed on Windows and both Mac architectures. Real existing Qwen2.5:7b tests completed a cited two-report comparison and identified the corrected fictional PDF value0.71m on page3. Schema guidance and an8192-token local context address observed response issues. These limited fixtures do not establish general answer accuracy, fresh-machine installation or confidentiality guarantees.

Native release local-preview-v0.3.1 published successfully (workflow38032074478): Windows, Mac ARM and Mac Intel package tests and native GUI review/export/source/error-recovery smoke all passed. Verified public assets: Windows payload39,353,041bytes, Mac ARM43,170,842bytes, Mac Intel43,101,301bytes; EXE16,896bytes, DMG71,951bytes. Website download links/size breakdown updated by339e6cc. Additional own-window test used the actual local Qwen provider and displayed the comparison and source inspector successfully. First-time full installation on a fresh machine remains unverified.

October10 startup hotfix v0.3.2: user encountered NoneType.mkdir before setup. Script entry initialized __main__, but desktop.run_window imported a separate launcher module with DATA=None. The entry now passes its initialized runtime explicitly. Added script-entry regression and packaged native GUI entry smoke, with downloads mocked. All29 Windows regression tests and bundled native smoke passed. Earlier imported-launcher smoke did not exercise this path.

Startup hotfix local-preview-v0.3.3 published: workflow38032588039 passed all three platform package jobs,29 unit tests (Windows-specific cases skipped on Mac), and actual script-entry/native workflow smoke. v0.3.2 was not published because a smoke-test timer fired before Mac window construction completed; v0.3.3 schedules the check after construction. Public EXE/DMG and39MB/43MB payload assets verified. Existing engine/model data stays separate and is reused; no user installation was modified during this repair.

October10 manual updater (v0.3.4): Check for updates is the only update-network trigger. GitHub version discovery requires matching platform payload/checksum assets; native prompt offers Install/Cancel. Installs verify SHA-256 and size/source bounds, extract to a separate version directory, preserve engine/models/current version, and restart. A local active-version pointer makes existing shortcuts use updates. Failed download leaves current selection; failed process spawn restores the old pointer. No automatic runtime-crash rollback or publisher signing claimed. Local edition removes fixed byte/page/passage limits; hosted defaults and bounded model context/requests remain. All33 Windows unit tests pass; native smoke covers manual current/offline feedback, Cancel and failed-download recovery.

Published local-preview-v0.3.4, workflow38033806077: all Windows/Mac ARM/Mac Intel builds, unit checks and native manual-updater smoke passed. Live GitHub discovery downloaded and checksum-verified the real Windows payload into a temporary folder; bundled imports, staged activation pointer, model-marker preservation and up-to-date result passed. Process restart was mocked in this live-download check; user installation was untouched. An actual synthetic21MB/301-page PDF indexed and retrieved successfully with local limits disabled. Website now links v0.3.4 and states No PDF file-size limit in the local section.

Published local-preview-v0.3.5 (commit623851b; package workflow38034551400): Windows, Mac ARM and Mac Intel package builds, unit checks and native smoke checks passed. The native UI/core path has no fixed document-count cap; hosted web app limits remain. README distinguishes the installed native app from the browser-based developer Streamlit app. Windows and Mac website links target v0.3.5. Two legacy manual publisher workflows also ran on the tag and failed because they still reference v0.2.2; the tag-based package-and-release workflow succeeded and published all six platform assets.
