#!/usr/bin/env python3
"""Harvest public Hugging Face Spaces search results as app discovery candidates."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/sources/huggingface-search.json"
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


def get_spaces(query: str, limit: int) -> list[dict]:
    url = "https://huggingface.co/api/spaces?" + urlencode({"search": query, "limit": limit})
    request = Request(url, headers={"User-Agent": "awesome-agent-apps-catalog/1.0"})
    with urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    if not isinstance(payload, list):
        raise RuntimeError(f"unexpected Spaces API response for query {query!r}")
    return payload


def read_existing() -> dict[str, dict]:
    records = {}
    if JSONL.exists():
        with JSONL.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    records[item["id"]] = item
    elif CSV.exists():
        with CSV.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if not row.get("repository_url"):
                    continue
                rid = "github:" + row["repository_url"].rstrip("/").split("github.com/")[-1].lower()
                stamp = (row.get("checked_on") or now()) + "T00:00:00Z"
                records[rid] = {
                    "id": rid, "name": row["name"], "category": row["category"], "summary": row.get("summary"),
                    "website_url": row.get("product_url") or None, "repository_url": row.get("repository_url"),
                    "x_discovery_url": row.get("x_discovery_url") or None, "source": "curated_seed",
                    "source_url": row.get("repository_url"), "source_query": None, "first_seen": stamp,
                    "last_seen": stamp, "source_updated_at": None, "status": "canonical_page_checked",
                    "evidence_level": "canonical_page_checked", "classification_confidence": "high", "tags": [],
                    "metadata": {"form_factor": row.get("form_factor")}, "low_signal_flags": [], "review_reason": None,
                    "evaluation": {"agent_capability": None, "app_readiness": None, "documentation": None,
                        "maintenance": None, "safety_and_control": None, "user_experience": None,
                        "evidence_urls": [], "evaluated_at": None, "notes": ["Canonical page checked; no runtime evaluation recorded."]},
                }
    return records


def as_record(space: dict, query: str, category: str, collected_at: str) -> dict:
    name = space.get("id") or "unknown-space"
    tags = space.get("tags") or []
    flags = []
    if space.get("likes", 0) < 5:
        flags.append("very_low_likes")
    if space.get("sdk") == "static":
        flags.append("static_space")
    if not any(tag.startswith("license:") for tag in tags):
        flags.append("no_license_tag")
    page = "https://huggingface.co/spaces/" + name
    return {
        "id": "huggingface-space:" + name.lower(),
        "name": name,
        "category": category,
        "summary": None,
        "website_url": page,
        "repository_url": None,
        "x_discovery_url": None,
        "source": "huggingface_spaces_search",
        "source_url": page,
        "source_query": query,
        "discoveries": [{"source": "huggingface_spaces_search", "source_url": page,
                         "query": query, "first_seen": collected_at, "last_seen": collected_at}],
        "first_seen": collected_at,
        "last_seen": collected_at,
        "source_updated_at": space.get("lastModified"),
        "status": "discovered",
        "evidence_level": "metadata_only",
        "classification_confidence": "low",
        "candidate_type": "unclassified",
        "metadata_assessment": {},
        "tags": tags,
        "metadata": {
            "space_id": name,
            "display_name": name.rsplit("/", 1)[-1],
            "likes": space.get("likes", 0),
            "trending_score": space.get("trendingScore"),
            "sdk": space.get("sdk"),
            "created_at": space.get("createdAt"),
            "private": bool(space.get("private")),
            "source_platform": "Hugging Face Spaces",
        },
        "low_signal_flags": flags,
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
            "notes": ["Search listing only; inspect the Space before evaluating its app behavior."],
        },
    }


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


def save(records: dict[str, dict]) -> None:
    ordered = sorted(records.values(), key=lambda r: (r.get("category", ""), r.get("name", "").casefold(), r["id"]))
    JSONL.parent.mkdir(parents=True, exist_ok=True)
    with JSONL.open("w", encoding="utf-8", newline="\n") as f:
        for row in ordered:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    with CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_row(row) for row in ordered)
    print(f"Saved {len(ordered)} unique records")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit-per-query", type=int, default=1000)
    parser.add_argument("--max-queries", type=int, default=12)
    parser.add_argument("--delay-seconds", type=float, default=0.25)
    args = parser.parse_args()
    if args.limit_per_query < 1 or args.max_queries < 1:
        parser.error("limit-per-query and max-queries must be positive")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    queries = manifest["queries"][:args.max_queries]
    records = read_existing()
    collected_at = now()
    for index, spec in enumerate(queries, start=1):
        try:
            spaces = get_spaces(spec["query"], args.limit_per_query)
        except Exception as exc:
            print(f"Stopping at query {index}: {exc}", file=sys.stderr)
            break
        for space in spaces:
            if space.get("private"):
                continue
            item = as_record(space, spec["query"], spec["category"], collected_at)
            old = records.get(item["id"])
            if old:
                old["last_seen"] = collected_at
                old["source_query"] = spec["query"]
                old["metadata"] = item["metadata"]
                old["low_signal_flags"] = item["low_signal_flags"]
                discoveries = old.setdefault("discoveries", [])
                discovery = next((d for d in discoveries if d.get("source") == item["source"] and d.get("source_url") == item["source_url"] and d.get("query") == spec["query"]), None)
                if discovery:
                    discovery["last_seen"] = collected_at
                else:
                    discoveries.append({"source": item["source"], "source_url": item["source_url"], "query": spec["query"],
                                        "first_seen": collected_at, "last_seen": collected_at})
                records[item["id"]] = old
            else:
                records[item["id"]] = item
        print(f"[{index}/{len(queries)}] {spec['query']}: {len(spaces)} records", flush=True)
        save(records)
        time.sleep(args.delay_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
