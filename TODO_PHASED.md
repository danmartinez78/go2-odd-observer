# ODD Observer Roadmap (Phased, Consolidated)

This document reorganizes the existing TODO into clear phases while preserving all content. The original `TODO.md` remains unchanged.

## Status Snapshot
- Phase 1.4.5 complete (HTML reports v2.0, knowledge layer in place).
- Agent Evaluation refresh completed (2025-02-24) with rubric-based ADK suites.
- Current decision point: Memory/consolidation (Phase 2.2) vs. open issues (token accounting, sporadic window failures).

## Phase 0: Data Source Discovery ✅
- Bagfile audits, topic sampling, findings documented (`data/development/bagfile_audit/PHASE0_FINDINGS.md`).
- Key discovery: no reliable velocity; IMU primary, camera/LiDAR needed for odometry.

## Phase 1: Architecture Refactor ✅ (v1.4.4 complete)
- 1.1 BEV Data Enhancement: auto-crop BEVs, 3 channels (occupancy/height/roughness), data reorg.
- 1.2 Collision Agent Rework: binary collision detection, schema updates, thresholds validated.
- 1.3 COD Agent Redesign: simplified ODD schema, semantic context, decoupled measurement.
- 1.4 Agent Versioning & Telemetry: prompt/metadata registry, catalog, workflow metadata capture.

## Phase 1.4.5: HTML Reports + Terminology ✅
- HTML Generator v2.0, production reports, index updates (ODD/COD explainer, badges, cards).
- Terminology fixes: COD = Current Operating Domain; boundary definition; evaluator/report prompt updates.
- Known issues noted here: token accounting bug; Getting Started guide needs update.

## Phase 1.5: Knowledge Layer ✅
- Agent knowledge docs: fundamentals, sensor interpretation, Go2 profile.
- Prompts wired to `ref:knowledge_manifest`; workflow records `knowledge_refs`; seeding helper `scripts/seed_knowledge_manifest.py`.

## Phase 1.6: Test Updates (Planned/Partial)
- Goal: Update unit/eval tests for consolidated agents.
- Planned: refresh wrappers to latest API, ensure scenarios point to `data/test/sim/sim_test_w010_w011`, add missing agent test files if any remain.

## Phase 1.7: Full Production Run (Planned)
- Run on all `sim_1_0` chunks (100 windows). Priority: HIGH.

## Phase 1.x: Kaggle Capstone Prep (Ongoing)
- Align with competition rubric; add quantitative eval metrics, failure analysis, future work roadmap.
- Demo artifacts: screen recording, notebook walkthrough, static reports, README showcase.

## Phase 2: Performance & Memory (Planned)
- 2.0 Performance Optimization (LOW): visual/LiDAR odometry, tool splitting; benchmarking.
- 2.1 Real Data Validation (HIGH): test on real robot data (post-Phase 1 architecture).
- 2.2 Memory & Knowledge System (NEXT UP): define memory schema (`ref:*`, `global:odd_profile:*`, `case:run:*`), build consolidator agent, have Evaluator/Report read memory for cross-scenario context, choose persistent backend (e.g., VertexAiMemoryBankService) with cost/toggle, add comparative reasoning (“COD distance higher than typical”).
- 2.3 Visual & LiDAR Odometry (NEW!): compute odometry from camera/LiDAR; validate drift/accuracy; enrich motion JSON; update motion tool to consume odometry.
- 2.4 Performance Benchmarking: batch latency/tokens, model comparisons (flash/flash-lite/pro), target 30-50% token reduction without accuracy loss.

## Phase 3: Evaluation Framework (Planned)
- Ground truth dataset (hand-labeled IN_ODD/BOUNDARY/OUT_ODD, axis violations).
- Evaluator setup (Gemini 3 Pro), rubrics (per-window accuracy, violation precision/recall, severity alignment, COD region accuracy).
- Baseline measurement, iterative prompt/threshold tuning to >95% per-window accuracy, <10% false positives.

## Phase 4: Model Testing & Report Updates (Planned)
- Model tests: Gemini 3 Pro on COD/Evaluator; keep flash-lite for Perception/Motion.
- Report enhancements: per-window compliance table, severity visualization, COD region summary, window distribution chart, investigation flags, executive summary, remove collision risk charts, add collision events display, example reports per severity.

## Cross-Cutting Known Issues (Open)
- Token accounting bug: tool-level `genai.Client` calls not tracked by ADK; fix by capturing usage in tools or returning usage to workflow; image token costs missing.
- Sporadic window analysis failures: intermittent tool-agent errors; investigate via isolated agent tests, add logging, compare isolated vs pipeline for rate-limit/timeouts/load issues.

## Agent Evaluation Refresh (2025-11-27) ✅
- Rubric-based configs for Perception/Motion/Collision/Evaluator/Report/ODD Spec; trajectory checks removed.
- Fixtures for evaluator/report (`tests/evaluation/fixtures/eval_report`); results log (`tests/evaluation/RESULTS.md`).
- Docs updated (`docs/guides/AGENT_EVALUATION.md`, README link, docs/index.html callout).
- Caveat: report hallucinations omitted; evaluator hallucinations threshold relaxed to 0.5 until ADK grounds function_call outputs better.

## Documentation Backlog (Open)
- Update Getting Started for Phase 1.4.5.
- Agent deep dives (OddSpec, Perception, Motion, Collision, Evaluator, Report).
- Architecture overview diagram; data formats (window structure, JSON schemas); cost/performance benchmarks.
- GitHub Pages content expansion (mirrors above).

## Additional Tasks / Tech Debt
- Metadata & Telemetry: design done in `docs/METADATA_DESIGN.md`; implement callbacks/hybrid, integrate into pipeline, surface in reports, enable A/B tracking.
- Deferred: Plotly charts in reports (broken rendering), BEV ground filtering validation (reprocess data, compare metrics).
- Code quality: type hints, logging consistency, remove legacy `odd_cod/` if unused.
- Nice-to-haves: web UI, automated report pipeline, real-time monitoring, historical trends, compliance PDF export, meta-analysis tools.
- Future research: triage/pre-analysis agent for adaptive sampling.

## Completed Tasks (Snapshot)
- Real robot validation (6 collections, 270 windows; standardized test sets; validated motion/collision/ODD compliance).
- Production workflow scripts (manual + batch runners, outputs, naming conventions, archiving).
- IMU-based motion analysis (jerk/smoothness, multimodal hints, updated schema).

## Phase Priorities (if unclear, clarify)
- High: Phase 1.7 full production run; Phase 2.1 real data validation; resolve token accounting bug; investigate sporadic failures.
- Next-up decision: start Phase 2.2 memory vs. finish open issues above.
