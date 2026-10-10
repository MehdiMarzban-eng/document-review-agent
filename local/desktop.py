"""Native Tk desktop controls; no browser, HTML or UI web server."""
import json
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


class ReviewWindow:
    def __init__(self, root, launcher, auto_start=True):
        self.root, self.launcher = root, launcher
        self.paths, self.citations = [], []
        self.corpus_cache = None
        self.result = None
        self.busy = False
        self.updating = False
        self.events = queue.Queue()
        root.title("Document Review Agent")
        root.geometry("1050x760")
        root.minsize(760, 580)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.setup_page = ttk.Frame(root, padding=32)
        self.setup_page.pack(fill="both", expand=True)
        ttk.Label(self.setup_page, text="Document Review Agent", font=("", 22, "bold")).pack(anchor="w")
        self.setup_status = tk.StringVar(value="Preparing local AI…")
        ttk.Label(self.setup_page, textvariable=self.setup_status, wraplength=680).pack(anchor="w", pady=20)
        self.progress = ttk.Progressbar(self.setup_page, maximum=100)
        self.progress.pack(fill="x")
        self.retry = ttk.Button(self.setup_page, text="Install local AI", command=self.begin_setup)
        self.retry.pack(anchor="w", pady=20)
        ttk.Label(self.setup_page, text="Ollama · Qwen2.5 7B · Processing stays on this computer.").pack(anchor="w")
        self.build_review()
        self.update_button = ttk.Button(root, text="Check for updates", command=self.check_updates)
        self.update_button.pack(side="bottom", anchor="e", padx=20, pady=8)
        if auto_start:
            root.after(0, self.begin_setup)
        self.poll_id = root.after(100, self.poll)

    def begin_setup(self):
        self.retry.pack_forget()
        self.launcher.update("working", "Preparing local AI…", 0)
        threading.Thread(target=self.launcher.setup, daemon=True).start()

    def build_review(self):
        self.review_page = ttk.Frame(self.root, padding=20)
        page = self.review_page
        ttk.Label(page, text="Document Review Agent", font=("", 20, "bold")).pack(anchor="w")
        ttk.Label(page, text="Local AI · Ollama / Qwen2.5 7B").pack(anchor="w", pady=(0, 12))
        bar = ttk.Frame(page)
        bar.pack(fill="x")
        self.add = ttk.Button(bar, text="Add documents", command=self.choose_documents)
        self.add.pack(side="left")
        self.clear = ttk.Button(bar, text="Clear", command=self.clear_review)
        self.clear.pack(side="left", padx=8)
        self.files = tk.StringVar(value="Choose PDF, TXT or MD files. No fixed document or file-size cap.")
        ttk.Label(page, textvariable=self.files, wraplength=950).pack(anchor="w", pady=8)
        scope = ttk.Frame(page)
        scope.pack(fill="x", pady=(0, 8))
        ttk.Label(scope, text="Review:").pack(side="left", padx=(0, 8))
        self.scope = ttk.Combobox(scope, values=["All documents"], state="readonly", width=70)
        self.scope.current(0)
        self.scope.pack(side="left", fill="x", expand=True)
        self.scope.bind("<<ComboboxSelected>>", lambda event: self.invalidate())
        ttk.Label(page, text="What would you like to find out?").pack(anchor="w")
        self.question = ScrolledText(page, height=3, wrap="word", font=("", 11))
        self.question.pack(fill="x", pady=6)
        self.question.bind("<<Modified>>", self.question_changed)
        actions = ttk.Frame(page)
        actions.pack(fill="x", pady=6)
        self.start = ttk.Button(actions, text="Review documents", command=self.start_review, state="disabled")
        self.start.pack(side="left")
        self.export = ttk.Button(actions, text="Save review", command=self.save_review, state="disabled")
        self.export.pack(side="left", padx=8)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(page, textvariable=self.status, wraplength=950).pack(anchor="w", pady=6)
        split = ttk.Panedwindow(page, orient="horizontal")
        split.pack(fill="both", expand=True)
        findings = ttk.Frame(split)
        ttk.Label(findings, text="Findings", font=("", 12, "bold")).pack(anchor="w")
        self.findings = ScrolledText(findings, wrap="word", width=48, state="disabled")
        self.findings.pack(fill="both", expand=True)
        split.add(findings, weight=1)
        evidence = ttk.Frame(split, padding=(12, 0, 0, 0))
        ttk.Label(evidence, text="Source evidence", font=("", 12, "bold")).pack(anchor="w")
        self.sources = tk.Listbox(evidence, height=5, exportselection=False)
        self.sources.pack(fill="x")
        self.sources.bind("<<ListboxSelect>>", self.inspect)
        self.passage = ScrolledText(evidence, wrap="word", width=42, state="disabled")
        self.passage.pack(fill="both", expand=True)
        split.add(evidence, weight=1)
        ttk.Label(page, text="Check cited passages before relying on findings. Saved reviews include excerpts.").pack(anchor="w", pady=(8, 0))

    @staticmethod
    def set_text(widget, value):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def question_changed(self, event=None):
        if self.question.edit_modified():
            self.question.edit_modified(False)
            self.invalidate()

    def invalidate(self):
        self.result, self.citations = None, []
        self.set_text(self.findings, "")
        self.set_text(self.passage, "")
        self.sources.delete(0, "end")
        self.export.configure(state="disabled")
        valid = self.paths and self.question.get("1.0", "end").strip() and not self.busy
        self.start.configure(state="normal" if valid else "disabled")

    def choose_documents(self):
        paths = filedialog.askopenfilenames(parent=self.root, title="Choose documents",
            filetypes=[("Documents", "*.pdf *.txt *.md")])
        if not paths:
            return
        self.paths = list(paths)
        self.corpus_cache = None
        self.scope.configure(values=["All documents"] + [Path(p).name for p in paths])
        self.scope.current(0)
        self.files.set(" · ".join(Path(p).name for p in paths))
        self.invalidate()

    def clear_review(self):
        self.paths = []
        self.corpus_cache = None
        self.scope.configure(values=["All documents"])
        self.scope.current(0)
        self.question.delete("1.0", "end")
        self.files.set("Choose PDF, TXT or MD files. No fixed document or file-size cap.")
        self.status.set("Ready")
        self.invalidate()

    def set_busy(self, busy):
        self.busy = busy
        self.update_button.configure(state="disabled" if busy else "normal")
        for widget in (self.add, self.clear, self.start):
            widget.configure(state="disabled" if busy else "normal")
        self.question.configure(state="disabled" if busy else "normal")
        self.scope.configure(state="disabled" if busy else "readonly")
        self.export.configure(state="normal" if self.result and not busy else "disabled")

    def start_review(self):
        question = self.question.get("1.0", "end").strip()
        if not self.paths or not question or len(question) > 2000:
            self.status.set("Choose documents and enter a question of up to 2,000 characters.")
            return
        self.invalidate()
        self.set_busy(True)
        self.status.set("Reviewing documents…")
        selected = self.scope.current()
        paths = [self.paths[selected - 1]] if selected > 0 else list(self.paths)
        def work():
            try:
                from agent import review
                from corpus import Corpus
                from providers import Ollama
                signature = tuple((p, Path(p).stat().st_size, Path(p).stat().st_mtime_ns) for p in paths)
                if not self.corpus_cache or self.corpus_cache[0] != signature:
                    self.corpus_cache = (signature, Corpus.from_paths(paths, max_documents=None,
                        max_file_bytes=None, max_pages=None, max_passages=None))
                result = review(self.corpus_cache[1], question, Ollama(self.launcher.MODEL, port=11435))
                self.events.put(("result", result))
            except Exception as error:
                self.events.put(("error", str(error)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        with self.launcher.LOCK:
            state = dict(self.launcher.STATE)
        self.setup_status.set(state["message"])
        self.progress["value"] = state["progress"]
        self.update_button.configure(state="disabled" if self.busy or self.updating or state["status"] == "working" else "normal")
        if state["status"] == "ready" and self.setup_page.winfo_manager():
            self.setup_page.pack_forget()
            self.review_page.pack(fill="both", expand=True)
        elif state["status"] == "error":
            self.retry.configure(text="Retry setup")
            self.retry.pack(anchor="w", pady=20)
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "result":
                    self.show_result(value)
                elif kind == "update_check":
                    self.offer_update(value)
                elif kind == "update_progress":
                    self.status.set(value)
                    self.setup_status.set(value)
                elif kind == "update_ready":
                    self.finish_update(value)
                    return
                elif kind == "update_error":
                    self.updating = False
                    self.update_button.configure(state="normal")
                    self.retry.configure(state="normal")
                    if self.review_page.winfo_manager():
                        self.set_busy(False)
                    messagebox.showinfo("App updates", value, parent=self.root)
                else:
                    self.set_busy(False)
                    self.status.set(value)
        except queue.Empty:
            pass
        self.poll_id = self.root.after(100, self.poll)

    def check_updates(self):
        if self.busy or self.updating or self.launcher.STATE["status"] == "working":
            return
        self.updating = True
        if self.review_page.winfo_manager():
            self.set_busy(True)
        self.update_button.configure(state="disabled")
        def work():
            try:
                import updates
                self.events.put(("update_check", updates.check(self.launcher.ROOT, self.launcher.PLATFORM)))
            except Exception as error:
                self.events.put(("update_error", str(error)))
        threading.Thread(target=work, daemon=True).start()

    def offer_update(self, info):
        self.updating = False
        if self.review_page.winfo_manager():
            self.set_busy(False)
        self.update_button.configure(state="normal")
        if not info:
            messagebox.showinfo("App updates", "You're up to date.", parent=self.root)
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Update available")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        ttk.Label(dialog, text=f"{info['version'].replace('local-preview-', '')} is available.", padding=20).pack()
        ttk.Label(dialog, text="The app will restart. Save your review first.").pack(padx=20)
        buttons = ttk.Frame(dialog, padding=20)
        buttons.pack()
        def install():
            dialog.destroy()
            self.install_update(info)
        ttk.Button(buttons, text="Install", command=install).pack(side="left", padx=6)
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="left", padx=6)
        dialog.grab_set()

    def install_update(self, info):
        self.updating = True
        self.set_busy(True)
        self.update_button.configure(state="disabled")
        self.retry.configure(state="disabled")
        def work():
            try:
                import updates
                destination = updates.prepare(info, self.launcher.DATA, self.launcher.PLATFORM,
                    self.launcher.extract, lambda text: self.events.put(("update_progress", text)), self.launcher.CANCELLED)
                self.events.put(("update_ready", destination))
            except Exception:
                self.events.put(("update_error", "Couldn't install the update. Your current app is unchanged. Try again when online."))
        threading.Thread(target=work, daemon=True).start()

    def finish_update(self, destination):
        import updates
        try:
            self.launcher.stop_children()
            updates.activate(self.launcher.DATA, self.launcher.ROOT, destination, self.launcher.PLATFORM)
        except Exception as error:
            self.events.put(("update_error", str(error)))
            self.retry.configure(state="normal")
            self.begin_setup()
            self.poll_id = self.root.after(100, self.poll)
            return
        self.close()

    def show_result(self, result):
        self.result = result
        self.set_busy(False)
        answer = result.get("answer")
        if not answer:
            self.status.set(result.get("clarification") or result.get("error") or
                            "Review budget reached. Try selecting one document or narrowing the question.")
            return
        self.status.set(answer["status"].replace("_", " ").capitalize())
        lines = []
        for number, claim in enumerate(answer["claims"], 1):
            lines.append(f"{number}. {claim['text']}")
            for citation in claim["evidence"]:
                self.citations.append(citation)
                label = f"[{len(self.citations)}] {citation['source_name']} · page {citation['pdf_page']}"
                self.sources.insert("end", label)
                lines.append(label)
            lines.append("")
        document_coverage = result.get("document_coverage", {})
        if document_coverage.get("requested_all"):
            lines += [f"Cited evidence from {document_coverage['cited']} of {document_coverage['total']} documents."]
            if document_coverage.get("not_cited"):
                lines += ["Not covered in this answer:", *document_coverage["not_cited"]]
        if answer["unanswered_parts"]:
            lines += ["Could not establish from the reviewed passages:", *answer["unanswered_parts"]]
        if result.get("coverage_check") == "unavailable":
            lines += ["", "Final answer check was unavailable. Check the cited passages."]
        self.set_text(self.findings, "\n".join(lines))
        if self.citations:
            self.sources.selection_set(0)
            self.inspect()

    def inspect(self, event=None):
        selected = self.sources.curselection()
        if selected and selected[0] < len(self.citations):
            self.set_text(self.passage, self.citations[selected[0]]["passage_text"])

    def save_review(self):
        if self.result:
            path = filedialog.asksaveasfilename(parent=self.root, title="Save review",
                initialfile="document-review.json", defaultextension=".json", filetypes=[("JSON", "*.json")])
            if path:
                try:
                    Path(path).write_text(json.dumps(self.result, ensure_ascii=False, indent=2), encoding="utf-8")
                except OSError as error:
                    messagebox.showerror("Could not save", str(error), parent=self.root)

    def close(self):
        self.launcher.CANCELLED.set()
        self.launcher.stop_children()
        self.root.after_cancel(self.poll_id)
        self.root.destroy()


def run_window(auto_start=None, launcher=None):
    if launcher is None:
        import launcher
    sys.path.insert(0, str(launcher.ROOT / "app"))
    root = tk.Tk()
    if auto_start is None:
        auto_start = launcher.STATE["installed"] or "--install" in sys.argv
    ReviewWindow(root, launcher, auto_start=auto_start)
    root.mainloop()
