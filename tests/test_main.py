from __future__ import annotations

from src.crawler import CrawledPage
from src.indexer import build_index, save_index
from src.main import handle_command
from src.search import SearchEngine


def test_load_command_loads_saved_index(tmp_path, capsys) -> None:
    path = tmp_path / "index.json"
    save_index(build_index([CrawledPage(url="https://example.com/", title="Example", text="hello world")]), path)
    engine = SearchEngine()

    should_exit = handle_command("load", engine, path)

    output = capsys.readouterr().out
    assert should_exit is False
    assert engine.is_loaded()
    assert "Loaded index" in output


def test_load_command_handles_missing_file(tmp_path, capsys) -> None:
    engine = SearchEngine()

    handle_command("load", engine, tmp_path / "missing.json")

    assert "Run 'build' first" in capsys.readouterr().out


def test_print_command_requires_loaded_index(capsys) -> None:
    handle_command("print good", SearchEngine())

    assert "No index loaded" in capsys.readouterr().out


def test_print_command_requires_word(capsys) -> None:
    handle_command("print", SearchEngine())

    assert "Usage: print <word>" in capsys.readouterr().out


def test_print_command_displays_postings(tmp_path, capsys) -> None:
    index = build_index([CrawledPage(url="https://example.com/", title="Example", text="good good")])
    engine = SearchEngine(index)

    handle_command("print good", engine, tmp_path / "index.json")

    output = capsys.readouterr().out
    assert "frequency=2" in output
    assert "positions=[0, 1]" in output


def test_print_command_displays_suggestions_for_missing_word(capsys) -> None:
    index = build_index([CrawledPage(url="https://example.com/", title="Example", text="friends")])
    engine = SearchEngine(index)

    handle_command("print frends", engine)

    output = capsys.readouterr().out
    assert "No entries found" in output
    assert "friends" in output


def test_find_command_requires_query(capsys) -> None:
    handle_command("find", SearchEngine())

    assert "Usage: find <query>" in capsys.readouterr().out


def test_find_command_displays_results(capsys) -> None:
    index = build_index([CrawledPage(url="https://example.com/", title="Example", text="good friends")])
    engine = SearchEngine(index)

    handle_command("find good friends", engine)

    output = capsys.readouterr().out
    assert "Found 1 page" in output
    assert "https://example.com/" in output
    assert "good friends" in output


def test_find_command_displays_suggestions(capsys) -> None:
    index = build_index([CrawledPage(url="https://example.com/", title="Example", text="friends")])
    engine = SearchEngine(index)

    handle_command("find frends", engine)

    output = capsys.readouterr().out
    assert "No pages found" in output
    assert "Suggestions for 'frends': friends" in output


def test_find_command_displays_no_results_for_no_candidates(capsys) -> None:
    index = build_index(
        [
            CrawledPage(url="https://example.com/1", title="One", text="good"),
            CrawledPage(url="https://example.com/2", title="Two", text="friends"),
        ]
    )
    engine = SearchEngine(index)

    handle_command("find good friends", engine)

    assert "No pages found" in capsys.readouterr().out


def test_help_unknown_and_exit_commands(capsys) -> None:
    engine = SearchEngine()

    assert handle_command("help", engine) is False
    assert handle_command("unknown", engine) is False
    assert handle_command("exit", engine) is True

    output = capsys.readouterr().out
    assert "Commands:" in output
    assert "Unknown command" in output
    assert "Goodbye" in output
