from __future__ import annotations

import math
import re
from dataclasses import dataclass
from difflib import get_close_matches

from .indexer import InvertedIndex, Posting, tokenize


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    score: float
    matched_terms: list[str]
    snippet: str = ""


class SearchEngine:
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
        index = self._require_index()
        query = query.strip()
        terms = self._query_terms(query)
        if not terms:
            return [], {}

        missing = [term for term in terms if term not in index.terms]
        suggestions = {term: self.suggest(term) for term in missing}
        if missing:
            return [], suggestions

        #query mode
        phrase_terms = self._phrase_terms(query)
        candidate_urls = self._candidate_urls(query, terms)
        if phrase_terms:
            candidate_urls = {
                url for url in candidate_urls if self._contains_phrase(url, phrase_terms)
            }

        results = [
            SearchResult(
                url=url,
                title=index.documents[url].title,
                score=self._score(url, terms, phrase_terms),
                matched_terms=terms,
                snippet=self._snippet(url, phrase_terms or terms),
            )
            for url in candidate_urls
        ]
        results.sort(key=lambda result: (-result.score, result.url))
        return results, suggestions

    def suggest(self, word: str, limit: int = 3) -> list[str]:
        index = self._require_index()
        return get_close_matches(word.lower(), index.terms.keys(), n=limit, cutoff=0.72)

    def _query_terms(self, query: str) -> list[str]:
        raw_tokens = re.findall(r'"[^"]+"|\S+', query)
        operator_words = {"AND", "OR", "NOT"}
        searchable_parts = [token for token in raw_tokens if token not in operator_words]
        return tokenize(" ".join(searchable_parts))

    def _phrase_terms(self, query: str) -> list[str]:
        phrases = re.findall(r'"([^"]+)"', query)
        if not phrases:
            return []
        return tokenize(phrases[0])

    def _candidate_urls(self, query: str, terms: list[str]) -> set[str]:
        #boolean search
        operator = self._boolean_operator(query)
        if operator is None:
            return self._and_urls(terms)

        left, _, right = query.partition(f" {operator} ")
        left_terms = tokenize(left)
        right_terms = tokenize(right)

        if operator == "AND":
            return self._and_urls(left_terms) & self._and_urls(right_terms)
        if operator == "OR":
            return self._and_urls(left_terms) | self._and_urls(right_terms)
        if operator == "NOT":
            return self._and_urls(left_terms) - self._and_urls(right_terms)
        return self._and_urls(terms)

    def _boolean_operator(self, query: str) -> str | None:
        found = [operator for operator in ("AND", "OR", "NOT") if f" {operator} " in query]
        if len(found) == 1:
            return found[0]
        return None

    def _and_urls(self, terms: list[str]) -> set[str]:
        index = self._require_index()
        if not terms:
            return set()

        candidate_urls = set(index.terms[terms[0]])
        for term in terms[1:]:
            candidate_urls &= set(index.terms[term])
        return candidate_urls

    def _contains_phrase(self, url: str, phrase_terms: list[str]) -> bool:
        #phrase search
        if len(phrase_terms) < 2:
            return bool(phrase_terms)

        index = self._require_index()
        first_positions = index.terms[phrase_terms[0]][url].positions
        following_positions = [
            set(index.terms[term][url].positions) for term in phrase_terms[1:]
        ]
        for start in first_positions:
            if all(start + offset + 1 in positions for offset, positions in enumerate(following_positions)):
                return True
        return False

    def _score(self, url: str, terms: list[str], phrase_terms: list[str] | None = None) -> float:
        #tf-idf
        index = self._require_index()
        document = index.documents[url]
        document_length = max(document.length, 1)
        score = 0.0

        matched_terms = [term for term in terms if url in index.terms[term]]
        for term in matched_terms:
            posting = index.terms[term][url]
            tf = posting.frequency / document_length
            idf = math.log((1 + index.document_count) / (1 + len(index.terms[term]))) + 1
            score += tf * idf

        phrase_bonus = 1.0 if phrase_terms and self._contains_phrase(url, phrase_terms) else 0.0
        return score + self._proximity_bonus(url, matched_terms) + phrase_bonus

    def _proximity_bonus(self, url: str, terms: list[str]) -> float:
        #word distance
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

    def _snippet(self, url: str, terms: list[str], radius: int = 70) -> str:
        #snippet
        index = self._require_index()
        text = index.documents[url].text
        if not text:
            return ""

        needle = " ".join(terms)
        match = re.search(re.escape(needle), text, flags=re.IGNORECASE) if needle else None
        if match is None:
            for term in terms:
                match = re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE)
                if match is not None:
                    break
        if match is None:
            return text[: radius * 2].strip()

        start = max(match.start() - radius, 0)
        end = min(match.end() + radius, len(text))
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return f"{prefix}{text[start:end].strip()}{suffix}"

    def _require_index(self) -> InvertedIndex:
        if self.index is None:
            raise ValueError("No index loaded. Run 'build' or 'load' first.")
        return self.index
