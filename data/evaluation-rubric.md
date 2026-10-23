# Classification and evaluation rubric

This directory deliberately keeps unverified and low-quality leads. Discovery is broad; evaluation is evidence-based and may remain incomplete.

## Record states

| State | Meaning |
| --- | --- |
| `discovered` | Found through a public source or community lead; no canonical page check implied. |
| `canonical_page_checked` | A first-party product or project page was reachable on the recorded date. |
| `metadata_only` | Classification uses listing metadata, repository metadata, or the discovery post only. |
| `runtime_evaluated` | A reviewer followed the documented setup or product flow and saved reproducible evidence. |
| `needs_review` | A conflict, weak match, duplicate, likely non-app, or quality concern needs human triage. |
| `rejected` | Kept in the audit trail but excluded from the active app index with a reason. |

## Classification

Assign a primary category and any supported tags: coding, browser, computer-use, personal assistant, research, voice, workflow/automation, workplace, multi-agent, agent framework/platform, or other. A repository search term alone gives a provisional category. Record `classification_confidence` as low, medium, or high and link the evidence used. Do not infer a hosted product, working UI, model support, or user control from a repo name.

The automated metadata triage also records a `candidate_type`, `candidate_relevance_score`, `metadata_completeness_score`, and, where a source timestamp exists, `maintenance_signal_score`. These scores prioritize inspection. They do not evaluate app quality and do not replace the hands-on dimensions below.

The current triage marks a discovered record `needs_review` when its metadata-only relevance score is 0 or 1, its artifact type is unclear, or it has at least two observable low-signal flags. The reason is stored on the record and in the CSV. This deliberately leaves rough and questionable records visible.

## Evaluation dimensions

Score each dimension from 0 to 4 only when there is enough evidence; otherwise use `null` and explain what is missing. Include one or more evidence URLs per non-null score.

| Dimension | 0 | 2 | 4 |
| --- | --- | --- | --- |
| Agent capability | No demonstrated agent behavior | Some tool use or multi-step behavior documented | Repeatable, useful goal-directed execution demonstrated |
| App readiness | No usable interface or setup path found | Partial demo or setup with important gaps | A user can follow a documented path and complete a real task |
| Documentation | No usable instructions | Basic setup exists but important gaps remain | Clear, maintained setup and task guidance |
| Maintenance | Abandoned or broken signals | Mixed or intermittent maintenance | Recent, consistent maintenance with releases/issues handled |
| Safety and control | No relevant controls disclosed | Some limits or approvals described | Clear permissions, confirmations, failure handling, and data practices |
| User experience | No direct observation | Usable in a narrow flow with friction | Directly observed polished and accessible task flow |

Do not compute an overall quality score when most dimensions are unknown. Keep source reputation, popularity, stars, and marketing claims separate from product quality.

Community reviews belong in `data/evaluations.csv` and are merged by `scripts/ingest_evaluations.py`. A `doc_review` can score documentation or disclosed controls with links to the pages reviewed. A `runtime_task` must include the task attempted, result summary, and evidence URL. Reviews are observations with provenance, not a security certification; disagreement should remain visible in the evaluation history.

## Low-signal and “AI slop” screening

Retain questionable entries. Store observable flags such as `archived`, `no_description`, `no_license_declared`, `very_low_stars`, `no_recent_push`, `fork`, `tiny_repository`, `generic_description`, or `broken_canonical_link`. These are review prompts, not proof of low effort, copying, deception, or unsafe behavior. Use `needs_review` and a short reason for conclusions that require human judgment. Never label a project as slop solely because it is new, unpopular, or uses generated content.

## Provenance

For every record keep the source name, source URL or query, first-seen and last-seen timestamps, canonical URLs when found, checked date, and evaluator evidence. Preserve original text where legally and practically appropriate; otherwise retain a short excerpt and a stable link. Re-check stale links before describing a project as current.
