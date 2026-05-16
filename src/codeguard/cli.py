"""Interactive provider selection and repository security scanning."""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from anthropic import APIError as AnthropicAPIError
from github import GithubException
from openai import APIError as OpenAIAPIError
from rich.console import Console
from rich.prompt import Prompt

from . import __version__
from .analysis.analyzer import Analyzer
from .analysis.parser import AnalysisError
from .config import PROVIDERS, default_model, get_config, load_environment
from .reporting.terminal import display_findings
from .reporting.text_report import write_report
from .scanner.github_scanner import fetch_python_files, repository_name


def choose_provider(console: Console) -> str:
    console.print("Choose a model provider:")
    names = list(PROVIDERS)
    for number, provider in enumerate(names, 1):
        console.print(
            f"  {number}. {PROVIDERS[provider][0]} ({default_model(provider)})", markup=False
        )
    choice = Prompt.ask("Provider", choices=["1", "2", "3", *names], console=console)
    return names[int(choice) - 1] if choice.isdigit() else choice


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Must be a positive integer.")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI security scanner for public GitHub repositories."
    )
    parser.add_argument("repository", nargs="?", help="owner/repo or GitHub repository URL")
    parser.add_argument("--provider", choices=list(PROVIDERS), help="Skip the provider menu")
    parser.add_argument("--model", help="Override the selected provider's model ID")
    parser.add_argument("--output", type=Path, help="Text report destination")
    parser.add_argument("--max-files", type=positive_int, default=20)
    parser.add_argument("--max-file-bytes", type=positive_int, default=50000)
    parser.add_argument("--version", action="version", version=f"CodeGuard {__version__}")
    args = parser.parse_args()
    load_environment()
    console = Console()
    if not sys.stdin.isatty() and (not args.provider or not args.repository):
        parser.error(
            "Use --provider and a repository when running without an interactive terminal."
        )
    analyzer = None
    try:
        provider = args.provider or choose_provider(console)
        model = args.model
        if sys.stdin.isatty() and not args.provider and model is None:
            model = Prompt.ask("Model ID", default=default_model(provider), console=console)
        config = get_config(provider, model)
        repository = repository_name(
            args.repository or Prompt.ask("GitHub repository", console=console)
        )
        console.print(
            f"Scanning {repository} with {PROVIDERS[provider][0]} / {config.model}", markup=False
        )
        console.print("Python source is sent to the selected provider for analysis.")
        scan = fetch_python_files(
            repository,
            os.getenv("GITHUB_TOKEN") or None,
            args.max_files,
            args.max_file_bytes,
        )
        if not scan.files:
            raise ValueError("No eligible Python files found. Check the repository and size limit.")
        analyzer = Analyzer(config)
        findings, failures = [], []
        scanned = 0
        for file in scan.files:
            console.print(f"Analyzing {file.path}...", markup=False)
            try:
                findings.extend(analyzer.analyze(file.path, file.source))
                scanned += 1
            except AnalysisError as exc:
                failures.append(f"{file.path}: {exc}")
            except (OpenAIAPIError, AnthropicAPIError) as exc:
                # Do not print provider response bodies, which may contain source or secrets.
                code = getattr(exc, "status_code", None)
                detail = f"HTTP {code}" if code else type(exc).__name__
                failures.append(f"{file.path}: provider request failed ({detail})")
                # Auth, quota, or connection failures are unlikely to improve for later files.
                if code in (401, 403, 429) or code is None:
                    remaining = scan.files[scan.files.index(file) + 1 :]
                    failures.extend(
                        f"{item.path}: not analyzed after provider failure" for item in remaining
                    )
                    break
        display_findings(console, findings)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = args.output or Path("reports") / f"{repository.replace('/', '-')}-{stamp}.txt"
        write_report(
            output,
            repository,
            scan.commit,
            provider,
            config.model,
            findings,
            scanned,
            scan.skipped,
            failures,
        )
        console.print(f"Analyzed {scanned} file(s); {len(findings)} potential finding(s).")
        for message in scan.skipped:
            console.print(f"Skipped: {message}", style="yellow", markup=False)
        for message in failures:
            console.print(f"Failed: {message}", style="red", markup=False)
        console.print(f"Report saved to {output}", markup=False)
        if failures or scan.skipped:
            console.print("Scan coverage is incomplete.", style="yellow")
            raise SystemExit(1)
    except (ValueError, OSError) as exc:
        console.print(f"Error: {exc}", style="red", markup=False)
        raise SystemExit(1) from exc
    except GithubException as exc:
        console.print(
            f"GitHub request failed (HTTP {exc.status}). Check access and rate limits.", style="red"
        )
        raise SystemExit(1) from exc
    except (KeyboardInterrupt, EOFError):
        console.print("Scan cancelled.")
        raise SystemExit(130) from None
    finally:
        if analyzer is not None:
            analyzer.close()
