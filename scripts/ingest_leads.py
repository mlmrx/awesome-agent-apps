#!/usr/bin/env python3
"""Merge community web/X discoveries from data/leads.csv into the catalog."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from harvest_github import CSV_FIELDS, CSV as CATALOG_CSV, JSONL, csv_row

ROOT = Path(__file__).resolve().parents[1]
LEADS = ROOT / "data/leads.csv"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        return None
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", ""))


def record_id(row: dict[str, str]) -> str:
    repo = clean_url(row.get("repository_url"))
    if repo and "github.com/" in repo:
        return "github:" + repo.split("github.com/", 1)[1].lower()
    identity = clean_url(row.get("website_url")) or clean_url(row.get("x_discovery_url")) or clean_url(row.get("source_url"))
    return "web:" + hashlib.sha256((identity or row.get("name", "")).encode("utf-8")).hexdigest()[:20]


def read_records() -> dict[str, dict]:
    records = {}
    if JSONL.exists():
        with JSONL.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    records[item["id"]] = item
    return records


def find_match(records: dict[str, dict], rid: str, row: dict[str, str]) -> tuple[str, dict | None]:
    if rid in records:
        return rid, records[rid]
    urls = {clean_url(row.get(k)) for k in ("website_url", "repository_url") if row.get(k)}
    urls.discard(None)
    for existing_id, item in records.items():
        if urls.intersection({clean_url(item.get(k)) for k in ("website_url", "repository_url") if item.get(k)}):
            return existing_id, item
    return rid, None


def discover(item: dict, source: str, source_url: str, query: str | None, stamp: str) -> None:
    refs = item.setdefault("discoveries", [])
    match = next((r for r in refs if r.get("source") == source and r.get("source_url") == source_url and r.get("query") == query), None)
    if match:
        match["last_seen"] = stamp
        match["query"] = query
    else:
        refs.append({"source": source, "source_url": source_url, "query": query, "first_seen": stamp, "last_seen": stamp})


def ingest_curated_seed(records: dict[str, dict]) -> None:
    seed_file = ROOT / "data/curated-seed.csv"
    with seed_file.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rid = record_id({
                "name": row["name"], "repository_url": row.get("repository_url"),
                "website_url": row.get("product_url"), "x_discovery_url": row.get("x_discovery_url"),
            })
            checked = row.get("checked_on") or ""
            stamp = checked + "T00:00:00Z" if checked else now()
            source_url = clean_url(row.get("repository_url")) or clean_url(row.get("product_url")) or clean_url(row.get("x_discovery_url"))
            rid, item = find_match(records, rid, {
                "website_url": row.get("product_url"), "repository_url": row.get("repository_url"),
            })
            if item is None:
                item = {
                    "id": rid, "name": row["name"], "category": row["category"], "summary": row.get("summary") or None,
                    "website_url": clean_url(row.get("product_url")), "repository_url": clean_url(row.get("repository_url")),
                    "x_discovery_url": clean_url(row.get("x_discovery_url")),
                    "source": "github_repository" if row.get("repository_url") else "web_product_page",
                    "source_url": source_url, "source_query": None, "first_seen": stamp, "last_seen": stamp,
                    "source_updated_at": None, "status": "canonical_page_checked", "evidence_level": "canonical_page_checked",
                    "classification_confidence": "high", "tags": [], "metadata": {"form_factor": row.get("form_factor")},
                    "low_signal_flags": [], "review_reason": None,
                    "evaluation": {"agent_capability": None, "app_readiness": None, "documentation": None,
                        "maintenance": None, "safety_and_control": None, "user_experience": None,
                        "evidence_urls": [], "evaluated_at": None,
                        "notes": ["Canonical page was checked during initial curation; no runtime evaluation recorded."]},
                }
            else:
                if not item.get("website_url"):
                    item["website_url"] = clean_url(row.get("product_url"))
                if not item.get("x_discovery_url"):
                    item["x_discovery_url"] = clean_url(row.get("x_discovery_url"))
                item.setdefault("metadata", {}).setdefault("form_factor", row.get("form_factor"))
            if clean_url(row.get("repository_url")):
                discover(item, "github_repository", clean_url(row.get("repository_url")), None, stamp)
            if clean_url(row.get("product_url")):
                discover(item, "web_product_page", clean_url(row.get("product_url")), None, stamp)
            records[rid] = item


def main() -> None:
    records = read_records()
    for item in records.values():
        for key in ("website_url", "repository_url", "x_discovery_url"):
            if item.get(key):
                item[key] = clean_url(item[key])
        if item.get("source_url"):
            item["source_url"] = clean_url(item["source_url"]) or item["source_url"]
        grouped = {}
        for ref in item.get("discoveries", []):
            if ref.get("source_url"):
                ref["source_url"] = clean_url(ref["source_url"]) or ref["source_url"]
            key = (ref.get("source"), ref.get("source_url"), ref.get("query"))
            existing = grouped.get(key)
            if existing:
                existing["first_seen"] = min(existing.get("first_seen", ""), ref.get("first_seen", ""))
                existing["last_seen"] = max(existing.get("last_seen", ""), ref.get("last_seen", ""))
            else:
                grouped[key] = ref
        if grouped:
            item["discoveries"] = list(grouped.values())
    ingest_curated_seed(records)
    stamp = now()
    for item in records.values():
        if not item.get("discoveries") and item.get("source_url"):
            discover(item, item.get("source", "unknown"), item["source_url"], item.get("source_query"), item.get("first_seen", stamp))
    with LEADS.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if not row.get("name") or not row.get("source_url"):
                continue
            rid = record_id(row)
            source = (row.get("source") or "community_submission").strip().lower()
            url = clean_url(row.get("source_url")) or row["source_url"].strip()
            rid, item = find_match(records, rid, row)
            if item is None:
                status = (row.get("status") or "discovered").strip()
                item = {
                    "id": rid,
                    "name": row["name"].strip(),
                    "category": (row.get("category") or "Unclassified").strip(),
                    "summary": (row.get("summary") or "").strip() or None,
                    "website_url": clean_url(row.get("website_url")),
                    "repository_url": clean_url(row.get("repository_url")),
                    "x_discovery_url": clean_url(row.get("x_discovery_url")),
                    "source": source,
                    "source_url": url,
                    "source_query": (row.get("source_query") or "").strip() or None,
                    "first_seen": stamp,
                    "last_seen": stamp,
                    "source_updated_at": None,
                    "status": status,
                    "evidence_level": "canonical_page_checked" if status == "canonical_page_checked" else "discovery_only",
                    "classification_confidence": "low",
                    "tags": [],
                    "metadata": {},
                    "low_signal_flags": [],
                    "review_reason": (row.get("review_reason") or "").strip() or None,
                    "discoveries": [],
                    "evaluation": {
                        "agent_capability": None, "app_readiness": None, "documentation": None,
                        "maintenance": None, "safety_and_control": None, "user_experience": None,
                        "evidence_urls": [], "evaluated_at": None,
                        "notes": ["Community/web/X discovery lead; not independently evaluated."],
                    },
                }
            else:
                item["last_seen"] = stamp
                for key in ("website_url", "repository_url", "x_discovery_url"):
                    candidate = clean_url(row.get(key))
                    if candidate and not item.get(key):
                        item[key] = candidate
                if row.get("review_reason"):
                    item["review_reason"] = row["review_reason"].strip()
                if row.get("status") == "canonical_page_checked" and item.get("status") != "runtime_evaluated":
                    item["status"] = "canonical_page_checked"
                    item["evidence_level"] = "canonical_page_checked"
            if not item.get("discoveries") and item.get("source_url"):
                discover(item, item.get("source", "unknown"), item["source_url"], item.get("source_query"), item.get("first_seen", stamp))
            discover(item, source, url, (row.get("source_query") or "").strip() or None, stamp)
            if item.get("website_url"):
                discover(item, "web_product_page", item["website_url"], None, stamp)
            if item.get("repository_url") and "github.com/" in item["repository_url"]:
                discover(item, "github_repository", item["repository_url"], None, stamp)
            if item.get("x_discovery_url"):
                discover(item, "x_post", item["x_discovery_url"], (row.get("source_query") or "").strip() or None, stamp)
            records[rid] = item

    ordered = sorted(records.values(), key=lambda r: (r.get("category", ""), r.get("name", "").casefold(), r["id"]))
    JSONL.parent.mkdir(parents=True, exist_ok=True)
    with JSONL.open("w", encoding="utf-8", newline="\n") as f:
        for item in ordered:
            f.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    with CATALOG_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_row(item) for item in ordered)
    print(f"Catalog now has {len(ordered)} unique records")


if __name__ == "__main__":
    main()
