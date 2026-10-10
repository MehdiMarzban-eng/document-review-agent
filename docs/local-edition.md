# Local desktop edition - preview

The current download release targets Windows and Mac, with the app opening in its own window. Linux packaging is experimental and is not offered on the website. No separate Python installation or API key is needed.

## Install

- **Windows x64:** run the latest `Document-Review-Setup.exe`, then choose Install. Windows installer v0.2.3 fixes the path-length extraction error in the earlier preview. Close the old installer and download the replacement; Retry in the old version does not apply the fix. A desktop shortcut is created when permitted.
- **Mac (Apple silicon or Intel):** open `Document-Review-Setup.dmg`, drag the app to Applications, then open it and choose Install. The correct architecture downloads automatically. macOS 14 or newer is required by the desktop toolkit.
- **Linux x64 (experimental source support; no website download):** run `Document-Review-Setup.sh` in a terminal (`sh Document-Review-Setup.sh`). A graphical desktop with glibc 2.34+ and Qt/X11 dependencies is required. On Debian/Ubuntu, Qt/X11 and browser system libraries may need installation through the system package manager (see the package list in `.github/workflows/local-packages.yml`). The script does not request root access or change system packages.

The small launcher downloads the app/runtime first. The app then shows **Local setup - Download AI dependencies**. Choose **Download and install** to prepare Ollama and the preselected model. Existing model installations are reused. Closing the app window stops the local services.

The initial Windows installer is approximately 14 KB. This shifts the larger downloads into setup; it does not reduce the total runtime/model storage. Allow several GB of downloads, at least 14 GB free disk space for model preparation, and preferably 16 GB RAM. Speed varies.

Current complete setup downloads: **Windows approximately 6.6 GB; Mac approximately 5.5 GB**. The app payload (including Python, Qt and review libraries) is approximately **400 MB on Windows** or **610 MB on Mac**. Ollama adds **1.47 GB on Windows** or **167 MB on Mac**; the Qwen2.5 7B model adds approximately **4.7 GB** on either platform. Installed disk use and temporary extraction space are separate from download size.

### Approximate first-install downloads

Sizes below are decimal MB/GB, based on the pinned engine/runtime assets, desktop dependency wheels and the current model listing. App libraries are bundled together; these are component estimates rather than separate user downloads. Compression and architecture change the final payload size.

| Component | Windows x64 | Mac | Linux x64 |
| --- | ---: | ---: | ---: |
| Qwen2.5 7B model | 4.7 GB | 4.7 GB | 4.7 GB |
| Ollama engine | 1.47 GB | 167 MB | 1.44 GB |
| Qt desktop window and embedded browser | 260 MB | 465 MB | 265 MB |
| Private Python runtime | 22 MB | 25 MB | 35 MB |
| Review app and remaining libraries | 100–180 MB | 100–180 MB | 100–180 MB |
| Estimated total | 6.5–7 GB | 5.5–6 GB | 6.5–7 GB |

The old approximately 145 MB Windows ZIP excluded Ollama, model weights and the new Qt desktop window. The model is the largest component. Installed size is larger than compressed downloads, and setup also needs temporary extraction space. Existing installations reuse prepared components.

Sources: `local/downloads.json`, [Qt package metadata](https://pypi.org/project/PySide6/6.12.0/) and [Ollama model listing](https://ollama.com/library/qwen2.5:7b). The model tag can change; these figures are not a permanent size guarantee.

## Preview status

Launchers are unsigned; OS/institution policy can block them. Do not disable security protections. Mac notarization, Windows signing, Linux installation polish and representative-machine testing remain release work. Download availability does not establish confidential-use readiness.

The preceding v0.1.0 archive release remains available for reference. It opened a browser launcher; v0.2.2 replaces it with lightweight launchers and a dedicated Qt desktop window. See the GitHub prerelease for the current assets and exact build status.

## Data boundaries

The app and Ollama use loopback only. This launcher starts its own model process on port 11435, disables Ollama cloud features, uses a separate model directory, and forces local-only review with no Gemini option. The desktop view uses an in-memory web profile and blocks external web requests. This is an embedded web interface inside a native window; the review engine still runs locally.

Setup explicitly downloads pinned/checksummed runtime and engine releases from GitHub, plus `qwen2.5:7b` from Ollama's registry. The model tag is not an immutable pinned distribution. Windows embeds the payload checksum in the installer; Mac/Linux retrieve the checksum sidecar over HTTPS from the same release. None of these checks replaces publisher code signing.

No document is involved in setup. Review files and excerpts remain in local process memory, with temporary extraction files removed on normal exits. Exports contain source excerpts. Device security, disk encryption, malicious documents and deletion behavior still need assessment. Local processing is not a confidentiality guarantee. Verify offline operation and actual answer quality using fictional documents before sensitive work.

## Removal

Close the app first. Remove the downloaded launcher and its installed per-user data folder when no longer needed:

- Windows: `%LOCALAPPDATA%\DocumentReviewLocal`
- Mac: `~/Library/Application Support/DocumentReviewLocal`
- Linux: `$XDG_DATA_HOME/document-review-local`, or `~/.local/share/document-review-local` if unset.

Exports saved elsewhere remain separate. Ordinary deletion is not secure erasure. The installer does not delete existing models or documents during an update.

## Sources and licenses

Python: [python-build-standalone](https://github.com/astral-sh/python-build-standalone). Desktop window: [Qt for Python](https://doc.qt.io/qtforpython-6/), dynamically loaded under its applicable open-source licenses; license files remain in the dependency distribution. [Ollama](https://github.com/ollama/ollama/blob/main/LICENSE) and [Qwen2.5 7B](https://ollama.com/library/qwen2.5:7b) retain their licenses. Application reuse provenance is in ORIGIN.json and README. Packaging does not establish independent authorship or security certification.
