from __future__ import annotations

import pytest

from src.crawler import CrawledPage
from src.indexer import build_index
from src.search import SearchEngine


@pytest.fixture
def engine() -> SearchEngine:
    index = build_index(
        [
            CrawledPage(
                url="https://quotes.toscrape.com/",
                title="Page 1",
                text="Good friends good books make a good life with friends",
            ),
            CrawledPage(
                url="https://quotes.toscrape.com/page/2/",
                title="Page 2",
                text="Friends and courage make life bright",
            ),
            CrawledPage(
                url="https://quotes.toscrape.com/page/3/",
                title="Page 3",
                text="Courage is not indifference",
            ),
        ]
    )
    return SearchEngine(index)


def test_search_requires_loaded_index() -> None:
    engine = SearchEngine()

    with pytest.raises(ValueError, match="No index loaded"):
        engine.find("good")


def test_postings_for_word(engine: SearchEngine) -> None:
    postings = engine.postings_for("GOOD")

    assert list(postings) == ["https://quotes.toscrape.com/"]
    assert postings["https://quotes.toscrape.com/"].frequency == 3


def test_postings_for_empty_word(engine: SearchEngine) -> None:
    assert engine.postings_for("!!!") == {}


def test_find_single_word_returns_ranked_results(engine: SearchEngine) -> None:
    results, suggestions = engine.find("friends")

    assert suggestions == {}
    assert [result.url for result in results] == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
    ]


def test_find_multi_word_query_requires_all_terms(engine: SearchEngine) -> None:
    results, suggestions = engine.find("good friends")

    assert suggestions == {}
    assert [result.url for result in results] == ["https://quotes.toscrape.com/"]


def test_empty_query_returns_no_results(engine: SearchEngine) -> None:
    assert engine.find("   ") == ([], {})


def test_missing_word_returns_suggestions(engine: SearchEngine) -> None:
    results, suggestions = engine.find("frends")

    assert results == []
    assert suggestions["frends"] == ["friends"]
