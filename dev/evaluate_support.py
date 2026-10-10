"""Explicit local-model development checks; never downloads a model or calls a cloud API."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from corpus import Corpus
from evidence_search import VERSION
from paper_notes import audit_answer
from providers import Ollama


def evaluate(cases, provider):
    results = []
    for case in cases:
        text = case['source']
        corpus = Corpus([{'schema_version': VERSION, 'source_name': case['id'] + '.txt',
            'source_sha256': hashlib.sha256(text.encode()).hexdigest(), 'page_count': 1, 'empty_pages': [],
            'passages': [{'id': 'p1', 'text': text, 'pdf_page': 1, 'page_label': '1'}]}])
        doc = next(iter(corpus.documents))
        p = corpus._annotate(doc, corpus.documents[doc]['passages'])[0]
        citation = {'document_id': doc, 'passage_id': p['id'], 'pdf_page': 1,
                    'source_name': p['source_name'], 'support_quote': text}
        started = time.monotonic()
        answer, trace, calls = audit_answer(corpus, provider, '', {'status': 'answered',
            'claims': [{'text': case['claim'], 'evidence': [citation]}], 'unanswered_parts': []})
        outcome = answer['claims'][0]['support_check'] if answer['claims'] else 'withheld'
        if any(t.get('verdict') is None and t['action'] == 'finding_removed' for t in trace):
            outcome = 'check_unavailable'
        result = {'id': case['id'], 'expected': case['expected'], 'outcome': outcome,
                  'requests': calls, 'seconds': round(time.monotonic() - started, 3), 'trace': trace}
        results.append(result)
        print(f"{case['id']}: {outcome} (expected {case['expected']})", flush=True)
    summary = {'cases': len(results),
        'false_support': sum(r['outcome'] == 'model_supported' and r['expected'] == 'unsupported' for r in results),
        'false_rejection': sum(r['outcome'] == 'withheld' and r['expected'] == 'supported' for r in results),
        'needs_review': sum(r['outcome'] == 'needs_review' for r in results),
        'check_unavailable': sum(r['outcome'] == 'check_unavailable' for r in results),
        'requests': sum(r['requests'] for r in results)}
    return {'model': provider.model, 'summary': summary, 'results': results,
            'qualification': 'Synthetic development fixtures, not held-out evaluation or general accuracy.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='qwen2.5:7b', help='An already installed Ollama model.')
    parser.add_argument('--port', type=int, choices=[11434, 11435], default=11435)
    parser.add_argument('--cases', type=Path, default=ROOT / 'dev/support_cases.json')
    parser.add_argument('--output', type=Path, default=ROOT / '.test-tmp/support-development.json')
    args = parser.parse_args()
    report = evaluate(json.loads(args.cases.read_text(encoding='utf-8')), Ollama(args.model, port=args.port))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report['summary'], indent=2))
