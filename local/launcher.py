"""Local model setup for the native desktop. Uses private bundled Python.

No documents are accepted here. Downloads follow the user's installer consent.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tarfile
import threading
import time
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
MODEL = "qwen2.5:7b"
STATE = {"status": "welcome", "message": "Ready", "progress": 0, "installed": False}
CHILDREN = []
LOCK = threading.Lock()
CANCELLED = threading.Event()
DATA = None
PLATFORM = None


def update(status, message, progress=0):
    if CANCELLED.is_set():
        raise InterruptedError("Setup cancelled")
    with LOCK:
        STATE.update(status=status, message=message, progress=progress)


def private_environment(data):
    env = os.environ.copy()
    # Avoid inheriting unrelated model credentials, provider choice or proxies.
    for key in list(env):
        if key.upper().endswith("_PROXY") or key.startswith(("GEMINI_", "GOOGLE_", "OLLAMA_", "DOCUMENT_REVIEW_", "LANGCHAIN_", "LANGSMITH_")):
            env.pop(key, None)
    env.update(OLLAMA_HOST="127.0.0.1:11435", OLLAMA_NO_CLOUD="1",
               OLLAMA_MODELS=str(data / "models"), OLLAMA_DEBUG="0",
               OLLAMA_CONTEXT_LENGTH="16384", DOCUMENT_REVIEW_LOCAL_ONLY="1",
               STREAMLIT_BROWSER_GATHER_USAGE_STATS="false",
               LANGCHAIN_TRACING_V2="false", LANGSMITH_TRACING="false")
    return env


def download(asset, destination):
    request = Request(asset["browser_download_url"], headers={"User-Agent": "DocumentReviewLocal/0.1"})
    digest = hashlib.sha256()
    done = 0
    with urlopen(request, timeout=120) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            update("working", f"Downloading the local AI engine: {done // 1048576} MB of {asset['size'] // 1048576} MB", min(45, int(done / asset["size"] * 45)))
    if "sha256:" + digest.hexdigest() != asset["digest"]:
        destination.unlink(missing_ok=True)
        raise ValueError("The download did not pass its integrity check. Please retry.")


def extract(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as source:
            for info in source.infolist():
                target = (destination / info.filename).resolve()
                if not target.is_relative_to(destination.resolve()):
                    raise ValueError("Unsafe archive path")
            source.extractall(destination)
    else:
        if archive.name.endswith(".tar.zst"):
            import zstandard
            unpacked = archive.with_suffix("")
            with archive.open("rb") as source, unpacked.open("wb") as output:
                zstandard.ZstdDecompressor().copy_stream(source, output)
        else:
            unpacked = archive
        try:
            with tarfile.open(unpacked) as source:
                source.extractall(destination, filter="data")
        finally:
            if unpacked != archive:
                unpacked.unlink(missing_ok=True)


def engine_path():
    name = "ollama.exe" if PLATFORM == "windows-x64" else "ollama"
    paths = list((DATA / "engine").rglob(name))
    if len(paths) != 1:
        raise ValueError("The local AI engine is incomplete. Run setup again.")
    return paths[0]


def read_json(url):
    with urlopen(url, timeout=2) as response:
        return json.load(response)


def start_engine(env):
    # Never attach to an unrelated existing server, even if it speaks Ollama.
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 11435)) == 0:
            raise ValueError("Another local edition is already open. Close it before opening this copy.")
    with LOCK:
        if CANCELLED.is_set():
            raise InterruptedError("Setup cancelled")
        process = subprocess.Popen([str(engine_path()), "serve"], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        CHILDREN.append(process)
    for _ in range(120):
        if CANCELLED.is_set():
            raise InterruptedError("Setup cancelled")
        if process.poll() is not None:
            raise ValueError("The local AI engine could not start on this computer.")
        try:
            read_json("http://127.0.0.1:11435/api/version")
            return
        except (OSError, ValueError):
            time.sleep(0.5)
    raise ValueError("The local AI engine took too long to start.")


def pull_model():
    request = Request("http://127.0.0.1:11435/api/pull",
                      data=json.dumps({"model": MODEL, "stream": True}).encode(),
                      headers={"Content-Type": "application/json"})
    success = False
    with urlopen(request, timeout=300) as response:
        for line in response:
            item = json.loads(line)
            if item.get("error"):
                raise ValueError("The model download failed. Check your connection and try again.")
            total, done = item.get("total", 0), item.get("completed", 0)
            percent = int(done / total * 100) if total else 0
            update("working", f"Preparing the AI model: {percent}%" if total else "Preparing the AI model…", 50 + int(percent * .45))
            success = item.get("status") == "success"
    if not success:
        raise ValueError("The model download did not finish. Please retry.")


def stop_children():
    with LOCK:
        children = list(reversed(CHILDREN))
        CHILDREN.clear()
    for process in children:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


def setup():
    try:
        update("working", "Checking your computer…", 0)
        DATA.mkdir(parents=True, exist_ok=True)
        ready = DATA / "setup-complete.json"
        engine_ready = DATA / "engine-complete.json"
        config = json.loads((ROOT / "downloads.json").read_text())[PLATFORM]["ollama"]
        try:
            engine_path()
            has_engine = ready.exists() or (engine_ready.exists() and json.loads(engine_ready.read_text())["digest"] == config["digest"])
        except (ValueError, OSError, KeyError):
            has_engine = False
        if not has_engine:
            if shutil.disk_usage(DATA).free < 14 * 1024**3:
                raise ValueError("Setup needs at least 14 GB of free disk space for downloads, extraction and the model.")
            archive = DATA / config["name"]
            download(config, archive)
            update("working", "Unpacking the local AI engine…", 46)
            extract(archive, DATA / "engine")
            archive.unlink(missing_ok=True)
            engine_ready.write_text(json.dumps({"digest": config["digest"]}))
        env = private_environment(DATA)
        start_engine(env)
        if not ready.exists():
            pull_model()
            ready.write_text(json.dumps({"model": MODEL, "engine_digest": config["digest"]}))
        else:
            installed = read_json("http://127.0.0.1:11435/api/tags")
            if MODEL not in {item["name"] for item in installed.get("models", [])}:
                pull_model()
        update("ready", "Ready", 100)
    except Exception as error:
        stop_children()
        # Local filesystem paths and tracebacks are never sent to remote telemetry.
        if not CANCELLED.is_set():
            update("error", str(error), 0)


def main():
    global DATA, PLATFORM
    PLATFORM = (ROOT / "platform.txt").read_text().strip()
    if os.name == "nt":
        DATA = Path(os.environ["LOCALAPPDATA"]) / "DocumentReviewLocal"
    elif sys.platform == "darwin":
        DATA = Path.home() / "Library" / "Application Support" / "DocumentReviewLocal"
    else:
        DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "document-review-local"
    if (DATA / "setup-complete.json").exists():
        STATE.update(installed=True)
    try:
        from desktop import run_window
        run_window()
    finally:
        CANCELLED.set()
        stop_children()


if __name__ == "__main__":
    main()
