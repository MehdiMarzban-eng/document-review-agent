"""Multiple source documents with stable, document-qualified passage IDs."""
from dataclasses import asdict
import hashlib
import re
from pathlib import Path

from evidence_search import SearchIndex, VERSION, chunk_page, index_pdf


class Corpus:
    def __init__(self, documents, max_documents=8):
        if not documents or (max_documents is not None and len(documents) > max_documents):
            raise ValueError(f"Supply at least one document" + (f" (maximum {max_documents})." if max_documents is not None else "."))
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
    def from_paths(cls, paths, max_documents=8, max_file_bytes=20 * 1024 * 1024,
                   max_pages=300, max_passages=2000):
        paths = list(paths)
        if max_documents is not None and len(paths) > max_documents:
            raise ValueError(f"Supply at most {max_documents} documents.")
        documents = []
        for source in map(Path, paths):
            if max_file_bytes is not None and source.stat().st_size > max_file_bytes:
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
            if (max_pages is not None and data["page_count"] > max_pages) or (max_passages is not None and len(data["passages"]) > max_passages):
                raise ValueError("Document is too large: maximum 300 pages / 2,000 passages.")
            documents.append(data)
        return cls(documents, max_documents=max_documents)

    def manifest(self):
        return [{"document_id": key, "name": data["source_name"],
                 "sha256": data["source_sha256"], "pages": data["page_count"]}
                for key, data in self.documents.items()]

    def _annotate(self, identity, passages):
        return [dict(p, document_id=identity,
                     source_name=self.documents[identity]["source_name"]) for p in passages]

    def overview(self):
        """Real opening/closing excerpts for planning, never generated summaries."""
        result = []
        for identity, data in self.documents.items():
            passages = data["passages"]
            opening = passages[:2]
            # Stop at the reference section so bibliography titles do not become summaries.
            body = []
            for passage in passages:
                body.append(passage)
                if re.search(r"\b(?:References|REFERENCES|Bibliography)\b", passage["text"]):
                    break
            closing = [p for p in body if re.search(
                r"\b(conclusions?|summary|discussion)\b", p["text"], re.I)]
            selected = {p["id"]: p for p in opening + closing[-2:]}
            result.extend(self._annotate(identity, list(selected.values())))
        return result

    def search_many(self, queries, document_ids=None, top_k=3):
        """Fuse independently worded searches per document without comparing BM25 scores."""
        if not isinstance(queries, list) or not 1 <= len(queries) <= 4:
            raise ValueError("Supply one to four search queries.")
        identities = list(self.documents) if document_ids is None else document_ids
        if not identities or any(i not in self.documents for i in identities):
            raise ValueError("Unknown or empty document scope.")
        result = []
        for identity in identities:
            scores, candidates = {}, {}
            for query in queries:
                for rank, passage in enumerate(self.search(query, identity, top_k=5), 1):
                    key = passage["id"]
                    candidates[key] = passage
                    scores[key] = scores.get(key, 0) + 1 / (60 + rank)
            ordered = sorted(candidates, key=lambda key: scores[key], reverse=True)
            result.extend(candidates[key] for key in ordered[:top_k])
        return self.with_neighbors(result)

    def with_neighbors(self, passages):
        """Include the next overlapping chunk when an excerpt ends mid-argument."""
        expanded = {}
        positions = {identity: {p["id"]: n for n, p in enumerate(data["passages"])}
                     for identity, data in self.documents.items()}
        for passage in passages:
            expanded[passage["id"]] = passage
            identity = passage["document_id"]
            source = self.documents[identity]["passages"]
            following = positions[identity][passage["id"]] + 1
            if following < len(source) and source[following]["pdf_page"] == passage["pdf_page"]:
                neighbor = self._annotate(identity, [source[following]])[0]
                expanded[neighbor["id"]] = neighbor
        return list(expanded.values())

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
