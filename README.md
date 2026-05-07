# COMP3011 Coursework 2: Search Engine Tool

This project implements the COMP3011 Web Services and Web Data coursework search tool. It crawls [quotes.toscrape.com](https://quotes.toscrape.com/), builds an inverted index, saves that index to disk, and provides an interactive command-line shell for searching it.

The implementation follows the brief's recommended Python libraries:

- `requests` for HTTP requests
- `beautifulsoup4` for HTML parsing
- `pytest` for automated tests

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Start the interactive shell:

```bash
python -m src.main
```

Available commands:

```text
build
load
print nonsense
find indifference
find good friends
find "good friends"
find good OR friends
find good NOT friends
help
exit
```

### Required Commands

`build` crawls the target website, creates the inverted index, and saves it to `data/index.json`.

`load` loads the previously saved index from `data/index.json`.

`print <word>` prints the inverted index postings for one word, including the page URL, frequency, and word positions.

`find <query>` returns matching pages with a relevance score and a short result snippet. Standard multi-word queries use AND semantics, so `find good friends` returns pages containing both words. The command also supports quoted phrase search and simple uppercase Boolean operators:

```text
find "good friends"
find good AND friends
find good OR friends
find good NOT friends
```

## Architecture

The code is split into three main responsibilities:

- `src/crawler.py`: fetches pages using `requests`, parses quote text and pagination links using `BeautifulSoup`, and enforces the 6-second politeness window required by the brief.
- `src/indexer.py`: tokenises text case-insensitively, builds the inverted index, stores frequencies and positions, and saves/loads JSON.
- `src/search.py`: handles lookup, multi-word query matching, phrase search, Boolean search, TF-IDF ranking, proximity scoring, snippets, and simple spelling suggestions.

The inverted index stores each term as a dictionary of page postings:

```json
{
  "good": {
    "https://quotes.toscrape.com/": {
      "frequency": 3,
      "positions": [0, 2, 6]
    }
  }
}
```

Page metadata is stored separately so search results can include page titles, document lengths for ranking, and original text for snippets.

## Design Decisions

Search is case-insensitive because the brief says that words such as `Good` and `good` should be treated as the same word. The index stores positions as well as frequencies so the basic requirements are met and multi-word ranking can reward terms that appear near each other.

The crawler waits 6 seconds between live website requests. Tests mock the HTTP layer and the sleep function so they run quickly without contacting the live website.

The `find` command uses AND semantics for normal multi-word queries: every query term must appear in a page for that page to be returned. This matches the brief's example of finding pages containing both `good` and `friends`.

Phrase search uses the stored word positions to check whether quoted terms appear consecutively. Boolean search is intentionally simple and demo-friendly: it supports one uppercase operator per query (`AND`, `OR`, or `NOT`) and does not support nested parentheses.

## Testing

Run the test suite:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=src --cov-report=term-missing
```

The tests cover crawler pagination, network errors, tokenisation, index statistics, save/load, single-word search, multi-word search, phrase search, Boolean search, snippets, empty queries, missing words, and ranked results.

## Benchmarking Notes

For the target website, crawling time is dominated by the required 6-second politeness window. Indexing is linear in the number of tokens: each token is processed once and added to a dictionary-backed inverted index. Querying is efficient because each word lookup is a dictionary lookup, multi-word queries intersect posting lists before ranking candidate pages, and phrase search reuses stored word positions instead of scanning every page from scratch.

## GenAI Reflection Notes

GenAI was used in critical areas of this project. First of all it was used as a checklist for all requirements, making sure none were missed. During advanced feature implementation, it was used to suggest new ways to elevate the project and make it stand out, the suggestion feature was one I was most proud of. AI was also used to make sure I had a comprehensive testing suite, which ensures everything has been tested and is what helped me a lot in CW1, and I have transferred this skill onto this coursework. 

## Submission Checklist

- Run `build` once and include the generated `data/index.json`.
- Run `pytest` and note the result for the video.
- Record a maximum 5-minute video showing `build`, `load`, `print`, and `find`.
- Demonstrate edge cases such as empty queries and missing words.
- Show Git commit history with meaningful incremental commits.
- Submit a text document containing the video link, GitHub URL, and index file information.
