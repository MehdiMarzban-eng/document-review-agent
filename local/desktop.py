"""Dedicated desktop window; no external browser or persistent web profile."""
import os
from pathlib import Path
from urllib.parse import urlparse


def is_local_url(url, ports):
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "ws") and parsed.hostname == "127.0.0.1" and parsed.port in ports
    except ValueError:
        return False


def run_window(server):
    import launcher
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineUrlRequestInterceptor
    from PySide6.QtWebEngineWidgets import QWebEngineView

    class LocalRequests(QWebEngineUrlRequestInterceptor):
        def interceptRequest(self, info):
            ports = {server.server_port}
            if launcher.APP_URL:
                ports.add(urlparse(launcher.APP_URL).port)
            url = info.requestUrl().toString()
            if info.requestUrl().scheme() not in ("data", "blob", "qrc", "about") and not is_local_url(url, ports):
                info.block(True)

    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Document Review Agent")
    window = QMainWindow()
    window.setWindowTitle("Document Review Agent")
    window.resize(1200, 850)
    view = QWebEngineView(window)
    profile = QWebEngineProfile(view)
    interceptor = LocalRequests(profile)
    profile.setUrlRequestInterceptor(interceptor)
    page = QWebEnginePage(profile, view)
    view.setPage(page)
    window.setCentralWidget(view)

    def save_download(item):
        path, _ = QFileDialog.getSaveFileName(window, "Save review", item.downloadFileName())
        if path:
            item.setDownloadDirectory(str(Path(path).parent))
            item.setDownloadFileName(Path(path).name)
            item.accept()
        else:
            item.cancel()

    profile.downloadRequested.connect(save_download)
    view.setUrl(QUrl(f"http://127.0.0.1:{server.server_port}"))
    opened_review = False

    def advance():
        nonlocal opened_review
        if launcher.STATE["status"] == "closed":
            window.close()
        elif launcher.STATE["status"] == "ready" and not opened_review:
            opened_review = True
            view.setUrl(QUrl(launcher.APP_URL))

    timer = QTimer(window)
    timer.timeout.connect(advance)
    timer.start(300)
    window.show()
    # Capture only this app's own window for development smoke verification.
    if os.environ.get("DOCUMENT_REVIEW_SMOKE_CAPTURE"):
        def capture():
            window.grab().save(os.environ["DOCUMENT_REVIEW_SMOKE_CAPTURE"])
            def captured_text(text):
                Path(os.environ["DOCUMENT_REVIEW_SMOKE_CAPTURE"]).with_suffix(".txt").write_text(text, encoding="utf-8")
                window.close()
            page.toPlainText(captured_text)
        QTimer.singleShot(5000, capture)
    app.exec()
    page.deleteLater()
