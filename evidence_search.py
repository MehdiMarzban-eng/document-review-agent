"""Local PDF passage search. No network calls, language model, or API key."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

from pypdf import PdfReader
from pypdf.errors import PdfReadError

VERSION = 1
STOP_WORDS = set("a an and are as at be been by can did do does for from had has have how i in is it its of on or that the their these this to was were what when where which who why will with would".split())
TABLE_INTENT = re.compile(
    r"\b(table|mae|mse|rmse|hit@\d+|accuracy|precision|recall|f1|auc|average|mean|"
    r"percentage|percent|ratio|count|sample|latency|throughput|compare|comparison|"
    r"across|by\s+\w+|per\s+\w+|split)\b", re.IGNORECASE)
FOCUS_STOP_WORDS = set("""
    a an and are as at be been by can did do does for from had has have how i in is it its
    of on or that the their these this to was were what when where which who why will with would
    compare compared comparison summarize summary identify differs differ cite supporting support
    evidence across overall any result results values value numbers number provide reports reported
    use used each all eight pipeline
""".split())


@dataclass(frozen=True)
class Passage:
    id: str
    pdf_page: int
    page_label: str
    text: str


def clean_text(text: str) -> str:
    """Normalize extraction artifacts without paraphrasing the source."""
    text = unicodedata.normalize("NFKC", text).replace("\x00", "")
    text = text.replace("\u00ad", "")
    text = re.sub(r"(?<=[A-Za-z])-\s*\n\s*(?=[a-z])", "", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list[str]:
    return [word for word in re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold())
            if word not in STOP_WORDS]


def chunk_page(text: str, page: int, label: str, size: int = 180,
               overlap: int = 40) -> list[Passage]:
    """Overlapping word windows never cross pages, preserving citation accuracy."""
    if size < 1 or not 0 <= overlap < size:
        raise ValueError("Chunk size must be positive and overlap must be smaller than size.")
    words = clean_text(text).split()
    chunks = []
    for start in range(0, len(words), size - overlap):
        chunks.append(Passage(f"p{page:04d}-c{len(chunks) + 1:03d}", page, label,
                              " ".join(words[start:start + size])))
        if start + size >= len(words):
            break
    return chunks


def index_pdf(source: Path, size: int = 180, overlap: int = 40) -> dict:
    if size < 1 or not 0 <= overlap < size:
        raise ValueError("Chunk size must be positive and overlap must be smaller than size.")
    passages, empty_pages = [], []
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else None
        if digest is None:
            stream.seek(0)
            digest = hashlib.sha256(stream.read()).hexdigest()
        stream.seek(0)
        reader = PdfReader(stream)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported. Supply a readable PDF copy.")
        labels = reader.page_labels
        total_pages = len(reader.pages)
        for number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                empty_pages.append(number)
                continue
            passages.extend(chunk_page(text, number, labels[number - 1], size, overlap))
    if not passages:
        raise ValueError("No extractable text found. Scanned PDFs require OCR, which is not included.")
    return {
        "schema_version": VERSION,
        "source_name": source.name,
        "source_sha256": digest,
        "page_count": total_pages,
        "empty_pages": empty_pages,
        "chunk_words": size,
        "overlap_words": overlap,
        "passages": [asdict(passage) for passage in passages],
    }


class SearchIndex:
    """BM25 ranking baseline: term rarity, frequency, and passage length."""

    def __init__(self, data: dict):
        if data.get("schema_version") != VERSION:
            raise ValueError("Unsupported index version. Rebuild the index.")
        self.data = data
        self.passages = [Passage(**item) for item in data["passages"]]
        if not self.passages:
            raise ValueError("Index contains no passages.")
        self.counts = [Counter(tokenize(p.text)) for p in self.passages]
        self.lengths = [sum(count.values()) for count in self.counts]
        self.average_length = sum(self.lengths) / len(self.lengths) or 1
        self.frequencies = Counter(term for count in self.counts for term in count)

    def search(self, question: str, top_k: int = 3) -> list[dict]:
        if top_k < 1:
            raise ValueError("top-k must be positive.")
        terms = set(tokenize(question))
        ranked = []
        for passage, counts, length in zip(self.passages, self.counts, self.lengths):
            score, matched = 0.0, []
            for term in sorted(terms):
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                df = self.frequencies[term]
                idf = math.log(1 + (len(self.passages) - df + 0.5) / (df + 0.5))
                score += idf * (frequency * 2.5) / (frequency + 1.5 * (0.25 + 0.75 * length / self.average_length))
                matched.append(term)
            if score > 0:
                ranked.append({**asdict(passage), "score": round(score, 6), "matched_terms": matched})
        ranked.sort(key=lambda item: (-item["score"], item["pdf_page"], item["id"]))
        # One passage per page reduces duplicate snippets caused by overlapping windows.
        results, seen_pages = [], set()
        for item in ranked:
            if item["pdf_page"] not in seen_pages:
                results.append(item)
                seen_pages.add(item["pdf_page"])
                if len(results) == top_k:
                    break
        return results

    def search_for_answer(self, question: str, top_k: int = 3) -> list[dict]:
        """Blend direct lexical search with a table-focused pass for quantitative asks."""
        direct = self.search(question, top_k * 3)
        if not TABLE_INTENT.search(question):
            return direct[:top_k]

        focused_terms = list(dict.fromkeys(
            token for token in tokenize(question) if token not in FOCUS_STOP_WORDS))
        focused_query = " ".join(focused_terms + ["table", "rows", "values", "average", "zone"])
        focused = self.search(focused_query, top_k * 3)

        # Reciprocal-rank fusion brings table rows forward without discarding
        # useful narrative passages from the original question search.
        fused: dict[str, dict] = {}
        for branch, results in (("question", direct), ("table", focused)):
            for rank, item in enumerate(results, start=1):
                entry = fused.setdefault(item["id"], {
                    "item": item, "score": 0.0, "question_rank": None, "table_rank": None})
                entry["score"] += 1 / (60 + rank)
                entry[f"{branch}_rank"] = rank
                if branch == "table" and entry["question_rank"] is None:
                    entry["item"] = item

        ranked = sorted(fused.values(), key=lambda entry: (
            -entry["score"],
            entry["question_rank"] if entry["question_rank"] is not None else 10**9,
            entry["table_rank"] if entry["table_rank"] is not None else 10**9,
            entry["item"]["pdf_page"], entry["item"]["id"]))
        ordered = []
        # Reserve one slot for the strongest table-focused match. Without this,
        # repeated narrative terms can crowd actual result rows out of top-k.
        if focused:
            numeric_tables = [item for item in focused
                              if re.search(r"\btable\s+[A-Z]?\d", item["text"], re.IGNORECASE)
                              and len(re.findall(r"(?<!\w)\d+(?:\.\d+)?%?(?!\w)", item["text"])) >= 15]
            ordered.append(numeric_tables[0] if numeric_tables else focused[0])
        ordered.extend(entry["item"] for entry in ranked
                       if entry["item"]["id"] not in {item["id"] for item in ordered})
        return ordered[:top_k]


def load_index(path: Path) -> SearchIndex:
    return SearchIndex(json.loads(path.read_text(encoding="utf-8")))


def print_results(index: SearchIndex, question: str, top_k: int) -> None:
    results = index.search(question, top_k)
    print("\nRetrieved source passages (not generated answers). Scores are not confidence estimates.")
    if not results:
        print("No matching keywords. This does not prove the document lacks an answer.")
    for rank, result in enumerate(results, start=1):
        print(f"\n{rank}. PDF page {result['pdf_page']} | document label {result['page_label']} | score {result['score']:.3f}")
        print(f"   Passage {result['id']} | matched: {', '.join(result['matched_terms'])}")
        print(result["text"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("index", help="Extract a PDF to a local JSON index")
    build.add_argument("pdf", type=Path)
    build.add_argument("--output", type=Path, default=Path("indexes/document.json"))
    build.add_argument("--chunk-words", type=int, default=180)
    build.add_argument("--overlap-words", type=int, default=40)
    for command in ("search", "interactive"):
        sub = commands.add_parser(command, help="Search once" if command == "search" else "Interactive passage search")
        sub.add_argument("--index", type=Path, default=Path("indexes/document.json"))
        sub.add_argument("--top-k", type=int, default=3)
        if command == "search":
            sub.add_argument("question")
            sub.add_argument("--json", action="store_true", help="Machine-readable results")
    args = parser.parse_args(argv)
    try:
        if args.command == "index":
            if args.pdf.resolve() == args.output.resolve():
                raise ValueError("Index output must not overwrite the source PDF.")
            data = index_pdf(args.pdf, args.chunk_words, args.overlap_words)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Indexed {data['page_count']} pages into {len(data['passages'])} passages: {args.output}")
            if data["empty_pages"]:
                print(f"Warning: no extracted text on PDF pages {data['empty_pages']}. OCR is not included.")
        else:
            if args.top_k < 1:
                raise ValueError("top-k must be positive.")
            index = load_index(args.index)
            if args.command == "search":
                if args.json:
                    print(json.dumps({"source": index.data["source_name"], "query": args.question,
                                      "results": index.search(args.question, args.top_k)}, ensure_ascii=False, indent=2))
                else:
                    print_results(index, args.question, args.top_k)
            else:
                print(f"Searching {index.data['source_name']}. Enter a question, or 'quit' to exit.")
                while True:
                    try:
                        question = input("\nQuestion> ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        break
                    if question.casefold() in {"quit", "exit"}:
                        break
                    if question:
                        print_results(index, question, args.top_k)
        return 0
    except (OSError, ValueError, KeyError, TypeError, PdfReadError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
