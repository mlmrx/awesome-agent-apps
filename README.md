# Awesome Agent Apps

A source-linked directory of AI agent applications, projects, and discovery leads people can inspect, try, or run themselves.

This project is an evidence ledger, not a winners list. We collect candidates broadly across GitHub, the web, and X, including unfinished projects, clones, abandoned experiments, low-effort launches, and records that may turn out not to be agent apps. We classify what each source actually supports and evaluate quality only when evidence exists. A discovery record is not an endorsement or proof that an app works.

**Starter examples checked:** 2026-10-22. The broad candidate index has separate discovery and evidence labels; a search match does not mean its page was opened, app was installed, or workflow was run.

## Curated examples

These examples have a canonical product or project page checked. The full, much larger candidate index is in [`apps.csv`](apps.csv) and [`data/apps.jsonl`](data/apps.jsonl). The index intentionally retains low-signal records for review.

## Directory

### Coding and building software

| App | What it does | Product | Code | X |
| --- | --- | --- | --- | --- |
| [Cline](https://cline.bot/) | Coding agent available as a desktop app, cloud service, IDE extension, CLI, and SDK. | [Website](https://cline.bot/) | [GitHub](https://github.com/cline/cline) | — |
| [OpenCode](https://opencode.ai/) | Open-source coding agent for the terminal, IDEs, and desktop, with multi-session support. | [Website](https://opencode.ai/) | [GitHub](https://github.com/anomalyco/opencode) | — |
| [OpenHands](https://www.openhands.dev/) | Agent platform for software development, available through a hosted cloud service or self-hosting. | [Website](https://www.openhands.dev/) | [GitHub](https://github.com/OpenHands/OpenHands) | — |
| [Replit Agent](https://replit.com/products/agent) | Build, refine, and deploy apps by describing the result you want in Replit. | [Website](https://replit.com/products/agent) | — | — |

### Personal and local agents

| App | What it does | Product | Code | X |
| --- | --- | --- | --- | --- |
| [AnythingLLM](https://anythingllm.com/) | On-device AI workspace for documents, web research, background jobs, custom skills, and meeting notes. | [Website](https://anythingllm.com/) | [GitHub](https://github.com/Mintplex-Labs/anything-llm) | — |
| [Hermes Agent](https://hermes-agent.nousresearch.com/) | Personal agent with a desktop app, terminal setup, messaging integrations, persistent memory, and scheduled tasks. | [Website](https://hermes-agent.nousresearch.com/) | [GitHub](https://github.com/NousResearch/hermes-agent) | — |
| [OpenClaw](https://openclaw.ai/) | Open-source personal assistant designed to act across devices and messaging platforms. | [Website](https://openclaw.ai/) | [GitHub](https://github.com/openclaw/openclaw) | [X showcase](https://x.com/steipete/status/2013089335629799607?lang=en) |
| [Open Interpreter](https://www.openinterpreter.com/) | Local coding agent for open models. | [Website](https://www.openinterpreter.com/) | [GitHub](https://github.com/OpenInterpreter/open-interpreter) | — |

### Browser agents

| App | What it does | Product | Code | X |
| --- | --- | --- | --- | --- |
| [Nanobrowser](https://nanobrowser.ai/) | Open-source browser extension agent that performs web tasks in the browser you are already signed into. | [Website](https://nanobrowser.ai/) | [GitHub](https://github.com/nanobrowser/nanobrowser) | — |

### Research and workplace knowledge

| App | What it does | Product | Code | X |
| --- | --- | --- | --- | --- |
| [GPT Researcher](https://github.com/assafelovic/gpt-researcher) | Open-source agent for deep research across the web and other data sources. | [GitHub](https://github.com/assafelovic/gpt-researcher) | [GitHub](https://github.com/assafelovic/gpt-researcher) | — |
| [Onyx](https://onyx.app/) | AI knowledge platform that connects workplace sources and provides context to people and agents. | [Website](https://onyx.app/) | [GitHub](https://github.com/onyx-dot-app/onyx) | — |
| [Spine AI](https://www.getspine.ai/) | Cloud and local-first products coordinate multiple agents for research, analysis, and software work. | [Website](https://www.getspine.ai/) | — | [X discussion](https://x.com/hasantoxr/status/2033594775077851371) |

### Work agents and automation

| App | What it does | Product | Code | X |
| --- | --- | --- | --- | --- |
| [Dify](https://dify.ai/) | Build agentic workflows and AI apps, then deploy them on Dify Cloud or self-hosted infrastructure. | [Website](https://dify.ai/) | [GitHub](https://github.com/langgenius/dify) | — |
| [Lindy](https://www.lindy.ai/) | Hosted work assistant with integrations, routines, memory, a Chrome extension, and meeting tools. | [Website](https://www.lindy.ai/) | — | — |
| [n8n](https://n8n.io/ai-agents/) | Fair-code workflow automation platform with AI agent capabilities and cloud or self-hosted deployment. | [Website](https://n8n.io/ai-agents/) | [GitHub](https://github.com/n8n-io/n8n) | — |

## How to read this list

- **Product** links to the app or its official product page.
- **Code** links to the project's public source repository when one is available.
- **X** links to a public post that helped surface the project. Social posts are discovery leads; the product description is checked against the project's own page or repository.
- A checked date means the linked canonical page was opened on that date. It does not mean the app was installed, run, or independently evaluated.

The machine-readable directory is [`apps.csv`](apps.csv); the richer JSONL records preserve discovery provenance and evaluation fields. The latest [catalog counts](data/catalog-stats.json) distinguish discoveries, low-signal records, and hands-on evaluations. The initial manually checked examples are in [`data/curated-seed.csv`](data/curated-seed.csv). Community web and X leads can be added through [`data/leads.csv`](data/leads.csv). See the [classification and evaluation rubric](data/evaluation-rubric.md), [record schema](schemas/app.schema.json), and [GitHub](data/sources/github-search.json), [Hugging Face Spaces](data/sources/huggingface-search.json), [web](data/sources/web-search.json), and [X](data/sources/x-search.json) discovery manifests.

## Refreshing the catalog

With Python 3.11 and GitHub CLI authenticated, run `python scripts/refresh_catalog.py`. It queries public GitHub repositories, public Hugging Face Spaces, merges community web/X leads and evidence-linked app reviews, and rebuilds metadata triage and counts. Add review rows to [`data/evaluations.csv`](data/evaluations.csv) using the [evaluation rubric](data/evaluation-rubric.md); runtime scores require a named task, result summary, and evidence URL. The GitHub Actions workflow can also be run manually from the Actions tab. Web search and X posts remain link-based leads in `data/leads.csv` so each discovery keeps its original public URL.

### Evidence labels

- `discovered`: a source matched a discovery query; the app itself has not been checked.
- `needs_review`: automated triage found weak matches or multiple observable warning signals; the record stays in the index.
- `canonical_page_checked`: a product or project page was reachable when checked.
- `metadata_only`: the classification uses public listing metadata only.
- `runtime_evaluated`: someone recorded a repeatable hands-on evaluation with evidence links.

Automated low-signal flags are observable metadata (for example, an archived repository or no declared license). They are screening clues, not a declaration that a project is “AI slop.” Keep questionable records and mark why they need review; do not silently remove them.

This directory is not an endorsement, security audit, or guarantee that a product remains available. Search coverage is incomplete and query-dependent. GitHub metadata cannot establish that software works, is safe, or is a complete app. Features, pricing, access, and licensing can change; check the linked project before relying on those details.

## License

Our original directory text, annotations, and compilation are dedicated to the public domain under [CC0 1.0 Universal](LICENSE). Source-supplied names, descriptions, tags, and metadata remain attributable to their publishers; linked projects, marks, and software remain subject to their respective owners' terms.
