"""Local TF-IDF retrieval. Returns verbatim passages; there is no language-model generation."""
import hashlib
import json
import re
import threading

METHOD = "tfidf-passages-v1"
MIN_SCORE = 0.18
MIN_SHARED_TERMS = 2
_lock = threading.Lock()
_cached_key = None
_cached_index = None


def normalize(value: str) -> str:
    return re.sub(r"wi[\s-]?fi", "wifi", value.lower())


class PassageIndex:
    def __init__(self, chunks: list[dict]):
        from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
        from threadpoolctl import threadpool_limits
        self.chunks = chunks
        self.stop = set(ENGLISH_STOP_WORDS) | {"help", "please", "issue", "problem", "tell", "need", "office", "company"}
        self.word = TfidfVectorizer(preprocessor=normalize, stop_words=sorted(self.stop),
                                    ngram_range=(1, 2), sublinear_tf=True, max_features=12000)
        self.char = TfidfVectorizer(preprocessor=normalize, analyzer="char_wb", ngram_range=(3, 5),
                                    sublinear_tf=True, max_features=20000)
        texts = [c["text"] for c in chunks]
        self.terms = [self.tokens(t) for t in texts]
        self.word_matrix = None
        self.char_matrix = None
        with threadpool_limits(limits=1):
            # A corpus made only of stop words is valid text but cannot answer a question.
            try:
                self.word_matrix = self.word.fit_transform(texts)
                self.char_matrix = self.char.fit_transform(texts)
            except ValueError as exc:
                if "empty vocabulary" not in str(exc):
                    raise

    def tokens(self, value: str) -> set[str]:
        return set(re.findall(r"(?u)\b\w\w+\b", normalize(value))) - self.stop

    def search(self, question: str) -> list[dict]:
        if self.word_matrix is None or self.char_matrix is None:
            return []
        from threadpoolctl import threadpool_limits
        terms = self.tokens(question)
        if len(terms) < MIN_SHARED_TERMS:
            return []
        with threadpool_limits(limits=1):
            word_scores = (self.word_matrix @ self.word.transform([question]).T).toarray().ravel()
            char_scores = (self.char_matrix @ self.char.transform([question]).T).toarray().ravel()
        scores = .8 * word_scores + .2 * char_scores
        ranked = sorted(range(len(self.chunks)), key=lambda i: (-scores[i], self.chunks[i]["id"]))
        selected = []
        threshold = max(MIN_SCORE, float(scores[ranked[0]]) * .55)
        for i in ranked:
            if scores[i] < threshold:
                break
            if len(terms & self.terms[i]) < MIN_SHARED_TERMS:
                continue
            # Suppress overlapping passages that contain almost identical terms.
            if any(len(self.terms[i] & self.terms[j]) / max(1, len(self.terms[i] | self.terms[j])) > .8 for j in selected):
                continue
            selected.append(i)
            if len(selected) == 3:
                break
        return [{"chunk_id": self.chunks[i]["id"], "score": round(float(scores[i]), 6)} for i in selected]


def retrieve(chunks: list[dict], question: str) -> list[dict]:
    global _cached_key, _cached_index
    if not chunks:
        return []
    # Content-derived identity prevents stale results and cross-database cache reuse.
    key = hashlib.sha256(json.dumps(chunks, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    with _lock:
        if key != _cached_key:
            index = PassageIndex(chunks)
            _cached_index, _cached_key = index, key
        index = _cached_index
    return index.search(question)
