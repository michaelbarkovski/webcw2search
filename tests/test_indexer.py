from __future__ import annotations

from src.crawler import CrawledPage
from src.indexer import build_index, load_index, save_index, tokenize


def test_tokenize_is_case_insensitive_and_ignores_punctuation() -> None:
    assert tokenize("Good, GOOD friends!") == ["good", "good", "friends"]


def test_build_index_stores_frequency_and_positions() -> None:
    pages = [
        CrawledPage(url="https://example.com/1", title="One", text="Good friends good books"),
        CrawledPage(url="https://example.com/2", title="Two", text="Friends are precious"),
    ]

    index = build_index(pages)

    assert index.document_count == 2
    assert index.terms["good"]["https://example.com/1"].frequency == 2
    assert index.terms["good"]["https://example.com/1"].positions == [0, 2]
    assert index.terms["friends"]["https://example.com/1"].positions == [1]
    assert index.terms["friends"]["https://example.com/2"].positions == [0]


def test_index_save_and_load_round_trip(tmp_path) -> None:
    index = build_index([CrawledPage(url="https://example.com/", title="Example", text="Simple simple test")])
    path = tmp_path / "index.json"

    save_index(index, path)
    loaded = load_index(path)

    assert loaded.document_count == 1
    assert loaded.documents["https://example.com/"].title == "Example"
    assert loaded.terms["simple"]["https://example.com/"].frequency == 2
