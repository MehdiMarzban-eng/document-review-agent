# Local native edition — preview v0.3.8

Windows and Mac. Native Tk desktop controls using the bundled Python runtime. No embedded browser, Qt, Chromium, Streamlit or UI web server. Ollama supplies the local model API; it does not serve the user interface.

## Install

- **Windows x64:** close the earlier local edition, download the latest EXE, run it and choose Install. A desktop shortcut is created when permitted.
- **Mac Apple silicon/Intel:** open the DMG, drag the app to Applications, open it and choose Install. The correct architecture downloads automatically.

Installation prepares the app, Ollama and Qwen2.5 7B. The same window switches automatically to document review when ready. Future opens start the installed engine and show review directly. There is no Open app step. Existing engine/model files in the local edition's data folder are reused. Closing the window stops the model process started by this copy.

Add documents, check the files to review, enter a question and choose **Review documents**. New files are checked by default; adding files preserves existing choices. Every question uses the checked selection. Select a citation to inspect the original passage. **Save review** exports JSON with source excerpts. **Clear** removes the current selection and results from the app.

## Unreleased workflow prototype

The following paper-note workflow exists only on the development branch. It failed real-paper quality checks and is **not** included in v0.3.8 or the updater. See the [development report](paper-workflow-development-check-2026-10-10.md).

The first review prepares source-linked notes for every checked paper. Later questions reuse those notes and extracted text in memory. Changing the checked selection preserves notes; **Clear** or closing the app discards them. Notes are not saved automatically. First reviews take longer, especially without a dedicated GPU.

Overview and per-paper questions answer each selected paper separately, then connect their ideas. Focused questions search for requested facts. The model selects labeled original sentences; Python attaches their text and pages. Select a citation to inspect the quotation and full passage. Contradictions are withheld; uncertain model checks retain quoted drafts marked **Needs review**. Results are labeled **Draft review**. Missing excerpts, invalid drafts and uncertain judgments are different outcomes. These checks do not prove factual accuracy or full-document reading. See the [latest development results](source-selection-development-check-2026-10-10.md).

Preparation uses up to two model requests per uncached paper, plus one answer request per selected paper for overview/per-paper questions, and up to ten planning/synthesis/check requests (at most eight finding checks). A six-paper overview can use up to 28 requests initially, then 16 with cached notes. Large selections can exceed context or checking budgets; withheld or unavailable contributions remain partial results. No extra dependencies or model download are needed for this workflow.

**Not fully answered** shows unresolved clauses from your original question. Model-invented questions are replaced with your original request, preserving the partial status rather than hiding uncertainty. This checks wording origin, not whether the model correctly understood or answered the question.

## Updates (released edition)

Choose **Check for updates** when online. If a new version is available, choose **Install** or **Cancel**. Install downloads and verifies only the app/runtime package, then restarts the app. Save your review first. Existing Ollama/model files and the previous app version stay in place. The original shortcut opens the installed update.

There are no automatic update checks. The button contacts GitHub without sending documents, questions or findings. A failed check does not prevent offline use. Updates use HTTPS and SHA-256 checksums from the project release; this is not publisher code signing. A failed download leaves the current app selected; a failed process launch restores the previous selection. Runtime failures after a successful launch are not automatically detected.

The local edition has no fixed document-count, file-size, page-count or passage-count cap. Large batches still depend on available memory and processing time; scanned PDFs need OCR. Retrieval and model context/request budgets remain bounded. The hosted website retains its upload limits.

## Size and hardware

The desktop/runtime payload excludes all former browser-framework dependencies. Exact current payload sizes are shown in the GitHub release assets and the website's Setup details.

- Ollama: approximately **1.47 GB Windows / 167 MB Mac**.
- Qwen2.5 7B: approximately **4.7 GB** on either platform.
- Complete first setup: approximately **6.3 GB Windows / 5 GB Mac**, including the native app/runtime.
- Allow **14 GB free disk space** for installation and temporary extraction; **16 GB RAM** recommended. Model speed depends on hardware.

These are download sizes, not installed disk use. The installer is small because dependencies download after it runs. Existing prepared dependencies are reused. Sizes vary with release/architecture; the model tag is not immutable-pinned.

## Data boundaries

The native interface reads PDF/TXT/MD files directly on this computer. Review calls go only to the separate local Ollama process on `127.0.0.1:11435`. The launcher disables Ollama cloud features and inherited provider/tracing/proxy settings. No Gemini key or cloud review option is used by the native interface.

Setup downloads pinned/checksummed Python and Ollama releases from GitHub, and the model from Ollama's registry. Windows embeds the app payload checksum in its installer; Mac obtains its checksum sidecar over HTTPS from the same release. These checks do not replace publisher code signing.

Local processing is not a confidentiality guarantee. Device security, malicious documents, model errors, deletion and export handling still matter. Launchers are unsigned previews and may be blocked by OS or institutional policy; do not disable protections. Native-control tests and mocked-model reviews do not establish general model quality or security certification. Linux is deferred.

## Removal

Close the app, then remove its launcher/shortcut and per-user data folder if no longer needed:

- Windows: `%LOCALAPPDATA%\DocumentReviewLocal`
- Mac: `~/Library/Application Support/DocumentReviewLocal`

This removes the edition's engine/model files too. Exports saved elsewhere remain separate. Ordinary deletion is not secure erasure. Updates preserve existing models and documents.

## Sources

[Python/Tk](https://docs.python.org/3/library/tkinter.html), [python-build-standalone](https://github.com/astral-sh/python-build-standalone), [Ollama](https://github.com/ollama/ollama/blob/main/LICENSE), [Qwen2.5 7B](https://ollama.com/library/qwen2.5:7b). Runtime/dependency licenses remain in their distributions. Application provenance is recorded in ORIGIN.json and README. The old v0.2.x release used a browser wrapper; v0.3.0 replaces it with native controls.
