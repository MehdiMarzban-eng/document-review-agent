"""Multiple source documents with stable, document-qualified passage IDs."""
from dataclasses import asdict
import hashlib
from pathlib import Path

from evidence_search import SearchIndex, VERSION, chunk_page, index_pdf


class Corpus:
    def __init__(self, documents):
        if not documents or len(documents) > 8:
            raise ValueError("Supply between one and eight documents.")
        self.documents = {}
        self.indexes = {}
        for data in documents:
            identity = "d" + data["source_sha256"][:16]
            if identity in self.documents:
                continue
            data = dict(data)
            data["passages"] = [dict(p, id=identity + ":" + p["id"])
                                for p in data["passages"]]
            self.documents[identity] = data
            self.indexes[identity] = SearchIndex(data)

    @classmethod
    def from_paths(cls, paths):
        documents = []
        for source in map(Path, paths):
            if source.stat().st_size > 20 * 1024 * 1024:
                raise ValueError("Each document must be at most 20 MB.")
            if source.suffix.lower() == ".pdf":
                data = index_pdf(source)
            elif source.suffix.lower() in {".txt", ".md"}:
                raw = source.read_bytes()
                data = {"schema_version": VERSION, "source_name": source.name,
                        "source_sha256": hashlib.sha256(raw).hexdigest(),
                        "page_count": 1, "empty_pages": [],
                        "passages": [asdict(p) for p in chunk_page(raw.decode("utf-8"), 1, "1")]}
            else:
                raise ValueError("Supported formats: text-readable PDF, UTF-8 TXT, MD.")
            if data["page_count"] > 300 or len(data["passages"]) > 2000:
                raise ValueError("Document is too large: maximum 300 pages / 2,000 passages.")
            documents.append(data)
        return cls(documents)

    def manifest(self):
        return [{"document_id": key, "name": data["source_name"],
                 "sha256": data["source_sha256"], "pages": data["page_count"]}
                for key, data in self.documents.items()]

    def _annotate(self, identity, passages):
        return [dict(p, document_id=identity,
                     source_name=self.documents[identity]["source_name"]) for p in passages]

    def search(self, query, document_id="", top_k=3):
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            raise ValueError("Search query must contain 1–1,000 characters.")
        if type(top_k) is not int or not 1 <= top_k <= 5:
            raise ValueError("top_k must be between one and five.")
        identities = [document_id] if document_id else list(self.documents)
        if any(i not in self.documents for i in identities):
            raise ValueError("Unknown document ID.")
        # Keep each document's top matches: BM25 scores across indexes are not comparable.
        return [p for i in identities
                for p in self._annotate(i, self.indexes[i].search_for_answer(query, top_k))]

    def open_page(self, document_id, page):
        if document_id not in self.documents or type(page) is not int:
            raise ValueError("Provide a known document ID and an integer PDF page.")
        data = self.documents[document_id]
        if not 1 <= page <= data["page_count"]:
            raise ValueError("Page is outside this document.")
        matches = [p for p in data["passages"] if p["pdf_page"] == page]
        if len(matches) > 12:
            raise ValueError("Page exceeds the context limit; use search instead.")
        return self._annotate(document_id, matches)
