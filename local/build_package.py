"""Build a self-contained Python/app package on the target OS (CI only)."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(platform):
    asset = json.loads((ROOT / "local" / "downloads.json").read_text())[platform]["python"]
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    folder = out / "Document Review Local"
    folder.mkdir()
    archive = out / "python.tar.gz"
    urllib.request.urlretrieve(asset["browser_download_url"], archive)
    if "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest() != asset["digest"]:
        raise ValueError("Python runtime checksum mismatch")
    with tarfile.open(archive) as runtime:
        runtime.extractall(folder, filter="data")
    executable = folder / "python" / ("python.exe" if platform == "windows-x64" else "bin/python3")
    subprocess.run([str(executable), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(ROOT / "requirements.txt"), "zstandard==0.25.0"], check=True)
    app = folder / "app"
    app.mkdir()
    for source in ROOT.glob("*.py"):
        shutil.copy2(source, app / source.name)
    shutil.copytree(ROOT / "samples", app / "samples")
    shutil.copytree(ROOT / "docs", app / "docs")
    for name in ("launcher.py", "setup.html", "downloads.json"):
        shutil.copy2(ROOT / "local" / name, folder / name)
    (folder / "platform.txt").write_text(platform)
    (folder / "START HERE.txt").write_text(
        "DOCUMENT REVIEW LOCAL - PREVIEW\n\n"
        "1. Extract this entire download into a folder on your computer.\n"
        "2. Open Start Document Review.cmd (Windows) or Start Document Review.command (Mac) or Start Document Review.sh (Linux).\n"
        "3. Your browser opens a guided setup. Choose Set up on this computer.\n\n"
        "No separate Python or Ollama installation is needed. First setup downloads Ollama and the model.\n"
        "Keep the launcher page open while reviewing; use Close local edition to stop it.\n"
        "This preview is unsigned. Your OS or institution may block it. Do not disable security protections.\n"
        "Use fictional documents until this setup has been verified for your environment.\n"
        "Model/data downloads are in DocumentReviewLocal in your per-user application data folder.\n"
        "See app/docs/local-edition.md for limitations, removal and source/license details.\n", encoding="utf-8")
    if platform == "windows-x64":
        (folder / "Start Document Review.cmd").write_text('@echo off\r\nstart "" /b "%~dp0python\\pythonw.exe" "%~dp0launcher.py"\r\n', encoding="ascii")
    else:
        name = "Start Document Review.command" if platform.startswith("mac") else "Start Document Review.sh"
        starter = folder / name
        starter.write_text('#!/bin/sh\ncd "$(dirname "$0")" || exit 1\nexec ./python/bin/python3 ./launcher.py\n')
        starter.chmod(0o755)
    # Verify the actual bundled runtime and dependencies, not just the build host.
    subprocess.run([str(executable), "-c", "import streamlit, langgraph, pypdf, zstandard; print('Bundled runtime imports passed')"], check=True)
    subprocess.run([str(executable), "-m", "pip", "check"], check=True)
    # Runtime licenses remain in the bundle; archive also includes project provenance.
    shutil.copy2(ROOT / "ORIGIN.json", app / "ORIGIN.json")
    if platform == "windows-x64":
        target = out / f"Document-Review-{platform}.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as package:
            for path in folder.rglob("*"):
                if path.is_file():
                    package.write(path, path.relative_to(out))
    else:
        target = out / f"Document-Review-{platform}.tar.gz"
        with tarfile.open(target, "w:gz") as package:
            package.add(folder, arcname=folder.name)
    (out / (target.name + ".sha256")).write_text(hashlib.sha256(target.read_bytes()).hexdigest() + "  " + target.name + "\n")
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("platform", choices=["windows-x64", "mac-arm64", "mac-x64", "linux-x64"])
    build(parser.parse_args().platform)
