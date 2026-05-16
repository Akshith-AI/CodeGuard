"""Retrieve bounded Python files from public GitHub repositories."""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from github import Auth, Github


@dataclass(frozen=True)
class SourceFile:
    path: str
    source: str


@dataclass
class ScanInput:
    files: list[SourceFile]
    skipped: list[str]
    commit: str


def repository_name(value: str) -> str:
    value = value.strip()
    if "://" in value:
        parsed = urlparse(value)
        if parsed.scheme != "https" or parsed.hostname != "github.com":
            raise ValueError("Use owner/repo or an https://github.com/owner/repo URL.")
        value = parsed.path.strip("/")
    value = value.removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", value) or value.split("/")[
        -1
    ] in {".", ".."}:
        raise ValueError("Repository must be owner/repo or its GitHub URL.")
    return value


def fetch_python_files(
    repository: str,
    token: str | None = None,
    max_files: int = 20,
    max_bytes: int = 50000,
) -> ScanInput:
    name = repository_name(repository)
    client = Github(auth=Auth.Token(token) if token else None, timeout=30)
    try:
        repo = client.get_repo(name)
        if repo.private:
            raise ValueError("CodeGuard currently supports public repositories only.")
        commit = repo.get_branch(repo.default_branch).commit.sha
        tree = repo.get_git_tree(commit, recursive=True)
        if tree.truncated:
            raise ValueError("GitHub returned a truncated file tree; scan a smaller repository.")
        files, skipped = [], []
        for entry in sorted(tree.tree, key=lambda item: item.path):
            if entry.type != "blob" or not entry.path.endswith(".py"):
                continue
            if len(files) >= max_files:
                skipped.append(f"{entry.path}: file limit reached")
                continue
            if entry.size is not None and entry.size > max_bytes:
                skipped.append(f"{entry.path}: larger than {max_bytes} bytes")
                continue
            content = repo.get_contents(entry.path, ref=commit).decoded_content
            if len(content) > max_bytes:
                skipped.append(f"{entry.path}: larger than {max_bytes} bytes")
                continue
            try:
                source = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                skipped.append(f"{entry.path}: unsupported encoding (expected UTF-8)")
                continue
            if source.strip():
                files.append(SourceFile(entry.path, source))
        return ScanInput(files, skipped, commit)
    finally:
        client.close()
