from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest

from codeguard.scanner.github_scanner import fetch_python_files


def make_client(monkeypatch, entries):
    client = MagicMock()
    repo = client.get_repo.return_value
    repo.private = False
    repo.default_branch = "main"
    repo.get_branch.return_value.commit.sha = "fixed-commit"
    repo.get_git_tree.return_value = NS(truncated=False, tree=entries)
    monkeypatch.setattr("codeguard.scanner.github_scanner.Github", lambda **kw: client)
    return client, repo


def test_limits_and_pinned_commit(monkeypatch):
    entries = [
        NS(type="blob", path="a.py", size=4),
        NS(type="blob", path="b.py", size=999),
        NS(type="blob", path="c.py", size=4),
        NS(type="blob", path="readme.md", size=4),
    ]
    client, repo = make_client(monkeypatch, entries)
    repo.get_contents.return_value.decoded_content = b"pass"
    scan = fetch_python_files("owner/repo", max_files=1, max_bytes=10)
    assert [f.path for f in scan.files] == ["a.py"]
    assert len(scan.skipped) == 2
    assert scan.commit == "fixed-commit"
    repo.get_contents.assert_called_once_with("a.py", ref="fixed-commit")
    client.close.assert_called_once()


@pytest.mark.parametrize("private, truncated", [(True, False), (False, True)])
def test_incomplete_or_private_repository_rejected(monkeypatch, private, truncated):
    client, repo = make_client(monkeypatch, [])
    repo.private = private
    repo.get_git_tree.return_value.truncated = truncated
    with pytest.raises(ValueError):
        fetch_python_files("owner/repo")
    client.close.assert_called_once()
