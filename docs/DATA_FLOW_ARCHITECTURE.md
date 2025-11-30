# Data Flow Architecture

## Overview

This document describes the complete data flow through the ODD analysis pipeline, including:
- What data sources each component reads
- What artifacts are saved by tools (full detail for post-processing)
- What gets propagated to session state via `output_key` (summaries for downstream)
- What downstream agents consume

---

## Universal Pattern

**All agents with tools follow the same pattern:**

```
┌─────────────────────────────────────────────────────────────────┐
│  TOOL: Detailed analysis → ARTIFACT (full detail)              │
│        Returns full data to agent                               │
│                                                                 │
│  AGENT: Temporal/higher-order analysis → SESSION (summary)     │
│         Synthesizes insights for downstream agents              │
└─────────────────────────────────────────────────────────────────┘
```

**Why this pattern?**
- **Artifacts** preserve full detail for debugging, audit trails, and post-processing
- **Session state** carries compact summaries to minimize downstream token usage
- **Uniform** - every tool-using agent follows the same contract

**Key Principles:**
1. Tools MUST save artifacts with complete analysis results
2. Tools MUST return full data to the agent (not just `{status: saved}`)
3. Agents MUST output JSON summaries for `output_key` to capture to session
4. Session summaries include issues, alerts, anomalies - the "meta analysis"

---

## ASCII Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SCENARIO DATA (on disk)                           │
│  data/test/sim_2win/                                                        │
│  ├── motion_*.json     (IMU timeseries)                                     │
│  ├── cam_*.png         (camera frames)                                      │
│  └── bev_*.png         (occupancy, height, roughness)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
════════════════════════════════════╪══════════════════════════════════════════
                              ODD SPEC AGENT
════════════════════════════════════╪══════════════════════════════════════════
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  save_odd_spec_tool (Python)                                                │
│  ├── INPUT: 9 lists of axis definitions from LLM                            │
│  ├── BUILDS: Full structured ODD spec                                       │
│  ├── SAVES TO ARTIFACT: odd_spec_full.json  ◄── FULL DETAIL                 │
│  │   {environment: {categorical:[], numeric:[], boolean:[]},                │
│  │    actors: {...}, ego: {...}}                                            │
│  └── RETURNS TO AGENT: Full spec (agent summarizes for session)             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  OddSpecAgent (LLM)                                                         │
│  ├── Calls save_odd_spec_tool → receives full spec                          │
│  ├── Synthesizes summary: key axes, limits, constraints                     │
│  └── output_key="temp:odd_spec" ──▶ SESSION STATE  ◄── SUMMARY              │
│      (downstream: axis names, relevant limits - NOT full spec)              │
└─────────────────────────────────────────────────────────────────────────────┘

════════════════════════════════════╪══════════════════════════════════════════
                        SENSOR AGENTS (Batch Processing → Temporal Analysis)
════════════════════════════════════╪══════════════════════════════════════════
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  analyze_all_perception_tool (Python) - SINGLE CALL, ALL WINDOWS            │
│  ├── INPUT: window_ids[], odd_context from agent                            │
│  ├── READS: cam_*.png, bev_*.png for ALL windows from disk                  │
│  ├── ANALYZES: Each window - observations, issues, anomalies                │
│  ├── SAVES TO ARTIFACT: perception_output.json  ◄── ALL WINDOWS             │
│  │   {per_window: [{window_id, observations, issues, alerts}...]}           │
│  └── RETURNS TO AGENT: Full per-window results for all windows              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  PerceptionAgent (LLM)                                                      │
│  ├── Reads {temp:odd_spec} for ODD context                                  │
│  ├── Calls analyze_all_perception_tool ONCE → receives all window results   │
│  ├── TEMPORAL ANALYSIS: Trends, transitions, cross-window patterns          │
│  ├── SYNTHESIZES: Summary with key issues, alerts, anomalies                │
│  └── output_key="temp:perception_summary" ──▶ SESSION  ◄── SUMMARY          │
│      (downstream: temporal insights, aggregated issues - NOT raw windows)   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  analyze_all_motion_tool (Python) - SINGLE CALL, ALL WINDOWS                │
│  ├── INPUT: window_ids[], odd_context from agent                            │
│  ├── READS: motion_*.json for ALL windows from disk                         │
│  ├── ANALYZES: Each window - IMU stats, motion state, anomalies             │
│  ├── SAVES TO ARTIFACT: motion_output.json  ◄── ALL WINDOWS                 │
│  │   {per_window: [{window_id, motion_state, imu_stats, issues}...]}        │
│  └── RETURNS TO AGENT: Full per-window results for all windows              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  MotionAgent (LLM)                                                          │
│  ├── Reads {temp:odd_spec} for ODD context                                  │
│  ├── Calls analyze_all_motion_tool ONCE → receives all window results       │
│  ├── TEMPORAL ANALYSIS: Motion transitions, stability trends                │
│  ├── SYNTHESIZES: Summary with key issues, state changes, anomalies         │
│  └── output_key="temp:motion_summary" ──▶ SESSION  ◄── SUMMARY              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  analyze_all_collision_tool (Python) - SINGLE CALL, ALL WINDOWS             │
│  ├── INPUT: window_ids[], odd_context, motion_summary from agent            │
│  ├── READS: motion_*.json, cam_*.png for ALL windows from disk              │
│  ├── ANALYZES: Each window - collision indicators, risk assessment          │
│  ├── SAVES TO ARTIFACT: collision_output.json  ◄── ALL WINDOWS              │
│  │   {per_window: [{window_id, collision_detected, confidence, evidence}...]}│
│  └── RETURNS TO AGENT: Full per-window results for all windows              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  CollisionAgent (LLM)                                                       │
│  ├── Reads {temp:odd_spec}, {temp:motion_summary}                           │
│  ├── Calls analyze_all_collision_tool ONCE → receives all window results    │
│  ├── TEMPORAL ANALYSIS: Collision patterns, risk progression                │
│  ├── SYNTHESIZES: Summary with collision count, risk assessment             │
│  └── output_key="temp:collision_summary" ──▶ SESSION  ◄── SUMMARY           │
└─────────────────────────────────────────────────────────────────────────────┘

