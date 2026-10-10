"""Native controls and full review flow, mocked model; no network or model download."""
import json
import gc
import runpy
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
from unittest.mock import patch

package = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(package))
sys.path.insert(0, str(package / "app"))
import launcher
import desktop
from desktop import ReviewWindow
from demo import Walkthrough, DEMO_QUESTION


def wait(root, condition, timeout=30):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "Native UI timed out"
        root.update()
        time.sleep(.01)
    root.update()


# Exercise the installer's actual script entry, not just an imported launcher.
original_window, original_tk = desktop.run_window, tk.Tk
def script_window(*, launcher):
    assert launcher.DATA is not None and launcher.PLATFORM
    states = []
    def make_root():
        root = original_tk()
        mainloop = root.mainloop
        def check():
            states.append(launcher.STATE['status'])
            for callback in root.tk.call('after', 'info'):
                root.after_cancel(callback)
            root.destroy()
        def run_loop():
            # Schedule after window construction; Mac's first Tk window can take
            # longer than this timer and otherwise close before its startup task.
            root.after(500, check)
            mainloop()
        root.mainloop = run_loop
        return root
    with patch.object(launcher, 'setup', side_effect=lambda: launcher.update('ready', 'Ready', 100)), \
         patch.object(desktop.tk, 'Tk', side_effect=make_root):
        original_window(auto_start=True, launcher=launcher)
    assert states == ['ready'], states
with patch.object(desktop, 'run_window', side_effect=script_window):
    runpy.run_path(str(package / 'launcher.py'), run_name='__main__')
gc.collect()  # Release the first Tk interpreter on the GUI thread.


with tempfile.TemporaryDirectory() as data:
    launcher.DATA = Path(data)
    launcher.CANCELLED.clear()
    launcher.PLATFORM = (package / "platform.txt").read_text().strip()
    root = tk.Tk()
    with patch.object(launcher, "setup", side_effect=lambda: launcher.update("ready", "Ready", 100)):
        app = ReviewWindow(root, launcher, auto_start=True)
        wait(root, lambda: bool(app.review_page.winfo_manager()))
    assert not app.setup_page.winfo_manager(), "Setup did not automatically open review"
    app.set_documents([str(package / "app" / "samples" / name) for name in ("report-a.md", "report-b.md")])
    assert all(variable.get() for variable in app.document_vars.values())
    app.question.insert("1.0", DEMO_QUESTION)
    root.update()
    with patch("providers.Ollama", return_value=Walkthrough()):
        app.start_review()
        wait(root, lambda: app.result is not None)
    assert app.result["stop_reason"] == "finished", app.result
    assert "1.8" in app.findings.get("1.0", "end")
    assert app.citations and app.passage.get("1.0", "end").strip()
    app.sources.selection_clear(0, "end")
    app.sources.selection_set(1)
    app.inspect()
    assert app.passage.get("1.0", "end").strip() == app.citations[1]["passage_text"].strip()
    export = Path(data) / "review.json"
    with patch("desktop.filedialog.asksaveasfilename", return_value=str(export)):
        app.save_review()
    assert json.loads(export.read_text())["answer"]["claims"]
    # Repeated questions reuse extracted text instead of rereading every PDF.
    with patch("corpus.Corpus.from_paths") as extract, patch("providers.Ollama", return_value=Walkthrough()):
        app.start_review()
        wait(root, lambda: app.result is not None)
        extract.assert_not_called()
    # Changing the question discards stale output and prevents stale exports.
    app.question.insert("end", " changed")
    root.update()
    assert app.result is None and not app.citations
    app.corpus_cache = None  # Deliberately force extraction for failure recovery.
    with patch("corpus.Corpus.from_paths", side_effect=ValueError("Unreadable document")):
        app.start_review()
        wait(root, lambda: not app.busy)
    assert app.status.get() == "Unreadable document"
    app.clear_review()
    assert not app.paths and str(app.start["state"]) == "disabled" and app.corpus_cache is None
    sample = str(package / "app" / "samples" / "report-a.md")
    with patch("desktop.filedialog.askopenfilenames", return_value=[sample]):
        app.choose_documents()
    assert app.selected_paths() == [sample]
    app.document_checks[0].invoke()
    assert not app.selected_paths() and str(app.start['state']) == 'disabled'
    second = str(package / "app" / "samples" / "report-b.md")
    with patch("desktop.filedialog.askopenfilenames", return_value=[second]):
        app.choose_documents()
    assert app.paths == [sample, second] and app.selected_paths() == [second]
    app.question.insert('1.0', 'What is the main takeaway?')
    root.update()
    def capture_scope(corpus, *args, **kwargs):
        assert [doc['name'] for doc in corpus.manifest()] == ['report-b.md']
        assert corpus.paper_note_cache is app.paper_note_cache
        corpus.paper_note_cache['test-note'] = {'text': 'cached'}
        kwargs['progress']('Preparing test notes…')
        return {'answer': None, 'clarification': 'Subset verified'}
    with patch('agent.review', side_effect=capture_scope):
        app.start_review()
        assert all(str(checkbox['state']) == 'disabled' for checkbox in app.document_checks)
        wait(root, lambda: app.result is not None)
    app.select_documents(True)
    assert app.selected_paths() == [sample, second] and app.result is None
    assert 'test-note' in app.paper_note_cache
    app.select_documents(False)
    assert not app.selected_paths() and str(app.start['state']) == 'disabled'
    app.start_review()
    assert 'Check at least one' in app.status.get()
    app.clear_review()
    assert not app.paper_note_cache
    # Manual-only checks, offline/current feedback and explicit cancellation.
    import updates
    with patch.object(updates, 'check', return_value=None) as check, patch('desktop.messagebox.showinfo') as notice:
        app.check_updates()
        wait(root, lambda: not app.updating)
        check.assert_called_once()
        assert notice.call_args.args[1] == "You're up to date."
    with patch.object(updates, 'check', side_effect=updates.UpdateError('Offline')), patch('desktop.messagebox.showinfo') as notice:
        app.check_updates()
        wait(root, lambda: not app.updating)
        assert notice.call_args.args[1] == 'Offline'
    with patch.object(updates, 'prepare') as prepare:
        app.offer_update({'version': 'local-preview-v9.9.9'})
        dialog = next(child for child in root.winfo_children() if isinstance(child, tk.Toplevel))
        buttons = [child for frame in dialog.winfo_children() for child in frame.winfo_children()
                   if isinstance(child, __import__('tkinter.ttk', fromlist=['Button']).Button)]
        assert {button['text'] for button in buttons} == {'Install', 'Cancel'}
        next(button for button in buttons if button['text'] == 'Cancel').invoke()
        root.update()
        prepare.assert_not_called()
    with patch.object(updates, 'prepare', side_effect=updates.UpdateError('Download failed')), patch('desktop.messagebox.showinfo') as notice:
        app.install_update({'version': 'local-preview-v9.9.9'})
        wait(root, lambda: not app.updating)
        assert 'current app is unchanged' in notice.call_args.args[1]
    assert not any(name.startswith(("streamlit", "PySide6")) for name in sys.modules)
    (package.parent / "desktop-smoke.txt").write_text(
        "Native Tk setup -> review; cited findings, source selection, export, stale-clear and failure recovery passed. No web UI.\n")
    app.close()
print("Native desktop workflow passed; no external requests or model downloads.")
