# Versioning Guide

A single place to understand how we track versions across agents, prompts, knowledge, data, and reports.

## What We Version
- **Agents & prompts:** Pipeline agents and their tool prompts carry semantic versions (the badges you see on the site). Source: `odd_agents/agent_prompts.py` and agent/tool modules.
- **Tools:** Function tools mirror agent versions when their prompts or behavior change (see `odd_agents/tools/`).
- **Knowledge & ODD docs:** Core knowledge, robot profiles, and overlays are treated as revisioned artifacts. Keep filenames stable; record revisions and dates in the doc headers.
- **Data:** Processed datasets are versioned in `data/DATA_VERSIONS.md` (production, test, regeneration parameters).
- **Reports & runs:** Reports include the pipeline/agent versions and the scenario/data version used (visible in report metadata and archived results).

## Naming & Bumping
- **Agents/Tools:** `vMAJOR.MINOR.PATCH` (e.g., PerceptionAgent v7.4.0). Bump when prompts/logic change in ways that affect outputs. Minor for behavior/prompt improvements, patch for small wording/stability tweaks.
- **Knowledge:** Update the revision/date in the doc header and summarize changes (what changed, why).
- **Data:** Follow `data/DATA_VERSIONS.md` (`{source}_{id}_v{n}`) and log processing parameters.
- **Reports:** Keep the version stamps (pipeline + agent versions + data version) in the generated artifacts.

## Where Versions Surface
- **UI:** Badges on the homepage and architecture page.
- **Artifacts:** `full_result.json`, `executive_summary.json`, and HTML reports include pipeline/agent versions and scenario/data identifiers.
- **Docs:** This guide (overall), `data/DATA_VERSIONS.md` (data), knowledge doc headers (knowledge).

## How to Update
1) Change code/prompt/knowledge/data.
2) Bump the relevant version number (agent/tool prompt file, knowledge doc header, or data manifest).
3) Log the change (short note in HISTORY/RESULTS where appropriate; data changes go in `data/DATA_VERSIONS.md`).
4) Ensure reports pick up the new versions (rerun workflows).

## Quick Checklist
- Agent or tool prompt changed → bump agent/tool version.
- Knowledge doc edited → update its revision/date.
- Data regenerated → add entry to `data/DATA_VERSIONS.md`.
- Reports shipped → confirm they include pipeline/agent/data versions in metadata.