════════════════════════════════════╪══════════════════════════════════════════
                            EVALUATOR AGENT
════════════════════════════════════╪══════════════════════════════════════════
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  construct_cod_tool (Python)                                                │
│  ├── LOADS FROM ARTIFACTS: odd_spec_full.json, perception_w*.json,          │
│  │   motion_w*.json, collision_w*.json                                      │
│  ├── COMPUTES: COD envelope, region_metrics, violations                     │
│  ├── SAVES TO ARTIFACT: cod_construction.json  ◄── FULL COD DATA            │
│  │   {cod_envelope, per_window_compliance, metrics}                         │
│  └── RETURNS TO AGENT: Full COD construction result                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  EvaluatorAgent (LLM)                                                       │
│  ├── Reads session summaries for context                                    │
│  ├── Calls construct_cod_tool → receives full COD data                      │
│  ├── ANALYSIS: Determines verdict, identifies key concerns                  │
│  ├── SYNTHESIZES: Compliance verdict with rationale                         │
│  └── output_key="temp:evaluator_output" ──▶ SESSION  ◄── VERDICT SUMMARY    │
│      (downstream: verdict, key_concerns, recommendation - NOT full COD)     │
└─────────────────────────────────────────────────────────────────────────────┘

════════════════════════════════════╪══════════════════════════════════════════
                             REPORT AGENT
════════════════════════════════════╪══════════════════════════════════════════
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ReportAgent (LLM) - NO TOOLS, NO ARTIFACTS                                 │
│  ├── READS SESSION SUMMARIES:                                               │
│  │   {temp:odd_spec}, {temp:perception_summary}, {temp:motion_summary},     │
│  │   {temp:collision_summary}, {temp:evaluator_output}                      │
│  ├── Synthesizes executive summary for human consumption                    │
│  ├── OUTPUTS: Human-readable report JSON                                    │
│  └── output_key="temp:report_output" ──▶ SESSION STATE                      │
└─────────────────────────────────────────────────────────────────────────────┘

════════════════════════════════════╪══════════════════════════════════════════
                          POST-PIPELINE (Python)
════════════════════════════════════╪══════════════════════════════════════════
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  report_builder.py                                                          │
│  ├── Extracts session summaries from ADK events                             │
│  ├── LOADS ARTIFACTS for full detail: odd_spec_full.json, *_w*.json,        │
│  │   cod_construction.json                                                  │
│  ├── Combines into full_result.json (summaries + full artifacts)            │
│  └── Saves to data/archive/analysis_results/                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  generate_html_report.py                                                    │
│  ├── Reads full_result.json                                                 │
│  ├── Reads scenario images (cam_*.png, bev_*.png)                           │
│  ├── Has FULL DETAIL from artifacts for deep inspection                     │
│  └── Generates interactive HTML report with drill-down capability           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Session State Keys Reference

Session state carries **summaries** for downstream token efficiency.

| State Key | Set By | Consumed By | Contents (Summary) |
|-----------|--------|-------------|-------------------|
| `temp:odd_spec` | OddSpecAgent | Perception, Motion, Collision, Evaluator, Report | Key axes, limits, constraints |
| `temp:perception_summary` | PerceptionAgent | Collision, Evaluator, Report | Temporal insights, aggregated issues, alerts |
| `temp:motion_summary` | MotionAgent | Collision, Evaluator, Report | Motion state summary, transitions, anomalies |
| `temp:collision_summary` | CollisionAgent | Evaluator, Report | Collision count, risk assessment, patterns |
| `temp:evaluator_output` | EvaluatorAgent | Report | Verdict, key concerns, recommendation |
| `temp:report_output` | ReportAgent | (final output) | Executive summary |

---

## Artifacts Reference

Artifacts preserve **full detail** for debugging, audit trails, and post-processing.

