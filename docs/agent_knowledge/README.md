# Agent Knowledge Artifacts

These documents ground agents with shared terminology and platform/app context. They are referenced via the knowledge manifest (e.g., `ref:knowledge_manifest`) and must be versioned in artifact IDs (e.g., `artifact:odd_cod_fundamentals_v1`).

Structure:
- `core/` – robot-agnostic fundamentals used by all agents.
- `profiles/` – platform or application profiles with contextual guidance.

Agents read these as reference; the per-run ODD spec artifact remains the source of truth for constraints and axes.

Current artifacts:
- Core fundamentals: `core/ODD_COD_FUNDAMENTALS.md` (`artifact:odd_cod_fundamentals_v1`)
- Core sensor interpretation: `core/SENSOR_INTERPRETATION.md` (`artifact:sensor_interpretation_core_v1`)
- Robot profile (Go2): `profiles/ROBOT_GO2_PROFILE.md` (`artifact:robot_go2_profile_v1`)
