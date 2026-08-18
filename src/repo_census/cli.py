"""Command-line interface for repository census."""

import argparse
import os
import sys
from pathlib import Path
from typing import TextIO

from .collector import Collector
from .constants import DEFAULT_OWNERS
from .github import GitHubClient
from .persistence import CensusStore
from .reporting import build_report, render_json, render_markdown


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="repo-census")
    commands = result.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="collect a read-only GitHub census")
    collect.add_argument("--database", type=Path, default=Path("data/census.sqlite3"))
    collect.add_argument("--lookback-days", type=int, default=365)
    collect.add_argument(
        "--owner", action="append", choices=DEFAULT_OWNERS,
        help="collect only a configured owner; repeat for multiple owners",
    )
    report = commands.add_parser("report", help="render the collected census")
    report.add_argument("--database", type=Path, default=Path("data/census.sqlite3"))
    report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    report.add_argument("--output", type=Path)
    return result


def main(argv: list[str] | None = None, *, stdout: TextIO = sys.stdout) -> int:
    args = parser().parse_args(argv)
    if args.command == "collect":
        if args.lookback_days < 1:
            parser().error("--lookback-days must be positive")
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("error: GITHUB_TOKEN is required", file=sys.stderr)
            return 2
        with GitHubClient(token) as github, CensusStore(args.database) as store:
            run_id = Collector(github, store).collect(
                lookback_days=args.lookback_days,
                owners=tuple(args.owner) if args.owner else DEFAULT_OWNERS,
            )
        print(f"collection run {run_id} completed", file=stdout)
        return 0
    with CensusStore(args.database) as store:
        report = build_report(store)
    rendered = render_json(report) if args.format == "json" else render_markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="", file=stdout)
    return 0
