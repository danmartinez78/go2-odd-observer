# ODD & Agent Improvements Plan

Synthesizes pending changes across ODD definition, agent/tool prompts, and collision risk handling. Built on:
- `docs/PROPOSED_ODD_UPDATE.md` (ODD relaxation for realistic indoor use)
- `docs/RESULTS_REVIEW_20251129.md` (production run findings)
- `docs/COLLISION_RISK_REINTRODUCTION.md` (advisory risk signal plan)

## 1) ODD Definition Updates
- **Environment/obstacles:** Explicitly allow furniture-dense residential/commercial spaces; close proximity normal unless paths are blocked.
- **Motion:** Allow quick reactions up to ~10 m/s²; brief abrupt maneuvers for avoidance; still disallow racing/sustained aggressive motion.
- **Terrain:** Permit gentle ramps (<15°), thresholds, and typical residential flooring (hardwood, tile, low-pile carpet). Keep stairs/steep/outdoor excluded. Use BEV + camera fusion for terrain assessment.
- **Human/animal proximity:** Add explicit constraint—close approach by humans or animals (~0.5-1m while navigating) = OOD.
- **Collision:** NOT an ODD axis. Collision detection (binary + risk) is an **advisory safety signal** entirely outside ODD/COD computation. ODD definition should NOT mention collision thresholds.
- **Action:** Update `DEFAULT_ODD_DESCRIPTION` in runners/workflow. Remove any collision references from ODD; add human/animal proximity; soften terrain to allow carpet.

## 2) Agent/Tool Prompt Improvements
- **Perception:** Ground obstacle density in BEV %; add numeric justification; reduce camera-driven inflation. Terrain assessment via BEV + camera fusion: roughness from height/roughness BEV, surface type from camera, cross-check for consistency. Stairs: output `{present, direction: up|down|unknown, proximity_m, risk: low|med|high, justification}`; only OUT_ODD if (a) ODD forbids stairs outright, or (b) downward stairs intersect path at <1.5m. Humans/animals with proximity distance estimate. Traversability derived from density+roughness+surface with justification.
- **Motion:** Expose `is_stationary` with confidence and window list; clearer roll/pitch reporting (max + windows + rationale).
- **Collision:** Evidence gating for collisions (IMU + BEV/path + visual); clustering to avoid duplicate ramp taps; rationale per event. Output both `collision_detected` (bool) and `collision_risk` (0-1) as **advisory signals only**—neither affects ODD/COD verdict. Motion-state gating: require nonzero motion or strong IMU evidence; downgrade to info when stationary.
- **Evaluator:** Be verbose: per-axis values vs limits, roll/pitch details, human/animal proximity, density/roughness %, COD vs ODD distance, stability, and a "Why" section. Consume artifacts/agent_outputs directly. Collision (binary + risk) is reported as advisory context but does NOT influence ODD/COD verdict. **Cross-agent consistency check:** if Motion reports stationary but Collision reports multiple events, flag as suspicious and require strong evidence (IMU spike + visual contact) before including in advisory.
- **Report:** Use artifacts/agent_outputs; add warnings if missing. Include advisory collision risk and strong rationale for collisions/roll/pitch/humans/stairs/density.

## 3) Collision Signals (Fully Advisory)
- Both `collision_detected` (binary) and `collision_risk` (0-1) are **advisory safety signals**, entirely outside ODD/COD computation.
- Collision Agent outputs both; Evaluator and Report surface them for awareness but they do NOT affect IN_ODD/BOUNDARY/OUT_ODD verdict.
- Rationale: Collisions are safety events to be reported, not operational domain characteristics. A robot can be IN_ODD and still have a collision (user error, unexpected obstacle, etc.).
- See `docs/COLLISION_RISK_REINTRODUCTION.md` for implementation details.

## 4) Artifact/Reporting Reliability (needs verification)
- Persist artifacts to disk and hydrate `agent_outputs`; report builder fallback to artifacts.
- **Status:** Implemented but batch runs still show "No perception/motion/collision data available" warnings. Investigate batch-mode artifact hydration path.
- **Action:** Verify `agent_outputs` population in batch mode; check report builder reads artifacts correctly.

## 5) ODD Definition Centralization
- Currently `DEFAULT_ODD_DESCRIPTION` is duplicated in 3+ files (`run_odd_analysis.py`, `run_odd_batch_analysis.py`, `generate_all_test_reports.py`).
- **Recommendation:** Centralize in `odd_agents/workflow.py` or a dedicated `odd_agents/odd_definition.py`; other scripts import from there.
- **Benefit:** Single source of truth; version changes in one place.

## Execution Plan (feature branch)
1) Update DEFAULT_ODD_DESCRIPTION in workflow/runners with relaxed indoor spec + human/animal proximity.
2) Apply prompt updates (perception, motion, collision, evaluator/report).
3) Add collision risk advisory output and reporting.
4) Re-run targeted scenarios (e.g., real_173813, real_174604, real_174321, sim_1) and validate against `docs/SCENARIO_DESCRIPTIONS.md` expectations.
