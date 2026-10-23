#!/usr/bin/env python3
"""Run all public-source collectors, lead intake, and metadata triage."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script: str, args: list[str]) -> None:
    command = [sys.executable, str(ROOT / "scripts" / script), *args]
    print("\n$ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--github-pages", type=int, default=1)
    parser.add_argument("--github-queries", type=int, default=26)
    parser.add_argument("--github-sort", choices=["relevance", "updated", "stars", "forks", "created", "both"], default="both")
    parser.add_argument("--huggingface-limit", type=int, default=1000)
    parser.add_argument("--huggingface-queries", type=int, default=12)
    parser.add_argument("--reset-github-results", action="store_true")
    args = parser.parse_args()

    sorts = ["relevance", "updated"] if args.github_sort == "both" else [args.github_sort]
    for index, sort in enumerate(sorts):
        github_args = ["--max-pages-per-query", str(args.github_pages), "--max-queries", str(args.github_queries), "--sort", sort]
        if args.reset_github_results and index == 0:
            github_args.append("--reset-github-results")
        run("harvest_github.py", github_args)
    run("harvest_huggingface_spaces.py", ["--limit-per-query", str(args.huggingface_limit), "--max-queries", str(args.huggingface_queries)])
    run("ingest_leads.py", [])
    run("ingest_evaluations.py", [])
    run("classify_catalog.py", [])


if __name__ == "__main__":
    main()
