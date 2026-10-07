"""Community Cloud entry point: omit unavailable local Ollama mode."""
import os
from pathlib import Path
import runpy

os.environ["DOCUMENT_REVIEW_HOSTED"] = "1"
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
