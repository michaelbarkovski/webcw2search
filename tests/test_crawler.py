from __future__ import annotations

import pytest
import requests

from src.crawler import CrawlError, QuoteCrawler


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


class FakeSession:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: float) -> FakeResponse:
        self.requested_urls.append(url)
        if url not in self.pages:
            return FakeResponse("", 404)
        return FakeResponse(self.pages[url])


PAGE_ONE = """
<html>
  <head><title>Quotes Page 1</title></head>
  <body>
    <div class="quote">
      <span class="text">"Good friends, good books, and a sleepy conscience."</span>
      <small class="author">Mark Twain</small>
      <div class="tags"><a class="tag">friends</a><a class="tag">books</a></div>
    </div>
    <li class="next"><a href="/page/2/">Next</a></li>
  </body>
</html>
"""

PAGE_TWO = """
<html>
  <head><title>Quotes Page 2</title></head>
  <body>
    <div class="quote">
      <span class="text">"There is no charm equal to tenderness of heart."</span>
      <small class="author">Jane Austen</small>
      <div class="tags"><a class="tag">love</a></div>
    </div>
  </body>
</html>
"""


def test_crawler_extracts_quotes_and_follows_pagination() -> None:
    session = FakeSession(
        {
            "https://quotes.toscrape.com/": PAGE_ONE,
            "https://quotes.toscrape.com/page/2/": PAGE_TWO,
        }
    )
    sleeps: list[float] = []
    crawler = QuoteCrawler(session=session, sleeper=sleeps.append)

    pages = crawler.crawl()

    assert [page.url for page in pages] == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
    ]
    assert "Good friends" in pages[0].text
    assert "Mark Twain" in pages[0].text
    assert "tenderness of heart" in pages[1].text
    assert sleeps == [6.0]


def test_crawler_raises_clear_error_for_failed_request() -> None:
    crawler = QuoteCrawler(session=FakeSession({}), sleeper=lambda _: None)

    with pytest.raises(CrawlError, match="Could not fetch"):
        crawler.crawl()


def test_crawler_can_limit_pages_for_testing() -> None:
    session = FakeSession(
        {
            "https://quotes.toscrape.com/": PAGE_ONE,
            "https://quotes.toscrape.com/page/2/": PAGE_TWO,
        }
    )
    crawler = QuoteCrawler(session=session, sleeper=lambda _: None)

    pages = crawler.crawl(max_pages=1)

    assert len(pages) == 1
    assert session.requested_urls == ["https://quotes.toscrape.com/"]
