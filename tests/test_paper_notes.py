import copy
from pathlib import Path
import tempfile
import unittest

from corpus import Corpus
from paper_notes import prepare, validate_notes, audit_answer, FIELDS


class Provider:
    model = "local-test"
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []
    def decide(self, system, context, schema):
        self.calls.append((system, context, schema))
        return copy.deepcopy(next(self.replies))


class PaperNoteTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'paper.md'
        self.path.write_text('Historical background: a serial emotion circuit was proposed. '
                             'Conclusions: Reciprocal memory connections form parallel routes, not a serial loop.')
        self.corpus = Corpus.from_paths([self.path])
        self.passage = self.corpus.overview()[0]
        self.notes = {field: {"text": "", "passage_ids": []} for field in FIELDS}
        self.notes['contribution'] = {"text": "Memory connections form parallel routes.",
                                      "passage_ids": [self.passage['id']]}

    def test_audited_notes_are_reused_but_model_change_reprepares(self):
        provider = Provider([self.notes] * 4)
        first, trace, requests = prepare(self.corpus, provider)
        self.assertEqual(requests, 2)
        second, trace, requests = prepare(self.corpus, provider)
        self.assertEqual(requests, 0)
        self.assertEqual(first, second)
        provider.model = 'other-model'
        _, _, requests = prepare(self.corpus, provider)
        self.assertEqual(requests, 2)
        self.assertEqual(len(provider.calls), 4)

    def test_source_change_cannot_reuse_old_notes(self):
        provider = Provider([self.notes] * 2)
        prepare(self.corpus, provider)
        self.path.write_text('Conclusions: A different paper reports different evidence.')
        changed = Corpus.from_paths([self.path])
        changed.paper_note_cache = self.corpus.paper_note_cache
        new = copy.deepcopy(self.notes)
        new['contribution']['passage_ids'] = [changed.overview()[0]['id']]
        _, _, requests = prepare(changed, Provider([new] * 2))
        self.assertEqual(requests, 2)

    def test_renamed_source_reuses_notes_with_current_provenance(self):
        prepare(self.corpus, Provider([self.notes] * 2))
        renamed = self.path.with_name('renamed.md')
        renamed.write_bytes(self.path.read_bytes())
        changed = Corpus.from_paths([renamed])
        changed.paper_note_cache = self.corpus.paper_note_cache
        records, _, requests = prepare(changed, Provider([]))
        self.assertEqual(requests, 0)
        self.assertEqual(records[0]['source_name'], 'renamed.md')
        self.assertEqual(records[0]['evidence'][0]['source_name'], 'renamed.md')

    def test_invented_note_citation_is_rejected_and_not_cached(self):
        bad = copy.deepcopy(self.notes)
        bad['contribution']['passage_ids'] = ['invented']
        records, trace, requests = prepare(self.corpus, Provider([bad]))
        self.assertEqual(requests, 1)
        self.assertIsNone(records[0]['notes'])
        self.assertFalse(self.corpus.paper_note_cache)

    def test_note_audit_can_correct_historical_background(self):
        draft = copy.deepcopy(self.notes)
        draft['contribution']['text'] = 'The authors propose a serial emotion circuit.'
        records, _, _ = prepare(self.corpus, Provider([draft, self.notes]))
        self.assertEqual(records[0]['notes'], self.notes)

    def answer(self, text):
        p = self.passage
        return {'status': 'answered', 'unanswered_parts': [], 'claims': [{
            'text': text, 'evidence': [{'document_id': p['document_id'], 'pdf_page': p['pdf_page'],
                                     'passage_id': p['id'], 'source_name': p['source_name']}]}]}

    def test_unsupported_historical_claim_removed_and_original_request_kept(self):
        provider = Provider([{'verdict': 'unsupported', 'is_cross_paper_comparison': False, 'passage_ids': [], 'issue': 'Historical theory, not the authors conclusion.'}])
        answer, trace, requests = audit_answer(self.corpus, provider, 'What is the takeaway?',
                                             self.answer('This paper proves a serial emotion circuit.'))
        self.assertEqual(answer['claims'], [])
        self.assertEqual(answer['unanswered_parts'], ['What is the takeaway?'])
        self.assertEqual(answer['status'], 'insufficient_evidence')

    def test_one_source_cannot_pass_a_cross_paper_comparison_check(self):
        provider = Provider([{'verdict': 'supported', 'is_cross_paper_comparison': True, 'passage_ids': [self.passage['id']], 'issue': ''}])
        answer, trace, requests = audit_answer(self.corpus, provider, 'Do these papers agree?',
                                             self.answer('The papers all agree.'))
        self.assertFalse(answer['claims'])
        self.assertIn('at least two', trace[0]['message'])

    def test_malformed_audit_citation_withholds_finding_without_crashing(self):
        provider = Provider([{'verdict': 'supported', 'is_cross_paper_comparison': False,
                              'passage_ids': [{}], 'issue': ''}])
        answer, trace, _ = audit_answer(self.corpus, provider, 'Main idea?', self.answer('Memory connections.'))
        self.assertFalse(answer['claims'])
        self.assertEqual(trace[0]['message'], 'Invalid finding check.')

    def test_supported_finding_preserves_text_resolves_page_and_counts_request(self):
        provider = Provider([{'verdict': 'supported', 'is_cross_paper_comparison': False,
            'passage_ids': [self.passage['id']], 'issue': 'Corrected emphasis.'}])
        answer, trace, requests = audit_answer(self.corpus, provider, 'What does it conclude?',
                                             self.answer('There are memory connections.'))
        self.assertEqual(requests, 1)
        self.assertEqual(answer['claims'][0]['text'], 'There are memory connections.')
        self.assertEqual(answer['status'], 'answered')
        self.assertEqual(answer['claims'][0]['evidence'][0]['passage_text'], self.passage['text'])

    def test_complete_review_prepares_then_reuses_notes_and_counts_all_calls(self):
        from agent import review
        plan = {'kind': 'overview', 'queries': ['parallel memory routes']}
        finding = {
            'text': 'The review describes parallel memory routes.',
            'evidence': [{'passage_id': self.passage['id']}]}
        synthesis = {'status': 'answered', 'claims': [], 'unanswered_parts': []}
        audit = {'verdict': 'supported', 'is_cross_paper_comparison': False, 'passage_ids': [self.passage['id']], 'issue': ''}
        provider = Provider([self.notes, self.notes, plan, finding, synthesis, audit, plan, finding, synthesis, audit])
        provider.understands_questions = provider.prepares_paper_notes = True
        first = review(self.corpus, 'What is the main contribution?', provider)
        second = review(self.corpus, 'What does the paper teach us?', provider)
        self.assertEqual(first['model_requests'], 6)
        self.assertEqual(first['paper_preparation']['model_requests'], 2)
        self.assertEqual(second['model_requests'], 4)
        self.assertEqual(second['paper_preparation']['model_requests'], 0)
        self.assertEqual(first['claim_check'], 'completed')
        self.assertTrue(provider.calls[3][1]['document'])
        self.assertEqual(second['paper_answer_requests'], 1)

    def test_overview_requires_an_explicit_slot_for_every_selected_paper(self):
        from paper_review import synthesis_schema, normalize_synthesis
        records = [{'document_id': 'a', 'source_name': 'a.pdf'}, {'document_id': 'b', 'source_name': 'b.pdf'}]
        schema = synthesis_schema([], records, 'overview')
        self.assertEqual(schema['properties']['paper_findings']['required'], ['a', 'b'])
        with self.assertRaises(ValueError):
            normalize_synthesis({'paper_findings': {'a': {}}, 'synthesis': []}, records, 'overview', 'Main ideas?')
        result = normalize_synthesis({'paper_findings': {
            'a': {'text': 'A contribution.', 'evidence': [{'passage_id': 'a-1'}]},
            'b': {'text': '', 'evidence': []}}, 'synthesis': []}, records, 'overview', 'Main ideas?')
        self.assertEqual(result['status'], 'partially_answered')
        self.assertEqual(result['unanswered_parts'], ['Main ideas?'])

    def test_unchecked_findings_are_withheld_when_check_budget_is_exhausted(self):
        provider = Provider([])
        answer, trace, requests = audit_answer(self.corpus, provider, 'What does it conclude?',
                                             self.answer('There are memory connections.'), max_claims=0)
        self.assertEqual(requests, 0)
        self.assertFalse(answer['claims'])
        self.assertEqual(answer['unanswered_parts'], ['What does it conclude?'])
        self.assertEqual(trace[0]['message'], 'Finding check budget reached.')


if __name__ == '__main__':
    unittest.main()
