"""Manual GitHub updates. Never receives document paths, questions or findings."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.request import Request, urlopen

REPOSITORY = "MehdiMarzban-eng/document-review-agent"
BASE = f"https://github.com/{REPOSITORY}/releases/download/"
API = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=30"
MAX_PACKAGE = 200 * 1024**2


class UpdateError(ValueError):
    pass


def version(value):
    match = re.fullmatch(r"local-preview-v(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise UpdateError("Unrecognized app version.")
    return tuple(map(int, match.groups()))


def current_version(root):
    return (Path(root) / "version.txt").read_text().strip()


def fetch(url, limit):
    request = Request(url, headers={"User-Agent": "DocumentReviewLocal-updater", "Accept": "application/vnd.github+json"})
    with urlopen(request, timeout=30) as response:
        content = response.read(limit + 1)
    if len(content) > limit:
        raise UpdateError("Update response exceeds the download limit.")
    return content


def check(root, platform):
    """Called only by the user pressing Check for updates."""
    try:
        installed = version(current_version(root))
        suffix = {"windows-x64": "zip", "mac-arm64": "tar.gz", "mac-x64": "tar.gz"}[platform]
        name = f"Document-Review-{platform}.{suffix}"
        releases = json.loads(fetch(API, 2 * 1024**2))
        candidates = []
        for release in releases:
            tag = release.get("tag_name", "")
            if release.get("draft") or not re.fullmatch(r"local-preview-v\d+\.\d+\.\d+", tag):
                continue
            assets = {a["name"]: a for a in release.get("assets", [])}
            if version(tag) <= installed or name not in assets or name + ".sha256" not in assets:
                continue
            asset, checksum = assets[name], assets[name + ".sha256"]
            if asset["browser_download_url"] != BASE + tag + "/" + name or checksum["browser_download_url"] != BASE + tag + "/" + name + ".sha256":
                raise UpdateError("Unexpected update download source.")
            if not 0 < asset["size"] <= MAX_PACKAGE:
                raise UpdateError("Update package exceeds the download limit.")
            candidates.append({"version": tag, "name": name, "url": asset["browser_download_url"],
                               "checksum_url": checksum["browser_download_url"], "size": asset["size"]})
        return max(candidates, key=lambda item: version(item["version"]), default=None)
    except UpdateError:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        raise UpdateError("Couldn't check for updates. Try again when online.") from None


def target(data, tag):
    version(tag)
    base = (Path(data) / "updates").resolve()
    destination = (base / tag / "Document Review Local").resolve()
    if not destination.is_relative_to(base):
        raise UpdateError("Invalid update folder.")
    return destination


def executable(root, platform):
    return root / "python" / ("pythonw.exe" if platform == "windows-x64" else "bin/python3")


def validate_package(root, tag, platform):
    if current_version(root) != tag or (root / "platform.txt").read_text().strip() != platform:
        raise UpdateError("Update version or platform does not match.")
    if not (root / "launcher.py").is_file() or not executable(root, platform).is_file():
        raise UpdateError("The update package is incomplete.")


def prepare(info, data, platform, extract, progress, cancelled):
    """Download/verify into a separate folder; do not change the running app."""
    tag, name = info["version"], info["name"]
    version(tag)
    expected_name = f"Document-Review-{platform}." + ("zip" if platform == "windows-x64" else "tar.gz")
    if name != expected_name or info["url"] != BASE + tag + "/" + name or info["checksum_url"] != info["url"] + ".sha256":
        raise UpdateError("Unexpected update download source.")
    destination = target(data, tag)
    destination.parent.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        validate_package(destination, tag, platform)
        return destination
    checksum = fetch(info["checksum_url"], 1024).decode("ascii").split()
    if len(checksum) != 2 or not re.fullmatch(r"[0-9a-f]{64}", checksum[0]) or checksum[1] != name:
        raise UpdateError("Invalid update checksum.")
    with tempfile.TemporaryDirectory(prefix="download-", dir=destination.parent.parent) as temporary:
        stage = Path(temporary)
        archive = stage / name
        digest, count = hashlib.sha256(), 0
        request = Request(info["url"], headers={"User-Agent": "DocumentReviewLocal-updater"})
        with urlopen(request, timeout=60) as response, archive.open("wb") as output:
            while chunk := response.read(1024**2):
                if cancelled.is_set():
                    raise UpdateError("Update cancelled.")
                count += len(chunk)
                if count > MAX_PACKAGE or count > info["size"]:
                    raise UpdateError("Unexpected update package size.")
                output.write(chunk)
                digest.update(chunk)
                progress(f"Downloading update… {int(count / info['size'] * 100)}%")
        if count != info["size"] or digest.hexdigest() != checksum[0]:
            raise UpdateError("Update verification failed. Your current app is unchanged.")
        progress("Installing update…")
        unpacked = stage / "unpacked"
        extract(archive, unpacked)
        package = unpacked / "Document Review Local"
        validate_package(package, tag, platform)
        if cancelled.is_set():
            raise UpdateError("Update cancelled.")
        destination.parent.mkdir(exist_ok=True)
        package.rename(destination)
    return destination


def launch(root, platform):
    return subprocess.Popen([str(executable(root, platform)), "-I", str(root / "launcher.py"), "--install"],
                            cwd=root, close_fds=True,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


def active_root(data, root, platform):
    """Local pointer only: opening the original shortcut uses the installed update."""
    pointer = Path(data) / "active-version.json"
    if not pointer.exists():
        return None
    try:
        tag = json.loads(pointer.read_text())["version"]
        if version(tag) <= version(current_version(root)):
            return None
        destination = target(data, tag)
        validate_package(destination, tag, platform)
        return destination
    except (OSError, ValueError, KeyError, TypeError):
        # A missing/broken update must not prevent the installed app opening.
        return None


def activate(data, root, destination, platform):
    tag = current_version(destination)
    validate_package(destination, tag, platform)
    pointer = Path(data) / "active-version.json"
    previous = pointer.read_bytes() if pointer.exists() else None
    pending = pointer.with_suffix(".tmp")
    pending.write_text(json.dumps({"version": tag, "previous_version": current_version(root)}))
    pending.replace(pointer)
    try:
        launch(destination, platform)
    except OSError:
        if previous is None:
            pointer.unlink(missing_ok=True)
        else:
            pending.write_bytes(previous)
            pending.replace(pointer)
        raise UpdateError("Couldn't restart the update. Your previous version is still installed.") from None
