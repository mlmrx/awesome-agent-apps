# Contributing

Thanks for helping keep Awesome Agent Apps useful and current.

## What belongs in the candidate ledger

Add candidates broadly when a public source connects them to AI agents. Apps, builders, SDKs, frameworks, demos, abandoned experiments, rough launches, clones, and false positives may all be retained for triage. Use the category and status fields to distinguish what they are. A discovery is not an endorsement or proof that a project works.

## Sources and descriptions

For a quick community contribution, add a row to [`data/leads.csv`](data/leads.csv) with the app name, source (`web_search`, `x_post`, or `community_submission`), and public source URL, then run `python scripts/ingest_leads.py`. Include canonical site and repository URLs when available. Keep a short summary in your own words and preserve uncertainty. Do not add private messages or personal data.

An X post or web search result can be a discovery lead. Keep its original public URL, and leave the record `discovered` until a canonical product or project page is checked. Do not treat post text, stars, or marketing claims as proof of behavior, safety, or quality.

## Keep the files in sync

1. Add or update a lead in `data/leads.csv` or refresh one of the machine-readable sources.
2. Keep `data/curated-seed.csv` for the small manually checked set shown in the README; the generated root `apps.csv` and `data/apps.jsonl` are the broad candidate index.
3. Record the source query, URL, and date. Mark runtime evaluation only after following a repeatable product flow and saving evidence links.
4. Preserve low-signal entries with objective flags and a review reason. Do not delete an entry only because it looks rough, unpopular, or abandoned.
5. Do not paste full X posts, private messages, or long copyrighted descriptions into the catalog. Store short summaries and links.

Please include source links in pull requests so maintainers can review the entry quickly.
