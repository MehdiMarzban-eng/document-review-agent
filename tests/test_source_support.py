import unittest

from source_support import checked_quote, validate_finding, resolve_answer, source_sentences, resolve_selection


class SourceSupportTests(unittest.TestCase):
    def setUp(self):
        self.passage = {'id': 'd:p1', 'document_id': 'd', 'source_name': 'study.txt',
                        'pdf_page': 1, 'page_label': '1',
                        'text': 'Earlier reports claimed benefit. This study did not find a clinical benefit. '
                                'We mapped ﬁbre pathways.\nThe atlas has 45 plates.'}

    def test_invented_or_spliced_quote_is_rejected(self):
        for quote in ['This study found a clinical benefit.', 'The atlas has 46 plates.',
                      'Earlier reports claimed benefit. The atlas has 45 plates.']:
            with self.subTest(quote=quote), self.assertRaises(ValueError):
                checked_quote(quote, self.passage)

    def test_typography_and_line_break_normalization_preserves_words(self):
        self.assertEqual(checked_quote('We mapped fibre pathways. The atlas has 45 plates.', self.passage),
                         'We mapped fibre pathways. The atlas has 45 plates.')

    def test_resolved_quote_retains_original_source_context_and_provenance(self):
        claim = {'evidence': [{'passage_id': 'd:p1', 'quote': 'This study did not find a clinical benefit.'}],
                 'text': 'The study found no clinical benefit.'}
        validate_finding(claim, [self.passage])
        answer = resolve_answer({'status': 'answered', 'claims': [claim], 'unanswered_parts': []}, [self.passage])
        citation = answer['claims'][0]['evidence'][0]
        self.assertEqual(citation['support_quote'], 'This study did not find a clinical benefit.')
        self.assertEqual(citation['passage_text'], self.passage['text'])
        self.assertEqual(citation['source_name'], 'study.txt')
        self.assertIn('quote', claim['evidence'][0])  # Does not mutate the model output.

    def test_copying_a_real_quote_does_not_establish_paraphrase_support(self):
        # Local validation establishes provenance only; a semantic check is still required.
        claim = {'evidence': [{'passage_id': 'd:p1', 'quote': 'This study did not find a clinical benefit.'}],
                 'text': 'The study proved a clinical benefit.'}
        self.assertEqual(validate_finding(claim, [self.passage]), claim)

    def test_unknown_source_and_missing_quote_are_rejected(self):
        for citation in [{'passage_id': 'other', 'quote': 'The atlas has 45 plates.'}, {'passage_id': 'd:p1'}]:
            with self.subTest(citation=citation), self.assertRaises(ValueError):
                validate_finding({'text': 'The atlas has 45 plates.', 'evidence': [citation]}, [self.passage])

    def test_explicit_no_answer_does_not_require_a_fabricated_quote(self):
        value = {'text': '', 'evidence': []}
        self.assertEqual(validate_finding(value, [self.passage]), value)

    def test_selected_sentence_is_resolved_to_its_original_passage_without_model_quotes(self):
        units = source_sentences([self.passage])
        chosen = next(i for i, u in units.items() if 'did not find' in u['text'])
        finding = resolve_selection({'evidence': [chosen], 'text': 'No clinical benefit was found.'}, units, [self.passage])
        self.assertEqual(finding['evidence'], [{'passage_id': 'd:p1', 'quote': 'This study did not find a clinical benefit.'}])
        with self.assertRaises(ValueError):
            resolve_selection({'evidence': ['invented'], 'text': 'A benefit was found.'}, units, [self.passage])

    def test_numeric_assertions_need_support_in_selected_sentences(self):
        with self.assertRaises(ValueError):
            validate_finding({'text': 'The atlas was published in 2015 and has 45 plates.',
                'evidence': [{'passage_id': 'd:p1', 'quote': 'The atlas has 45 plates.'}]}, [self.passage])
        self.assertEqual(resolve_selection({'state': 'no_relevant_evidence'}, {}, []), {'text': '', 'evidence': []})

    def test_two_selected_sentences_from_same_passage_keep_both_quotes_and_one_citation(self):
        claim = {'text': 'No clinical benefit; the atlas has 45 plates.', 'evidence': [
            {'passage_id': 'd:p1', 'quote': 'This study did not find a clinical benefit.'},
            {'passage_id': 'd:p1', 'quote': 'The atlas has 45 plates.'}]}
        answer = resolve_answer({'status': 'answered', 'claims': [claim], 'unanswered_parts': []}, [self.passage])
        citations = answer['claims'][0]['evidence']
        self.assertEqual(len(citations), 1)
        self.assertEqual(len(citations[0]['support_quotes']), 2)
