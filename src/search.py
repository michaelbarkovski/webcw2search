"""Search and ranking logic for the inverted index."""

from __future__ import annotations

import math
from dataclasses import dataclass
from difflib import get_close_matches

from .indexer import InvertedIndex, Posting, tokenize


@dataclass(frozen=True)
class SearchResult:
    """A ranked page returned by a query."""

    url: str
    title: str
    score: float
    matched_terms: list[str]


class SearchEngine:
    """Query an inverted index with TF-IDF and simple proximity scoring."""

    def __init__(self, index: InvertedIndex | None = None) -> None:
        self.index = index

    def is_loaded(self) -> bool:
        return self.index is not None

    def set_index(self, index: InvertedIndex) -> None:
        self.index = index

    def postings_for(self, word: str) -> dict[str, Posting]:
        index = self._require_index()
        tokens = tokenize(word)
        if not tokens:
            return {}
        return index.terms.get(tokens[0], {})

    def find(self, query: str) -> tuple[list[SearchResult], dict[str, list[str]]]:
        """Return ranked pages containing all query terms plus suggestions."""

        index = self._require_index()
        terms = tokenize(query)
        if not terms:
            return [], {}

        missing = [term for term in terms if term not in index.terms]
        suggestions = {term: self.suggest(term) for term in missing}
        if missing:
            return [], suggestions

        candidate_urls = set(index.terms[terms[0]])
        for term in terms[1:]:
            candidate_urls &= set(index.terms[term])

        results = [
            SearchResult(
                url=url,
                title=index.documents[url].title,
                score=self._score(url, terms),
                matched_terms=terms,
            )
            for url in candidate_urls
        ]
        results.sort(key=lambda result: (-result.score, result.url))
        return results, suggestions

    def suggest(self, word: str, limit: int = 3) -> list[str]:
        index = self._require_index()
        return get_close_matches(word.lower(), index.terms.keys(), n=limit, cutoff=0.72)

    def _score(self, url: str, terms: list[str]) -> float:
        index = self._require_index()
        document = index.documents[url]
        document_length = max(document.length, 1)
        score = 0.0

        for term in terms:
            posting = index.terms[term][url]
            tf = posting.frequency / document_length
            idf = math.log((1 + index.document_count) / (1 + len(index.terms[term]))) + 1
            score += tf * idf

        return score + self._proximity_bonus(url, terms)

    def _proximity_bonus(self, url: str, terms: list[str]) -> float:
        if len(terms) < 2:
            return 0.0

        index = self._require_index()
        position_lists = [index.terms[term][url].positions for term in terms]
        best_span: int | None = None

        for start in position_lists[0]:
            span_positions = [start]
            for positions in position_lists[1:]:
                nearest = min(positions, key=lambda position: abs(position - start))
                span_positions.append(nearest)
            span = max(span_positions) - min(span_positions)
            if best_span is None or span < best_span:
                best_span = span

        if best_span is None:
            return 0.0
        return 1 / (1 + best_span)

    def _require_index(self) -> InvertedIndex:
        if self.index is None:
            raise ValueError("No index loaded. Run 'build' or 'load' first.")
        return self.index
