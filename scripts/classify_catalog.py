#!/usr/bin/env python3
"""Apply reproducible metadata-only triage; never invent hands-on product scores."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from harvest_github import CSV_FIELDS, CSV, JSONL, csv_row


def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def classify(item: dict, measured_at: datetime) -> None:
    meta = item.get("metadata", {})
    tags = item.get("tags", [])
    name = item.get("name") or ""
    summary = item.get("summary") or ""
    query = item.get("source_query") or ""
    text = " ".join([name, summary, " ".join(tags), query, item.get("category", "")]).lower()
    evidence_text = " ".join([name, summary, " ".join(tags)]).lower()

    if any(term in text for term in ("benchmark", "leaderboard", "eval suite", "research paper", "arxiv", "dataset")):
        candidate_type = "research_or_benchmark"
    elif any(term in text for term in ("template", "tutorial", "course", "example", "starter", "prototype", "demo", "showcase", "sample app")):
        candidate_type = "demo_or_template"
    elif any(term in text for term in ("framework", "sdk", "library", "toolkit", "mcp server", "orchestration framework", "agent runtime")):
        candidate_type = "framework_or_sdk"
    elif any(term in evidence_text for term in ("agent", "agentic", "assistant", "copilot")):
        candidate_type = "app_candidate"
    else:
        candidate_type = "unclear"

    relevance_reasons = []
    core_terms = ("agent", "agentic", "autonomous", "assistant", "copilot")
    if any(term in name.lower() for term in core_terms):
        relevance_reasons.append("agent-related term in name")
    if any(term in " ".join(tags).lower() for term in core_terms):
        relevance_reasons.append("agent-related tag")
    if any(term in summary.lower() for term in core_terms):
        relevance_reasons.append("agent-related term in description")
    if not relevance_reasons and any(term in query.lower() for term in core_terms):
        relevance_reasons.append("matched an agent-related discovery query only")

    relevance = 0
    if relevance_reasons:
        relevance = 1 if relevance_reasons == ["matched an agent-related discovery query only"] else 2
    if "agent-related term in description" in relevance_reasons and any(
        term in summary.lower() for term in ("tool", "plan", "multi-step", "workflow", "browse", "execute", "task")
    ):
        relevance = 3
    if relevance == 2 and candidate_type in ("framework_or_sdk", "research_or_benchmark", "demo_or_template"):
        # Relevant to the agent ecosystem, but may not itself be an end-user app.
        relevance = 1

    if item.get("source") == "github_repository_search":
        completeness = sum(bool(value) for value in [
            summary.strip(), item.get("website_url"), meta.get("license"), tags,
        ])
    elif item.get("source") == "huggingface_spaces_search":
        completeness = sum(bool(value) for value in [meta.get("sdk"), tags, meta.get("likes") is not None, name])
    else:
        completeness = sum(bool(value) for value in [summary.strip(), item.get("website_url"), item.get("repository_url"), item.get("x_discovery_url")])

    pushed = item.get("source_updated_at") or meta.get("pushed_at")
    maintenance = None
    if pushed:
        try:
            age_days = max(0, (measured_at - datetime.fromisoformat(pushed.replace("Z", "+00:00"))).days)
            maintenance = 4 if age_days <= 30 else 3 if age_days <= 90 else 2 if age_days <= 365 else 1 if age_days <= 730 else 0
            if meta.get("archived"):
                maintenance = 0
        except ValueError:
            maintenance = None

    item["candidate_type"] = candidate_type
    item["metadata_assessment"] = {
        "candidate_relevance_score": relevance,
        "metadata_completeness_score": min(4, completeness),
        "maintenance_signal_score": maintenance,
        "candidate_relevance_reasons": relevance_reasons,
        "measured_at": iso(measured_at),
        "notes": [
            "Metadata triage only. Relevance and completeness are not product quality scores.",
            "Hands-on capability, readiness, documentation, safety, and usability remain unscored until inspected.",
        ],
    }
    if item.get("status") == "discovered" and (relevance <= 1 or candidate_type == "unclear" or len(item.get("low_signal_flags", [])) >= 2):
        item["status"] = "needs_review"
        reasons = []
        if relevance <= 1:
            reasons.append("weak agent-app metadata match")
        if candidate_type == "unclear":
            reasons.append("unclear artifact type")
        if len(item.get("low_signal_flags", [])) >= 2:
            reasons.append("multiple observable low-signal flags")
        item["review_reason"] = "Automatic metadata triage: " + "; ".join(reasons) + ". This is a review prompt, not a quality verdict."


def main() -> None:
    measured_at = now()
    records = []
    with JSONL.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                classify(item, measured_at)
                records.append(item)
    records.sort(key=lambda item: (item.get("category", ""), item.get("name", "").casefold(), item["id"]))
    with JSONL.open("w", encoding="utf-8", newline="\n") as f:
        for item in records:
            f.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    with CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_row(item) for item in records)
    source_counts = Counter(item.get("source", "unknown") for item in records)
    discovery_channel_counts = Counter(ref.get("source", "unknown") for item in records for ref in item.get("discoveries", []))
    category_counts = Counter(item.get("category", "Unclassified") for item in records)
    stats = {
        "generated_at": iso(measured_at),
        "record_count": len(records),
        "unique_id_count": len({item["id"] for item in records}),
        "source_counts": dict(sorted(source_counts.items())),
        "discovery_channel_counts": dict(sorted(discovery_channel_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "discovered_count": sum(item.get("status") == "discovered" for item in records),
        "needs_review_count": sum(item.get("status") == "needs_review" for item in records),
        "canonical_page_checked_count": sum(item.get("status") == "canonical_page_checked" for item in records),
        "records_with_low_signal_flags": sum(bool(item.get("low_signal_flags")) for item in records),
        "records_with_x_discovery_url": sum(bool(item.get("x_discovery_url")) for item in records),
        "metadata_triaged_count": len(records),
        "hands_on_evaluated_count": sum(item.get("status") == "runtime_evaluated" for item in records),
    }
    (JSONL.parent / "catalog-stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f"Classified {len(records)} records: {dict(Counter(item['candidate_type'] for item in records))}")
    print(f"Metadata assessment timestamp: {iso(measured_at)}; hands-on evaluations scored: {sum(item.get('status') == 'runtime_evaluated' for item in records)}")


if __name__ == "__main__":
    main()
