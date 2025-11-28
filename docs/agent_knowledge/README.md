# Agent Knowledge Artifacts

These documents ground agents with shared terminology and platform/app context. They are referenced via the knowledge manifest (e.g., `ref:knowledge_manifest`) and must be versioned in artifact IDs (e.g., `artifact:odd_cod_fundamentals_v1`).

Structure:
- `core/` – robot-agnostic fundamentals used by all agents.
- `profiles/` – platform or application profiles with contextual guidance.

Agents read these as reference; the per-run ODD spec artifact remains the source of truth for constraints and axes.

## Current Artifacts

| Artifact | File | Version | Artifact ID |
|----------|------|---------|-------------|
| Core fundamentals | `core/ODD_COD_FUNDAMENTALS.md` | v1.0.0 | `artifact:odd_cod_fundamentals_v1` |
| Sensor interpretation | `core/SENSOR_INTERPRETATION.md` | v1.3.0 | `artifact:sensor_interpretation_core_v1` |
| Robot profile (Go2) | `profiles/ROBOT_GO2_PROFILE.md` | v1.1.0 | `artifact:robot_go2_profile_v1` |

## Versioning Policy

**When to increment versions:**

| Change Type | Version Bump | Examples |
|-------------|--------------|----------|
| **Major (vX.0.0)** | Breaking changes to structure or semantics | Rename sections, remove guidance, change interpretation rules |
| **Minor (v0.X.0)** | New content that agents should know about | Add new sections (e.g., self-hit guidance), new patterns |
| **Patch (v0.0.X)** | Clarifications, typo fixes, wording improvements | Fix typos, improve phrasing, add examples |

**Guidelines:**
- Update the version number in the doc header when making changes
- Add a changelog entry at the top of the doc (below version)
- Artifact IDs in the manifest use major version only (e.g., `_v1`) for stability
- Knowledge seeding is enabled by default; use `--no-knowledge` to disable
