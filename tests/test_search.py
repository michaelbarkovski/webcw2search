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
            CrawledPage(
                url="https://quotes.toscrape.com/page/4/",
                title="Page 4",
                text="Good stories mention friends later",
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

    assert set(postings) == {
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/4/",
    }
    assert postings["https://quotes.toscrape.com/"].frequency == 3


def test_postings_for_empty_word(engine: SearchEngine) -> None:
    assert engine.postings_for("!!!") == {}


def test_find_single_word_returns_ranked_results(engine: SearchEngine) -> None:
    results, suggestions = engine.find("friends")

    assert suggestions == {}
    assert results[0].url == "https://quotes.toscrape.com/"
    assert {result.url for result in results} == {
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
        "https://quotes.toscrape.com/page/4/",
    }


def test_find_multi_word_query_requires_all_terms(engine: SearchEngine) -> None:
    results, suggestions = engine.find("good friends")

    assert suggestions == {}
    assert [result.url for result in results] == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/4/",
    ]


def test_empty_query_returns_no_results(engine: SearchEngine) -> None:
    assert engine.find("   ") == ([], {})


def test_missing_word_returns_suggestions(engine: SearchEngine) -> None:
    results, suggestions = engine.find("frends")

    assert results == []
    assert suggestions["frends"] == ["friends"]


def test_phrase_search_requires_consecutive_positions(engine: SearchEngine) -> None:
    results, suggestions = engine.find('"good friends"')

    assert suggestions == {}
    assert [result.url for result in results] == ["https://quotes.toscrape.com/"]
    assert results[0].score > 1


def test_phrase_search_does_not_match_separate_words(engine: SearchEngine) -> None:
    results, suggestions = engine.find('"good make"')

    assert suggestions == {}
    assert results == []


def test_boolean_and_matches_both_sides(engine: SearchEngine) -> None:
    results, suggestions = engine.find("good AND friends")

    assert suggestions == {}
    assert [result.url for result in results] == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/4/",
    ]


def test_boolean_or_matches_either_side(engine: SearchEngine) -> None:
    results, suggestions = engine.find("indifference OR bright")

    assert suggestions == {}
    assert {result.url for result in results} == {
        "https://quotes.toscrape.com/page/2/",
        "https://quotes.toscrape.com/page/3/",
    }


def test_boolean_not_excludes_right_side(engine: SearchEngine) -> None:
    results, suggestions = engine.find("good NOT friends")

    assert suggestions == {}
    assert results == []


def test_result_snippet_contains_matched_terms(engine: SearchEngine) -> None:
    results, _ = engine.find('"good friends"')

    assert "Good friends" in results[0].snippet
