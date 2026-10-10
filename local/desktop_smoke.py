"""Exercise the packaged native window with no model or provider calls."""
import os
from pathlib import Path
import sys
import tempfile
import threading

package = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(package))
import launcher
from desktop import run_window

with tempfile.TemporaryDirectory() as data:
    launcher.DATA = Path(data)
    launcher.PLATFORM = (package / "platform.txt").read_text().strip()
    screenshot = package.parent / "desktop-smoke.png"
    os.environ["DOCUMENT_REVIEW_SMOKE_CAPTURE"] = str(screenshot)
    server = launcher.ThreadingHTTPServer(("127.0.0.1", 0), launcher.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        run_window(server)
        text = screenshot.with_suffix(".txt").read_text(encoding="utf-8")
        assert "Document Review Agent" in text and "Download AI dependencies" in text, text
        assert screenshot.stat().st_size > 1000
        print("Native desktop setup rendered successfully; no external model calls.")
    finally:
        server.shutdown()
        server.server_close()
        launcher.stop_children()
