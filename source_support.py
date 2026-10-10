"""Check quoted source spans locally; quote validity is not semantic entailment."""
import copy
import re
import unicodedata

from evidence_answers import validate_answer


def normalized(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text)).strip()


def checked_quote(quote, passage):
    if not isinstance(quote, str) or not 12 <= len(quote.strip()) <= 1600:
        raise ValueError('A source quote must contain 12–1,600 characters.')
    quote = normalized(quote)
    if quote not in normalized(passage['text']):
        raise ValueError('The quoted words do not occur together in the cited passage.')
    return quote


def source_sentences(passages):
    """Short labels map back to actual passages; the model never types citation quotes."""
    units = {}
    for passage in passages:
        for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z])', normalized(passage['text'])):
            if len(sentence) >= 12:
                key = f's{len(units) + 1}'
                units[key] = {'id': key, 'passage_id': passage['id'], 'text': sentence,
                              'source_name': passage['source_name'], 'pdf_page': passage['pdf_page']}
    return units


def selection_schema(units, max_sources=2):
    finding = {'type': 'object', 'properties': {
        'state': {'const': 'finding'},
        'evidence': {'type': 'array', 'minItems': 1, 'maxItems': max_sources, 'items': {'type': 'string', 'enum': list(units)}},
        'text': {'type': 'string', 'minLength': 1, 'maxLength': 360}},
        'required': ['state', 'evidence', 'text'], 'additionalProperties': False}
    return {'oneOf': [finding, {'type': 'object', 'properties': {
        'state': {'const': 'no_relevant_evidence'}}, 'required': ['state'], 'additionalProperties': False}]}


def resolve_selection(value, units, passages, max_sources=2):
    if value == {'state': 'no_relevant_evidence'}:
        return {'text': '', 'evidence': []}
    if isinstance(value, dict) and value.get('state') == 'finding':
        value = {k: v for k, v in value.items() if k != 'state'}
    if (not isinstance(value, dict) or set(value) != {'evidence', 'text'}
            or not isinstance(value['evidence'], list) or len(value['evidence']) > max_sources
            or not isinstance(value['text'], str) or len(value['text']) > 360
            or any(not isinstance(i, str) or i not in units for i in value['evidence'])):
        raise ValueError('Invalid source sentence selection.')
    if not value['text'].strip():
        return {'text': '', 'evidence': []}
    finding = {'text': value['text'], 'evidence': [
        {'passage_id': units[i]['passage_id'], 'quote': units[i]['text']} for i in dict.fromkeys(value['evidence'])]}
    return validate_finding(finding, passages, max_sources=max_sources)


def resolve_answer(raw, passages):
    """Strip quote fields for the reused validator, then attach locally matched spans."""
    clean = copy.deepcopy(raw)
    lookup = {p['id']: p for p in passages}
    quotes = {}
    if not isinstance(clean, dict) or not isinstance(clean.get('claims'), list):
        raise ValueError('Invalid cited answer.')
    for n, claim in enumerate(clean['claims']):
        if not isinstance(claim, dict) or not isinstance(claim.get('evidence'), list):
            raise ValueError('Invalid cited finding.')
        for citation in claim['evidence']:
            if (not isinstance(citation, dict) or set(citation) not in ({'passage_id'}, {'passage_id', 'quote'})
                    or not isinstance(citation['passage_id'], str) or citation['passage_id'] not in lookup):
                raise ValueError('Invalid source reference.')
            if 'quote' in citation:
                quote = checked_quote(citation.pop('quote'), lookup[citation['passage_id']])
                quotes.setdefault((n, citation['passage_id']), []).append(quote)
    answer = validate_answer(clean, passages)
    for n, claim in enumerate(answer['claims']):
        unique = {}
        for citation in claim['evidence']:
            p = lookup[citation['passage_id']]
            citation.update(document_id=p['document_id'], source_name=p['source_name'])
            if (n, p['id']) in quotes:
                citation['support_quotes'] = list(dict.fromkeys(quotes[n, p['id']]))
                citation['support_quote'] = citation['support_quotes'][0]
            unique.setdefault(p['id'], citation)
        claim['evidence'] = list(unique.values())
    return answer


def validate_finding(value, passages, max_sources=2):
    if (not isinstance(value, dict) or set(value) != {'evidence', 'text'}
            or not isinstance(value['text'], str) or len(value['text']) > 360
            or not isinstance(value['evidence'], list) or len(value['evidence']) > max_sources):
        raise ValueError('Invalid short paper finding.')
    if not value['text'].strip() and not value['evidence']:
        return copy.deepcopy(value)
    if not value['text'].strip() or not value['evidence']:
        raise ValueError('A finding needs both text and quoted evidence.')
    if any(not isinstance(c, dict) or set(c) != {'passage_id', 'quote'} for c in value['evidence']):
        raise ValueError('A paper finding needs quoted source evidence.')
    resolve_answer({'status': 'answered', 'claims': [value], 'unanswered_parts': []}, passages)
    stated_numbers = set(re.findall(r'\b\d+(?:\.\d+)?\b', value['text']))
    source_numbers = set(re.findall(r'\b\d+(?:\.\d+)?\b', ' '.join(c['quote'] for c in value['evidence'])))
    if not stated_numbers <= source_numbers:
        raise ValueError('A numeric assertion is absent from the selected source sentences.')
    return copy.deepcopy(value)


def audit_passages(corpus, claim, max_chars=6500):
    """Prioritize actual cited chunks and their same-page neighbors, not whole papers."""
    from question_understanding import bounded_evidence
    cited, nearby = [], []
    for citation in claim['evidence']:
        doc = citation['document_id']
        passages = corpus.documents[doc]['passages']
        index = next((i for i, p in enumerate(passages) if p['id'] == citation['passage_id']), None)
        if index is None:
            raise ValueError('Unknown source passage in finding check.')
        cited.extend(corpus._annotate(doc, [passages[index]]))
        nearby.extend(corpus._annotate(doc, [p for p in passages[max(0, index - 1):index + 2]
                                             if p['pdf_page'] == passages[index]['pdf_page']]))
    # Older/focused answers have IDs but no quotes: allow a short targeted repair search.
    repair = []
    if not all(c.get('support_quote') for c in claim['evidence']):
        repair = corpus.search_many([claim['text'][:180]],
            document_ids=list(dict.fromkeys(c['document_id'] for c in claim['evidence'])), top_k=2)
    return bounded_evidence(cited + repair + nearby, max_chars=max_chars)