| Artifact | Saved By | Contents | Post-Processing Value |
|----------|----------|----------|----------------------|
| `odd_spec_full.json` | save_odd_spec_tool | Complete ODD specification | Debug: "What ODD was evaluated?" |
| `perception_output.json` | analyze_all_perception_tool | All per-window observations | Debug: inspect any window's perception |
| `motion_output.json` | analyze_all_motion_tool | All per-window IMU analysis | Debug: inspect any window's motion |
| `collision_output.json` | analyze_all_collision_tool | All per-window collision detection | Debug: inspect collision evidence |
| `cod_construction.json` | construct_cod_tool | Full COD envelope, metrics | Debug: "What was the COD state?" |

**Loaded by:**
- `construct_cod_tool`: Loads `odd_spec_full.json` + sensor output artifacts
- `report_builder.py`: Loads all artifacts for `full_result.json`
- `generate_html_report.py`: Uses full_result for detailed report

---

## Common Pitfalls

### 1. Tool returns `{status: saved}` instead of data
If a save tool only returns status, the agent has no data to summarize.

**Fix:** Tools must return the full data they saved, so agents can synthesize summaries.

### 2. Agent outputs raw tool return instead of summary
If agent just echoes tool output, session carries too much detail (token bloat).

**Fix:** Agent prompts must instruct: "Synthesize a summary including key issues, alerts, anomalies."

### 3. Agent doesn't output JSON → state is empty
If an agent only calls tools and doesn't produce text output, `output_key` captures nothing.

**Fix:** Prompts must instruct agents to output JSON summary after tool calls.

### 4. State key mismatch
If `output_key` doesn't match what downstream agents reference, state lookup fails.

**Fix:** Ensure `output_key` matches `{temp:xxx}` references exactly.

### 5. Optional state references (`{temp:xxx?}`)
Optional references allow hallucination when upstream data is missing.

**Fix:** Remove `?` - pipeline should fail fast if required state is missing.

### 6. Artifacts not saved → post-processing blind
If tools don't save artifacts, you can't debug intermediate outputs.

**Fix:** Every tool must save its full output as an artifact before returning.

---

## Post-Processing Architecture (Phase 1.6)

After the ADK pipeline completes, `report_builder.py` generates comprehensive reports from:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         POST-PIPELINE PROCESSING                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ARTIFACTS (from tools)           SESSION STATE (from agents)               │
│  ┌────────────────────┐           ┌────────────────────┐                    │
│  │ odd_spec.json      │           │ temp:odd_spec      │ ← Full spec+summary│
│  │ perception_*.json  │           │ temp:perception_*  │ ← Temporal summary │
│  │ motion_*.json      │           │ temp:motion_*      │ ← Temporal summary │
│  │ collision_*.json   │           │ temp:collision_*   │ ← Temporal summary │
│  │ cod_construction   │           │ temp:evaluator_*   │ ← COD + verdict    │
│  └────────────────────┘           │ temp:report_*      │ ← Executive report │
│           │                       └────────────────────┘                    │
│           │                                │                                │
│           └────────────┬───────────────────┘                                │
│                        ▼                                                    │
│           ┌─────────────────────────────┐                                   │
│           │   generate_reports_from_    │                                   │
│           │      artifacts()            │                                   │
│           └─────────────────────────────┘                                   │
│                        │                                                    │
│           ┌────────────┴────────────┐                                       │
│           ▼                         ▼                                       │
│  ┌──────────────────┐     ┌──────────────────┐                              │
│  │ executive_summary│     │ full_technical   │                              │
│  │      .json       │     │     .json        │                              │
│  └──────────────────┘     └──────────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Entry Point: `generate_reports_from_artifacts()`**
- Artifacts: Full per-window data (for detailed analysis, debugging)
- Session State: Agent summaries (for executive overview, temporal insights)
- Output: `executive_summary.json` + `full_report.json`

**HTML Report Generator: `generate_html_report.py`**
- Input: `full_result.json` (includes artifacts, session_state, metadata)
- Extracts compliance/COD from multiple schema formats (artifacts, full_analysis, session_state)
- Renders interactive HTML with charts, images, tables

---

## Agent Patterns Summary

| Agent | Has Tools? | Saves Artifacts? | Pattern |
|-------|-----------|------------------|---------|
| OddSpec | Yes | Yes (`odd_spec.json`) | Tool → Artifact, Agent → Full spec + Summary |
| Perception | Yes | Yes (`perception_analysis.json`) | Tool batch → Artifact, Agent → Temporal Summary |
| Motion | Yes | Yes (`motion_analysis.json`) | Tool batch → Artifact, Agent → Temporal Summary |
| Collision | Yes | Yes (`collision_analysis.json`) | Tool batch → Artifact, Agent → Temporal Summary |
| Evaluator | Yes | Yes (`cod_construction.json`) | Tool constructs COD → Artifact, Agent → Summary |
| Report | No | No | Reads summaries → Final output |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.2.0 | 2024-11-30 | Added post-processing architecture with artifacts + session state |
| 1.1.0 | 2024-11-30 | Updated to "artifacts everywhere" pattern - all tools save full detail |
| 1.0.0 | 2024-11-30 | Initial documentation of Phase 1.5 architecture |
