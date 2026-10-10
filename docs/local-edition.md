# Local desktop edition - preview

The app opens in its own window on Windows, Mac and Linux. No separate Python installation or API key is needed.

## Install

- **Windows x64:** run `Document-Review-Setup.exe`, then choose Install. A desktop shortcut is created when permitted.
- **Mac (Apple silicon or Intel):** open `Document-Review-Setup.dmg`, drag the app to Applications, then open it and choose Install. The correct architecture downloads automatically. macOS 14 or newer is required by the desktop toolkit.
- **Linux x64:** run `Document-Review-Setup.sh` in a terminal (`sh Document-Review-Setup.sh`). A graphical desktop with glibc 2.34+ and Qt/X11 dependencies is required. On Debian/Ubuntu, missing `libxcb-cursor0`, `libxkbcommon-x11-0` or `libegl1` must be installed through the system package manager. The script does not request root access or change system packages.

The small launcher downloads the app/runtime first. The app then shows **Local setup - Download AI dependencies**. Choose **Download and install** to prepare Ollama and the preselected model. Existing model installations are reused. Closing the app window stops the local services.

The initial Windows installer is approximately 14 KB. This shifts the larger downloads into setup; it does not reduce the total runtime/model storage. Allow several GB of downloads, at least 14 GB free disk space for model preparation, and preferably 16 GB RAM. Speed varies.

## Preview status

Launchers are unsigned; OS/institution policy can block them. Do not disable security protections. Mac notarization, Windows signing, Linux installation polish and representative-machine testing remain release work. Download availability does not establish confidential-use readiness.

The preceding v0.1.0 archive release remains available for reference. It opened a browser launcher; v0.2.0 replaces it with lightweight launchers and a dedicated Qt desktop window. See the GitHub prerelease for the current assets and exact build status.

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
