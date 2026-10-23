#!/usr/bin/env python3
"""Harvest broad GitHub repository-search candidates into the catalog.

Requires GitHub CLI (`gh`) authenticated to github.com. Search matches are
unverified discovery leads. The script stores metadata and provenance, not code.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/sources/github-search.json"
JSONL = ROOT / "data/apps.jsonl"
CSV = ROOT / "apps.csv"
CSV_FIELDS = [
    "id", "name", "category", "summary", "website_url", "repository_url",
    "x_discovery_url", "source", "source_url", "source_query", "first_seen",
    "last_seen", "source_updated_at", "stars", "forks", "archived", "license",
    "language", "topics", "status", "evidence_level", "classification_confidence",
    "candidate_type", "candidate_relevance_score", "metadata_completeness_score", "maintenance_signal_score",
    "low_signal_flags", "review_reason", "discovery_count", "agent_capability", "app_readiness", "documentation",
    "maintenance", "safety_and_control", "user_experience", "evaluation_notes",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_http_url(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None
    return candidate if parsed.scheme.lower() in ("http", "https") and parsed.netloc else None


def low_signal_flags(repo: dict, today: datetime) -> list[str]:
    flags = []
    if repo.get("archived"):
        flags.append("archived")
    if not (repo.get("description") or "").strip():
        flags.append("no_description")
    if not repo.get("license"):
        flags.append("no_license_declared")
    if repo.get("stargazers_count", 0) < 10:
        flags.append("very_low_stars")
    if repo.get("fork"):
        flags.append("fork")
    if repo.get("size", 0) < 20:
        flags.append("tiny_repository")
    pushed = repo.get("pushed_at")
    if pushed:
        try:
            age = today - datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            if age.days > 365:
                flags.append("no_recent_push")
        except ValueError:
            pass
    desc = (repo.get("description") or "").lower()
    generic = ("best ai agent", "the ultimate ai agent", "revolutionary ai", "your personal ai")
    if desc and len(desc) < 36 and any(p in desc for p in generic):
        flags.append("generic_description")
    return flags


def category_for(repo: dict, query_category: str) -> tuple[str, str]:
    text = " ".join([
        repo.get("name") or "", repo.get("description") or "",
        " ".join(repo.get("topics") or []), query_category,
    ]).lower()
    rules = [
        ("Coding agents", ["coding agent", "code agent", "software engineer", "coding", "programming"]),
        ("Browser agents", ["browser agent", "web agent", "browser automation", "web automation"]),
        ("Computer-use agents", ["computer use", "computer-use", "desktop automation", "gui agent"]),
        ("Voice agents", ["voice agent", "voice assistant", "speech agent", "phone agent"]),
        ("Research agents", ["research agent", "deep research", "web research"]),
        ("Multi-agent systems", ["multi-agent", "multi agent", "agent swarm", "agent teams"]),
        ("Personal assistants", ["personal assistant", "ai assistant", "personal agent"]),
        ("Workflow agents", ["workflow agent", "automation agent", "workflow automation"]),
    ]
    for category, needles in rules:
        if any(needle in text for needle in needles):
            return category, "medium" if query_category.lower() in text else "low"
    return query_category, "low"


def normalize(repo: dict, query: str, query_category: str, collected_at: str) -> dict:
    full_name = repo["full_name"]
    website = safe_http_url(repo.get("homepage"))
    license_info = repo.get("license") or {}
    category, confidence = category_for(repo, query_category)
    return {
        "id": "github:" + full_name.lower(),
        "name": repo.get("name") or full_name.rsplit("/", 1)[-1],
        "category": category,
        "summary": repo.get("description"),
        "website_url": website,
        "repository_url": repo.get("html_url"),
        "x_discovery_url": None,
        "source": "github_repository_search",
        "source_url": repo.get("html_url"),
        "source_query": query,
        "discoveries": [{"source": "github_repository_search", "source_url": repo.get("html_url"),
                         "query": query, "first_seen": collected_at, "last_seen": collected_at}],
        "first_seen": collected_at,
        "last_seen": collected_at,
        "source_updated_at": repo.get("pushed_at"),
        "status": "discovered",
        "evidence_level": "metadata_only",
        "classification_confidence": confidence,
        "candidate_type": "unclassified",
        "metadata_assessment": {},
        "tags": repo.get("topics") or [],
        "metadata": {
            "full_name": full_name,
            "visibility": repo.get("visibility") or "public",
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "open_issues": repo.get("open_issues_count", 0),
            "archived": bool(repo.get("archived")),
            "fork": bool(repo.get("fork")),
            "disabled": bool(repo.get("disabled")),
            "size_kb": repo.get("size", 0),
            "language": repo.get("language"),
            "license": license_info.get("spdx_id") or license_info.get("key"),
            "created_at": repo.get("created_at"),
            "updated_at": repo.get("updated_at"),
            "default_branch": repo.get("default_branch"),
        },
        "low_signal_flags": low_signal_flags(repo, datetime.now(timezone.utc)),
        "review_reason": None,
        "evaluation": {
            "agent_capability": None,
            "app_readiness": None,
            "documentation": None,
            "maintenance": None,
            "safety_and_control": None,
            "user_experience": None,
            "evidence_urls": [],
            "evaluated_at": None,
            "notes": ["Metadata-only discovery; product evaluation has not been performed."],
        },
    }


def read_existing() -> dict[str, dict]:
    records: dict[str, dict] = {}
    if JSONL.exists():
        with JSONL.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    records[row["id"]] = row
    elif CSV.exists():
        with CSV.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if not row.get("repository_url"):
                    continue
                rid = "github:" + row["repository_url"].rstrip("/").split("github.com/")[-1].lower()
                stamp = (row.get("checked_on") or now()) + "T00:00:00Z"
                records[rid] = {
                    "id": rid, "name": row["name"], "category": row["category"],
                    "summary": row.get("summary"), "website_url": row.get("product_url") or None,
                    "repository_url": row.get("repository_url"), "x_discovery_url": row.get("x_discovery_url") or None,
                    "source": "curated_seed", "source_url": row.get("repository_url"),
                    "source_query": None, "first_seen": stamp, "last_seen": stamp,
                    "source_updated_at": None, "status": "canonical_page_checked",
                    "evidence_level": "canonical_page_checked", "classification_confidence": "high",
                    "tags": [], "metadata": {"form_factor": row.get("form_factor")},
                    "low_signal_flags": [], "review_reason": None,
                    "evaluation": {"agent_capability": None, "app_readiness": None, "documentation": None,
                        "maintenance": None, "safety_and_control": None, "user_experience": None,
                        "evidence_urls": [], "evaluated_at": None,
                        "notes": ["Canonical link checked during initial curation; no runtime evaluation recorded."]},
                }
    return records


def search(query: str, page: int, per_page: int, sort: str) -> dict:
    args = ["gh", "api", "-X", "GET", "/search/repositories", "-f", f"q={query} is:public",
            "-f", f"per_page={per_page}", "-f", f"page={page}"]
    if sort != "relevance":
        args.extend(["-f", f"sort={sort}", "-f", "order=desc"])
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return json.loads(proc.stdout)


def csv_row(item: dict) -> dict:
    meta = item.get("metadata", {})
    evaluation = item.get("evaluation", {})
    return {
        "id": item["id"], "name": item["name"], "category": item["category"],
        "summary": item.get("summary") or "", "website_url": item.get("website_url") or "",
        "repository_url": item.get("repository_url") or "", "x_discovery_url": item.get("x_discovery_url") or "",
        "source": item["source"], "source_url": item["source_url"], "source_query": item.get("source_query") or "",
        "first_seen": item["first_seen"], "last_seen": item["last_seen"], "source_updated_at": item.get("source_updated_at") or "",
        "stars": meta.get("stars", ""), "forks": meta.get("forks", ""), "archived": meta.get("archived", ""),
        "license": meta.get("license") or "", "language": meta.get("language") or "",
        "topics": ";".join(item.get("tags", [])), "status": item["status"], "evidence_level": item["evidence_level"],
        "classification_confidence": item.get("classification_confidence", ""),
        "candidate_type": item.get("candidate_type", ""),
        "candidate_relevance_score": item.get("metadata_assessment", {}).get("candidate_relevance_score", ""),
        "metadata_completeness_score": item.get("metadata_assessment", {}).get("metadata_completeness_score", ""),
        "maintenance_signal_score": item.get("metadata_assessment", {}).get("maintenance_signal_score", ""),
        "low_signal_flags": ";".join(item.get("low_signal_flags", [])),
        "review_reason": item.get("review_reason") or "",
        "discovery_count": len(item.get("discoveries", [])),
        "agent_capability": evaluation.get("agent_capability", ""), "app_readiness": evaluation.get("app_readiness", ""),
        "documentation": evaluation.get("documentation", ""), "maintenance": evaluation.get("maintenance", ""),
        "safety_and_control": evaluation.get("safety_and_control", ""), "user_experience": evaluation.get("user_experience", ""),
        "evaluation_notes": " | ".join(evaluation.get("notes", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-pages-per-query", type=int, default=1)
    parser.add_argument("--per-page", type=int, default=100)
    parser.add_argument("--max-queries", type=int, default=26)
    parser.add_argument("--sort", choices=["relevance", "updated", "stars", "forks", "created"], default="relevance")
    parser.add_argument("--reset-github-results", action="store_true", help="Drop prior search-only GitHub records before rebuilding public-only results.")
    parser.add_argument("--limit", type=int, default=0, help="Optional total records per query; 0 means full pages.")
    args = parser.parse_args()
    if not 1 <= args.per_page <= 100 or args.max_pages_per_query < 1:
        parser.error("per-page must be 1..100 and max-pages-per-query must be positive")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    queries = manifest["queries"][:args.max_queries]
    collected_at = now()
    records = read_existing()
    if args.reset_github_results:
        seed_file = ROOT / "data/curated-seed.csv"
        curated_ids = set()
        if seed_file.exists():
            with seed_file.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    repo_url = row.get("repository_url") or ""
                    if "github.com/" in repo_url:
                        curated_ids.add("github:" + repo_url.rstrip("/").split("github.com/")[-1].lower())
        before = len(records)
        records = {rid: item for rid, item in records.items()
                   if item.get("source") != "github_repository_search" or rid in curated_ids}
        print(f"Reset removed {before - len(records)} prior GitHub search-only records; public curated seeds retained.", flush=True)
    hits = 0
    stop = False
    for index, spec in enumerate(queries, start=1):
        query = spec["query"] + " is:public" + (f" sort:{args.sort}" if args.sort != "relevance" else "")
        for page in range(1, args.max_pages_per_query + 1):
            try:
                payload = search(spec["query"], page, args.per_page, args.sort)
            except RuntimeError as exc:
                print(f"Search stopped at query {index}: {exc}", file=sys.stderr, flush=True)
                stop = True
                break
            items = payload.get("items", [])
            if not items:
                break
            if args.limit:
                remaining = args.limit - (page - 1) * args.per_page
                items = items[:max(0, remaining)]
            for repo in items:
                if repo.get("visibility") not in (None, "public"):
                    continue
                item = normalize(repo, query, spec["category"], collected_at)
                old = records.get(item["id"])
                if old:
                    old["last_seen"] = collected_at
                    old["source"] = "github_repository_search"
                    old["source_query"] = query
                    old["source_url"] = item["source_url"]
                    old["source_updated_at"] = item["source_updated_at"]
                    old["metadata"] = item["metadata"]
                    old["low_signal_flags"] = item["low_signal_flags"]
                    discoveries = old.setdefault("discoveries", [])
                    discovery = next((d for d in discoveries if d.get("source") == item["source"] and d.get("source_url") == item["source_url"] and d.get("query") == query), None)
                    if discovery:
                        discovery["last_seen"] = collected_at
                    else:
                        discoveries.append({"source": item["source"], "source_url": item["source_url"], "query": query,
                                            "first_seen": collected_at, "last_seen": collected_at})
                    if old.get("status") == "discovered":
                        old["category"] = item["category"]
                        old["classification_confidence"] = item["classification_confidence"]
                    records[item["id"]] = old
                else:
                    records[item["id"]] = item
                hits += 1
            print(f"[{index}/{len(queries)}] {query}: {len(items)} records; {payload.get('total_count', '?')} matches", flush=True)
            if len(items) < args.per_page or (args.limit and page * args.per_page >= args.limit):
                break
        if stop:
            break

    JSONL.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records.values(), key=lambda r: (r.get("category", ""), r.get("name", "").casefold(), r["id"]))
    with JSONL.open("w", encoding="utf-8", newline="\n") as f:
        for row in ordered:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    with CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_row(row) for row in ordered)
    print(f"Saved {len(ordered)} unique records after {hits} search hits to {JSONL.relative_to(ROOT)} and {CSV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"harvest failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
