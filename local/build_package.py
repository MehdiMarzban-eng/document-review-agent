"""Build a self-contained Python/app package on the target OS (CI only)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(platform):
    asset = json.loads((ROOT / "local" / "downloads.json").read_text())[platform]["python"]
    out = Path(os.environ.get("DOCUMENT_REVIEW_DIST", ROOT / "dist"))
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
    subprocess.run([str(executable), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(ROOT / "local" / "requirements.txt")], check=True)
    app = folder / "app"
    app.mkdir()
    for name in ("agent.py", "corpus.py", "providers.py", "evidence_answers.py", "evidence_search.py", "demo.py", "question_understanding.py", "paper_notes.py", "paper_review.py", "source_support.py"):
        source = ROOT / name
        shutil.copy2(source, app / source.name)
    shutil.copytree(ROOT / "samples", app / "samples")
    shutil.copytree(ROOT / "docs", app / "docs")
    for name in ("launcher.py", "desktop.py", "updates.py", "downloads.json"):
        shutil.copy2(ROOT / "local" / name, folder / name)
    (folder / "platform.txt").write_text(platform)
    version = os.environ.get("GITHUB_REF_NAME", "local-preview-v0.3.5")
    if not version.startswith("local-preview-"):
        version = "local-preview-v0.3.5"
    (folder / "version.txt").write_text(version)
    (folder / "START HERE.txt").write_text(
        "DOCUMENT REVIEW LOCAL - PREVIEW\n\n"
        "1. Extract this entire download into a folder on your computer.\n"
        "2. Open Start Document Review.cmd (Windows) or Start Document Review.command (Mac) or Start Document Review.sh (Linux).\n"
        "3. The app opens a guided setup. Choose Download and install.\n\n"
        "No separate Python or Ollama installation is needed. First setup downloads Ollama and the model.\n"
        "Close the app window to stop its local services.\n"
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
    subprocess.run([str(executable), "-c", "import tkinter, langgraph, pypdf; import importlib.util; assert importlib.util.find_spec('streamlit') is None; assert importlib.util.find_spec('PySide6') is None; print('Native desktop/runtime imports passed; no browser framework')"], check=True)
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
    build_installer(platform, out, target)
    print(target)


def build_installer(platform, out, payload):
    version = os.environ.get("GITHUB_REF_NAME", "local-preview-v0.3.5")
    if not version.startswith("local-preview-"):
        version = "local-preview-v0.3.5"
    if platform == "windows-x64":
        manifest = out / "install.json"
        manifest.write_text(json.dumps({"version": version,
            "url": f"https://github.com/MehdiMarzban-eng/document-review-agent/releases/download/{version}/{payload.name}",
            "sha256": hashlib.sha256(payload.read_bytes()).hexdigest()}))
        compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe"
        references = ["System.Windows.Forms", "System.Drawing", "System.IO.Compression", "System.IO.Compression.FileSystem", "System.Web.Extensions", "Microsoft.CSharp"]
        subprocess.run([str(compiler), "/nologo", "/target:winexe",
            f"/out:{out / 'Document-Review-Setup.exe'}", f"/resource:{manifest},install.json",
            *[f"/reference:{name}.dll" for name in references], str(ROOT / "local" / "windows_setup.cs")], check=True)
    elif platform in ("mac-arm64", "linux-x64"):
        script = (ROOT / "local" / "bootstrap.sh").read_text().replace("__VERSION__", version)
        if platform == "linux-x64":
            starter = out / "Document-Review-Setup.sh"
            starter.write_text(script)
            starter.chmod(0o755)
        else:
            stage = out / "mac-installer"
            stage.mkdir()
            application = stage / "Document Review Agent.app"
            applescript = out / "setup.applescript"
            applescript.write_text('''on run
    display dialog "Download app dependencies?" with title "Document Review Agent" buttons {"Cancel", "Install"} default button "Install"
    set progress total steps to -1
    set progress description to "Downloading app dependencies..."
    set scriptFile to POSIX path of (path to resource "bootstrap.sh")
    try
        do shell script "DOCUMENT_REVIEW_DETACH=1 /bin/sh " & quoted form of scriptFile
    on error messageText
        display dialog messageText with title "Setup failed" buttons {"OK"} default button "OK"
    end try
end run
''')
            subprocess.run(["osacompile", "-o", str(application), str(applescript)], check=True)
            (application / "Contents" / "Resources" / "bootstrap.sh").write_text(script)
            (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
            subprocess.run(["hdiutil", "create", "-volname", "Document Review Agent", "-srcfolder", str(stage), "-format", "UDZO", str(out / "Document-Review-Setup.dmg")], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("platform", choices=["windows-x64", "mac-arm64", "mac-x64", "linux-x64"])
    build(parser.parse_args().platform)
