from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from codeguard.analysis.parser import AnalysisError
from codeguard.cli import choose_provider, main
from codeguard.scanner.github_scanner import ScanInput, SourceFile, repository_name


@pytest.mark.parametrize(
    "choice, provider", [("1", "openai"), ("2", "claude"), ("3", "kimi"), ("kimi", "kimi")]
)
def test_provider_menu(monkeypatch, choice, provider):
    monkeypatch.setattr("codeguard.cli.Prompt.ask", lambda *a, **kw: choice)
    assert choose_provider(Console()) == provider


@pytest.mark.parametrize("name", ["owner/repo", "https://github.com/owner/repo.git"])
def test_repository_names(name):
    assert repository_name(name) == "owner/repo"


@pytest.mark.parametrize("name", ["https://evil.com/owner/repo", "owner/repo/tree/main", "../repo"])
def test_invalid_repository_names(name):
    with pytest.raises(ValueError):
        repository_name(name)


def test_interactive_run_and_failed_report(monkeypatch, tmp_path):
    output = tmp_path / "report.txt"
    monkeypatch.setattr("sys.argv", ["codeguard", "--output", str(output)])
    monkeypatch.setattr("sys.stdin", NS(isatty=lambda: True))
    replies = iter(["2", "custom-claude", "owner/repo"])
    monkeypatch.setattr("codeguard.cli.Prompt.ask", lambda *a, **kw: next(replies))
    monkeypatch.setattr("codeguard.cli.load_environment", lambda: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(
        "codeguard.cli.fetch_python_files",
        lambda *a: ScanInput([SourceFile("a.py", "pass")], [], "abc123"),
    )
    analyzer = MagicMock()
    analyzer.analyze.side_effect = AnalysisError("invalid JSON")
    constructor = MagicMock(return_value=analyzer)
    monkeypatch.setattr("codeguard.cli.Analyzer", constructor)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert constructor.call_args.args[0].provider == "claude"
    assert constructor.call_args.args[0].model == "custom-claude"
    assert "Status: INCOMPLETE" in output.read_text()
    assert "invalid JSON" in output.read_text()
    analyzer.close.assert_called_once()


def test_noninteractive_requires_explicit_selection(monkeypatch):
    monkeypatch.setattr("sys.argv", ["codeguard", "owner/repo"])
    monkeypatch.setattr("sys.stdin", NS(isatty=lambda: False))
    monkeypatch.setattr("codeguard.cli.load_environment", lambda: None)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
