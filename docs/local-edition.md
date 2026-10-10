# Local edition — preview

The local edition is intended to keep the familiar browser interface while removing Python installation, API keys and model-setting choices. Windows x64, Mac Apple silicon/Intel and Linux x64 builds are prepared by the `Local edition packages` workflow. ARM Windows/Linux builds are not included.

[Download preview packages](https://github.com/MehdiMarzban-eng/document-review-agent/releases/tag/local-preview-v0.1.0). Published October 9, 2026: all four platform jobs passed the 25-test suite, bundled-runtime imports and dependency checks. The Windows setup welcome/close screens were browser-checked locally. No full Ollama/model installation or real inference was run in this release check; Mac/Linux user installation and offline end-to-end behavior remain unverified.

## Using the download

1. Download the package for your operating system and extract the entire archive.
2. Open **Start Document Review** in the extracted folder. The extension is `.cmd` on Windows, `.command` on Mac and `.sh` on Linux. Linux file-manager behavior varies; shell-script launch permissions may require assistance.
3. Your browser opens a guided setup. Approve the first-time engine/model download and wait for the progress screen to finish. Then choose **Open Document Review**.

Subsequent launches reuse the installed model and can run offline. Keep the launcher page open during reviews; choose **Close local edition** when finished. Closing a browser tab alone does not stop the services.

The package includes a private Python runtime and app dependencies. First setup downloads a checksum-pinned Ollama release from its official GitHub repository and the preselected `qwen2.5:7b` model from Ollama's registry. The engine is roughly 0.2–1.5 GB depending on the platform; the model is approximately 4.7 GB. Allow at least 14 GB free disk space during setup; 16 GB RAM is recommended as a starting point, not a performance guarantee. CPU operation can be slow. Internet is required for first setup; no document upload is part of setup. Model quality has not yet been validated for this edition.

## Preview limitations

These downloads are **unsigned previews**, not polished signed installers. OS security controls or institutional policy may block them; do not disable protections. Mac notarization, Windows signing, desktop shortcuts, OS-specific installation assistance and end-to-end testing on representative machines remain release work. Do not describe these builds as a one-click production installation or as verified safe for confidential research. Start with fictional documents.

## Data and network boundaries

The launcher starts its own Ollama process on loopback port 11435, with cloud features disabled and a separate model directory. It refuses an occupied port rather than connecting to an unknown existing model server. The review app binds to loopback, disables Streamlit usage telemetry and forces local-only mode: there is no Gemini selector or cloud fallback. The current browser interface keeps temporary uploads/reviews in local process memory and creates temporary extraction files. Citations/exports contain source excerpts. Operating-system accounts, disk encryption, dependencies and malicious documents still require assessment. Local operation alone is not a confidentiality guarantee.

The setup page has no document-upload facility. Setup contacts GitHub and Ollama's registry only after an explicit setup action. A fresh model tag is retrieved from the registry during first setup and then reused; this is not a fully pinned/reproducible model distribution. Verify offline behavior and model quality before relying on a deployment. The full engine and model are not embedded in the initial download.

## Removing the local edition

Close the local edition first. Remove the extracted package when no longer needed. Downloaded engine/models remain in the per-user data folder until you remove it yourself:

- Windows: `%LOCALAPPDATA%\DocumentReviewLocal`
- Mac: `~/Library/Application Support/DocumentReviewLocal`
- Linux: `$XDG_DATA_HOME/document-review-local`, or `~/.local/share/document-review-local` if unset.

This is ordinary file deletion, not secure erasure. Exports saved elsewhere remain separate.

## Sources and licenses

Python runtime: [Astral python-build-standalone](https://github.com/astral-sh/python-build-standalone); runtime license files remain in the distribution. Dependencies retain installed license metadata. Ollama binaries retain their bundled license files; [Ollama license](https://github.com/ollama/ollama/blob/main/LICENSE). The downloaded [Qwen2.5 7B model](https://ollama.com/library/qwen2.5:7b) uses Apache 2.0; this differs from the 3B and 72B variants. Application reuse provenance is in `ORIGIN.json` and the project README. Packaging does not establish independent authorship or audit the bundled components.
