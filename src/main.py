"""Interactive command-line interface for the coursework search tool."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .crawler import CrawlError, QuoteCrawler
from .indexer import DEFAULT_INDEX_PATH, build_index, load_index, save_index
from .search import SearchEngine


HELP_TEXT = """Commands:
  build              Crawl the website, build the index, and save it
  load               Load the saved index from the file system
  print <word>       Print the inverted index postings for a word
  find <query>       Find pages containing all query words
                     Supports "quoted phrases", AND, OR, and NOT
  help               Show this help text
  exit               Close the shell
"""


OUTPUT_SEPARATOR = "-" * 72


def run_shell(index_path: Path = DEFAULT_INDEX_PATH) -> None:
    engine = SearchEngine()
    print("COMP3011 Search Engine Tool")
    print("Type 'help' to see available commands.")

    while True:
        try:
            raw_command = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw_command:
            print("Please enter a command. Type 'help' for options.")
            continue

        should_exit = handle_command(raw_command, engine, index_path)
        if should_exit:
            break
        print(f"\n{OUTPUT_SEPARATOR}\n")


def handle_command(command: str, engine: SearchEngine, index_path: Path = DEFAULT_INDEX_PATH) -> bool:
    """Handle one shell command. Returns True when the shell should exit."""

    name, _, arguments = command.partition(" ")
    name = name.lower()
    arguments = arguments.strip()

    if name in {"exit", "quit"}:
        print("Goodbye.")
        return True
    if name == "help":
        print(HELP_TEXT)
        return False
    if name == "build":
        _build(engine, index_path)
        return False
    if name == "load":
        _load(engine, index_path)
        return False
    if name == "print":
        _print_word(engine, arguments)
        return False
    if name == "find":
        _find(engine, arguments)
        return False

    print(f"Unknown command: {name}. Type 'help' for options.")
    return False


def _build(engine: SearchEngine, index_path: Path) -> None:
    print("Crawling https://quotes.toscrape.com/ with a 6-second politeness window...")
    started = time.perf_counter()
    crawler = QuoteCrawler(logger=print)
    try:
        pages = crawler.crawl()
    except CrawlError as exc:
        print(exc)
        return

    index = build_index(pages)
    save_index(index, index_path)
    engine.set_index(index)
    elapsed = time.perf_counter() - started
    print(
        f"Built index for {index.document_count} pages and {len(index.terms)} unique words "
        f"in {elapsed:.2f}s. Saved to {index_path}."
    )


def _load(engine: SearchEngine, index_path: Path) -> None:
    try:
        index = load_index(index_path)
    except FileNotFoundError:
        print(f"No saved index found at {index_path}. Run 'build' first.")
        return
    except ValueError as exc:
        print(f"Could not load index: {exc}")
        return

    engine.set_index(index)
    print(f"Loaded index from {index_path}: {index.document_count} pages, {len(index.terms)} words.")


def _print_word(engine: SearchEngine, word: str) -> None:
    if not word:
        print("Usage: print <word>")
        return

    try:
        postings = engine.postings_for(word)
    except ValueError as exc:
        print(exc)
        return

    if not postings:
        suggestions = engine.suggest(word)
        print(f"No entries found for '{word.lower()}'.")
        if suggestions:
            print("Did you mean: " + ", ".join(suggestions))
        return

    print(f"Inverted index for '{word.lower()}':")
    for url, posting in sorted(postings.items()):
        positions = ", ".join(str(position) for position in posting.positions)
        print(f"- {url}: frequency={posting.frequency}, positions=[{positions}]")


def _find(engine: SearchEngine, query: str) -> None:
    if not query:
        print("Usage: find <query>")
        return

    try:
        results, suggestions = engine.find(query)
    except ValueError as exc:
        print(exc)
        return

    if suggestions:
        print(f"No pages found for '{query}'.")
        for term, matches in suggestions.items():
            if matches:
                print(f"Suggestions for '{term}': {', '.join(matches)}")
        return

    if not results:
        print(f"No pages found for '{query}'.")
        return

    print(f"Found {len(results)} page(s) for '{query}':")
    for result in results:
        print(f"- {result.url} (score={result.score:.4f})")
        if result.snippet:
            print(f"  {result.snippet}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="COMP3011 search engine shell")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH, help="Path to the saved index JSON file")
    args = parser.parse_args(argv)
    run_shell(args.index)
    return 0


if __name__ == "__main__":
    sys.exit(main())
