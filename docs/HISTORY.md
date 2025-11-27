# Project History & Improvements

Chronological log of notable features and improvements. Add entries when features merge to keep a clear trail beyond TODOs.

## 2025-??-?? (in progress)
- Added core knowledge reference doc `docs/agent_knowledge/core/ODD_COD_FUNDAMENTALS.md` (robot-agnostic fundamentals + optional profiles/manifest hook).
- Added sensor interpretation reference `docs/agent_knowledge/core/SENSOR_INTERPRETATION.md` (BEV, camera, IMU, collision cues; profiles allowed).
- Added knowledge manifest helpers `odd_agents/knowledge.py` to keep reference docs modular (fundamentals + optional robot/app/ODD + sensors overlays) and to seed memory keys.
- Wired knowledge manifest references into Perception (v7.5.0), Motion (v7.4.0), Collision (v7.4.0), OddSpec (v6.2.0), Evaluator (v5.1.0), and Report (v9.2.0) prompts for shared grounding without duplicating text.
- Added `scripts/seed_knowledge_manifest.py` helper to seed knowledge manifest + section pointers into session memory; pipeline now records knowledge_refs in metadata and displays them in the post-run summary.
- Added Go2 robot profile doc `docs/agent_knowledge/profiles/ROBOT_GO2_PROFILE.md` (v1.0.0) and runner flags to seed knowledge manifest in-process (defaults to fundamentals + sensors + Go2 profile). Workflow accepts an optional knowledge_seed and records knowledge_refs.
