"""Command-line entry point for CodeGuard."""

import argparse

from . import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI-powered security scanner for public GitHub repositories (scaffold)."
    )
    parser.add_argument("--version", action="version", version=f"CodeGuard {__version__}")
    parser.parse_args()
    parser.print_help()
