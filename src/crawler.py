from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


DEFAULT_START_URL = "https://quotes.toscrape.com/"
DEFAULT_POLITENESS_SECONDS = 6.0


class CrawlError(RuntimeError):
    pass


@dataclass(frozen=True)
class CrawledPage:
    url: str
    title: str
    text: str


class QuoteCrawler:
    def __init__(
        self,
        start_url: str = DEFAULT_START_URL,
        politeness_seconds: float = DEFAULT_POLITENESS_SECONDS,
        timeout_seconds: float = 10.0,
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.start_url = start_url
        self.politeness_seconds = politeness_seconds
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()
        self.sleeper = sleeper
        self.logger = logger

    def crawl(self, max_pages: int | None = None) -> list[CrawledPage]:
        pages: list[CrawledPage] = []
        visited: set[str] = set()
        next_url: str | None = self.start_url

        while next_url:
            if next_url in visited:
                break
            if max_pages is not None and len(pages) >= max_pages:
                break

            if pages:
                if self.logger:
                    self.logger(f"Waiting {self.politeness_seconds:.0f} seconds before the next request...")
                self.sleeper(self.politeness_seconds)

            if self.logger:
                self.logger(f"Fetching {next_url}")
            html = self._fetch(next_url)
            page, next_url = self._parse_page(next_url, html)
            pages.append(page)
            visited.add(page.url)

        return pages

    def _fetch(self, url: str) -> str:
        try:
            response = self.session.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CrawlError(f"Could not fetch {url}: {exc}") from exc
        return response.text

    def _parse_page(self, url: str, html: str) -> tuple[CrawledPage, str | None]:
        #html parsing
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else url

        #quote text
        quote_blocks = soup.select(".quote")
        if quote_blocks:
            text_parts: list[str] = []
            for block in quote_blocks:
                quote = block.select_one(".text")
                author = block.select_one(".author")
                tags = [tag.get_text(" ", strip=True) for tag in block.select(".tags .tag")]
                if quote:
                    text_parts.append(quote.get_text(" ", strip=True))
                if author:
                    text_parts.append(author.get_text(" ", strip=True))
                text_parts.extend(tags)
            text = " ".join(text_parts)
        else:
            #fallback text
            text = soup.get_text(" ", strip=True)

        #next page
        next_link = soup.select_one("li.next a")
        next_url = urljoin(url, next_link["href"]) if next_link and next_link.get("href") else None

        return CrawledPage(url=url, title=title, text=text), next_url
