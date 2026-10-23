#!/usr/bin/env python3
"""Merge evidence-linked community reviews into catalog records."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from urllib.parse import urlsplit

from harvest_github import CSV_FIELDS, CSV, JSONL, csv_row

SCORES = ("agent_capability", "app_readiness", "documentation", "maintenance", "safety_and_control", "user_experience")


def parse_time(value: str) -> str:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("evaluated_at must include a timezone")
    return parsed.isoformat().replace("+00:00", "Z")


def main() -> int:
    with JSONL.open(encoding="utf-8") as f:
        records = {item["id"]: item for item in (json.loads(line) for line in f if line.strip())}
    events = 0
    with (JSONL.parent / "evaluations.csv").open(encoding="utf-8-sig", newline="") as f:
        for line, row in enumerate(csv.DictReader(f), start=2):
            if not row.get("id", "").strip():
                continue
            rid = row["id"].strip()
            if rid not in records:
                raise ValueError(f"data/evaluations.csv:{line}: unknown catalog id {rid}")
            mode = (row.get("evaluation_mode") or "").strip()
            if mode not in ("doc_review", "runtime_task"):
                raise ValueError(f"data/evaluations.csv:{line}: evaluation_mode must be doc_review or runtime_task")
            if not (row.get("reviewer_handle") or "").strip():
                raise ValueError(f"data/evaluations.csv:{line}: reviewer_handle is required")
            evaluated_at = parse_time(row.get("evaluated_at") or "")
            scores = {}
            for key in SCORES:
                raw = (row.get(key) or "").strip()
                if raw:
                    score = int(raw)
                    if not 0 <= score <= 4:
                        raise ValueError(f"data/evaluations.csv:{line}: {key} must be 0..4")
                    scores[key] = score
                else:
                    scores[key] = None
            evidence_urls = [url.strip() for url in (row.get("evidence_urls") or "").split(";") if url.strip()]
            for evidence_url in evidence_urls:
                parsed_url = urlsplit(evidence_url)
                if parsed_url.scheme.lower() not in ("http", "https") or not parsed_url.netloc:
                    raise ValueError(f"data/evaluations.csv:{line}: evidence URLs must use HTTP or HTTPS")
            if any(scores.values()) or any(score == 0 for score in scores.values()):
                if not evidence_urls:
                    raise ValueError(f"data/evaluations.csv:{line}: scored dimensions require evidence_urls")
            if mode == "runtime_task" and (not row.get("task_name") or not row.get("result_summary") or not evidence_urls):
                raise ValueError(f"data/evaluations.csv:{line}: runtime_task requires task_name, result_summary, and evidence_urls")

            notes = [row["notes"].strip()] if (row.get("notes") or "").strip() else []
            event = {
                "reviewer_handle": row["reviewer_handle"].strip(),
                "evaluated_at": evaluated_at,
                "evaluation_mode": mode,
                "app_version": (row.get("app_version") or "").strip() or None,
                "task_name": (row.get("task_name") or "").strip() or None,
                "result_summary": (row.get("result_summary") or "").strip() or None,
                **scores,
                "evidence_urls": evidence_urls,
                "notes": notes,
            }
            item = records[rid]
            history = item.setdefault("evaluation_history", [])
            event_key = (event["reviewer_handle"], event["evaluated_at"], event["evaluation_mode"], event["app_version"], event["task_name"])
            existing_index = next((i for i, prior in enumerate(history) if (
                prior.get("reviewer_handle"), prior.get("evaluated_at"), prior.get("evaluation_mode"),
                prior.get("app_version"), prior.get("task_name"),
            ) == event_key), None)
            if existing_index is None:
                history.append(event)
            else:
                history[existing_index] = event
            item["evaluation"] = {**scores, "evidence_urls": evidence_urls, "evaluated_at": evaluated_at, "notes": notes}
            if mode == "runtime_task":
                item["status"] = "runtime_evaluated"
                item["evidence_level"] = "runtime_evaluated"
            else:
                item["status"] = "canonical_page_checked"
                item["evidence_level"] = "canonical_page_checked"
            events += 1

    ordered = sorted(records.values(), key=lambda item: (item.get("category", ""), item.get("name", "").casefold(), item["id"]))
    with JSONL.open("w", encoding="utf-8", newline="\n") as f:
        for item in ordered:
            f.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    with CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_row(item) for item in ordered)
    print(f"Merged {events} evidence-linked evaluations into {len(records)} records")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"evaluation ingest failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
