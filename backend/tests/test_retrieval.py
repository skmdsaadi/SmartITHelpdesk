from pathlib import Path

from app.documents import extract_document
from app.retrieval import PassageIndex, retrieve


def corpus():
    raw = (Path(__file__).resolve().parents[2] / 'docs/examples/IT_Helpdesk_Demo_Guide.txt').read_bytes()
    return [dict(id=i, text=c['text']) for i, c in enumerate(extract_document(raw, 'guide.txt')['chunks'], 1)]


def test_illustrative_queries_retrieve_the_expected_passage():
    index = PassageIndex(corpus())
    cases = [('How do I troubleshoot a Wi-Fi connection?', 'Wi-Fi connection troubleshooting'),
             ('How do I reset my password?', 'Password reset'),
             ('What should I check when the printer is offline?', 'Printer offline troubleshooting'),
             ('My VPN connection fails. What should I check?', 'VPN connection troubleshooting'),
             ('How can I request software installation?', 'Software installation requests'),
             ('Email is not synchronizing. What should I check?', 'Email synchronization troubleshooting'),
             ('My laptop will not turn on. What should I check?', 'Laptop startup troubleshooting')]
    by_id = {c['id']: c['text'] for c in index.chunks}
    for question, expected in cases:
        found = index.search(question)
        assert found and by_id[found[0]['chunk_id']].startswith(expected), question


def test_unknown_short_and_vocabulary_empty_queries_abstain():
    index = PassageIndex(corpus())
    for q in ['How do I bake a chocolate birthday cake?', 'What will tomorrow lottery numbers be?', 'help', 'password']:
        assert index.search(q) == []
    assert PassageIndex([{'id': 1, 'text': 'the and or the and or'}]).search('reset password') == []


def test_cache_cannot_return_removed_or_replaced_text():
    old = [{'id': 10, 'text': 'Reset a forgotten password using the approved password reset portal.'}]
    replacement = [{'id': 10, 'text': 'Check printer power and paper when the printer is offline.'}]
    assert retrieve(old, 'How do I reset my password?')
    assert retrieve(replacement, 'How do I reset my password?') == []
    assert retrieve([], 'How do I reset my password?') == []
