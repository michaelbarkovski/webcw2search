from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .crawler import CrawledPage


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9']+")
DEFAULT_INDEX_PATH = Path("data/index.json")


@dataclass
class PageDocument:
    url: str
    title: str
    length: int
    text: str = ""


@dataclass
class Posting:
    frequency: int
    positions: list[int]


@dataclass
class InvertedIndex:
    documents: dict[str, PageDocument] = field(default_factory=dict)
    terms: dict[str, dict[str, Posting]] = field(default_factory=dict)

    @property
    def document_count(self) -> int:
        return len(self.documents)


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def build_index(pages: list[CrawledPage]) -> InvertedIndex:
    index = InvertedIndex()

    for page in pages:
        #page metadata
        tokens = tokenize(page.text)
        index.documents[page.url] = PageDocument(
            url=page.url,
            title=page.title,
            length=len(tokens),
            text=page.text,
        )

        #word positions
        positions_by_term: dict[str, list[int]] = {}
        for position, token in enumerate(tokens):
            positions_by_term.setdefault(token, []).append(position)

        #postings
        for term, positions in positions_by_term.items():
            index.terms.setdefault(term, {})[page.url] = Posting(
                frequency=len(positions),
                positions=positions,
            )

    return index


def save_index(index: InvertedIndex, path: Path | str = DEFAULT_INDEX_PATH) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "documents": {url: asdict(document) for url, document in index.documents.items()},
        "terms": {
            term: {url: asdict(posting) for url, posting in postings.items()}
            for term, postings in index.terms.items()
        },
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_index(path: Path | str = DEFAULT_INDEX_PATH) -> InvertedIndex:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    documents = {
        url: PageDocument(
            url=data["url"],
            title=data.get("title", data["url"]),
            length=int(data.get("length", 0)),
            text=data.get("text", ""),
        )
        for url, data in payload.get("documents", {}).items()
    }
    terms = {
        term: {
            url: Posting(
                frequency=int(posting["frequency"]),
                positions=[int(position) for position in posting.get("positions", [])],
            )
            for url, posting in postings.items()
        }
        for term, postings in payload.get("terms", {}).items()
    }
    return InvertedIndex(documents=documents, terms=terms)


def term_frequencies(index: InvertedIndex) -> Counter[str]:
    return Counter(
        {
            term: sum(posting.frequency for posting in postings.values())
            for term, postings in index.terms.items()
        }
    )
