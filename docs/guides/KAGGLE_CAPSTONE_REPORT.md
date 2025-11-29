# Agents Intensive Capstone – Go2 ODD Observer

This document outlines how the Go2 ODD Observer project maps to the Kaggle **Agents Intensive – Capstone Project** requirements: a real, multi-agent system that uses tools, knowledge, and evaluation to solve a concrete problem.

## 1. Problem & Objectives

- **Problem**: Given ROS2 logs from a Unitree Go2 robot (sim + real), determine whether the robot operated **within its Operational Design Domain (ODD)** over a scenario, with clear evidence and actionable feedback.
- **Inputs**:
  - Synchronized camera frames, LiDAR-derived BEV images, and IMU/motion traces, grouped into fixed time windows.
  - A natural-language ODD description (environment, ego limits, actors).
  - A shared knowledge base for sensors, robot profile, and COD fundamentals.
- **Outputs**:
  - A structured COD/region verdict (IN_ODD / BOUNDARY / OUT_ODD) with supporting axes.
  - Per-window ODD measurements for perception, motion, and collision.
  - A narrative report with compliance summary, key findings, and recommendations.
- **Goals**:
  - Automate consistent, repeatable ODD analysis across multiple datasets.
  - Make sensor interpretation robust and knowledge-grounded, not prompt-copied.
  - Provide explainable outputs suitable for safety review or debugging.

## 2. Agent Architecture

High‑level pipeline (single run):

1. **ODD Spec Agent** – converts NL ODD description into a structured axis schema (environment/actors/ego).
2. **Perception Agent** – loops over windows and estimates ODD‑relevant environment axes (lighting, terrain, obstacle density, data source).
3. **Motion Agent** – loops over windows and computes ego motion metrics (IMU‑based plus camera cues).
4. **Collision Agent** – loops over windows and detects collisions / near‑misses (IMU + BEV + camera).
5. **Evaluator Agent** – aggregates all per‑window results into a COD region verdict and COD metadata.
6. **Report Agent** – synthesizes the final human‑readable report and saves it as an artifact.

All loop agents use **Google ADK**:

- Agents are implemented as ADK `Agent`s backed by **Gemini 2.5 Pro**.
- Tools are **FunctionTools** wrapping Python functions for:
  - Window listing.
  - Data loading + Gemini Vision calls.
  - Saving per‑domain outputs as artifacts.

### 2.1 Knowledge & Session Context

- A **knowledge manifest** is attached to the session:
  - `docs/agent_knowledge/core/SENSOR_INTERPRETATION.md` – BEV, camera, IMU patterns.
  - `docs/agent_knowledge/profiles/ROBOT_GO2_PROFILE.md` – robot geometry, dynamics.
  - `docs/guides/ODD_COD_FUNDAMENTALS.md` – COD/axis definitions and naming rules.
- Mainline agents are instructed to:
  - Treat ODD spec JSON as authoritative for axis names and limits.
  - Use KB for interpretation patterns only (no re‑defining axes or limits).

### 2.2 Perception tools (camera + BEV)

- **FunctionTool**: `analyze_window_perception_tool(window_id, odd_context)`:
  - Loads camera + three BEV channels (occupancy / height / roughness) for a window.
  - Builds a self‑contained prompt with:
    - BEV semantics (robot at center, facing up; occupancy vs height vs roughness).
    - Scale (0.05 m/pixel) and how to interpret obstacles/terrain.
    - Measurement guidelines for environment_type, lighting_conditions, terrain_type, obstacle_density, traversability_score, stairs_present, humans_detected.
    - Data source detection cues (sim vs real).
    - Explicit JSON output schema and anti‑patterns (odd_measurements must be flat).
  - Calls Gemini Vision with this prompt and the four images.
  - Parses JSON and returns:
    - `odd_measurements` (flat axes).
    - `data_source` (sim/real + confidence).
    - `camera_summary`, `bev_summary`, `explanation`, `key_insights`.
- **PerceptionAgent**:
  - Uses a list‑windows tool to enumerate windows.
  - Calls `analyze_window_perception_tool` per window with a filtered `odd_context` from the ODD spec.
  - Aggregates per‑window outputs and saves them via `save_perception_output_tool`.

### 2.3 Motion tools (IMU + camera)

- **FunctionTool**: `analyze_motion_tool(window_id, odd_context)`:
  - Loads IMU JSON (accel, gyro, roll/pitch, timestamps) and camera image.
  - Computes deterministic metrics:
    - `peak_horiz_accel`, `peak_gyro_z`, `peak_gyro_x`, `peak_gyro_y`.
    - `max_roll`, `max_pitch`.
    - `peak_jerk`.
  - Builds a detailed prompt that:
    - Explains gravity leakage and tilt effects on acceleration.
    - Prioritizes camera evidence for motion vs stationary classification.
    - Describes how to use IMU temporal patterns for stability.
    - Specifies the JSON schema (odd_measurements + motion_state, platform_stability, motion_confidence, explanation, key_insights).
  - Calls Gemini Vision with this prompt and the camera image.
  - Returns:
    - `odd_measurements` populated directly with the pre‑computed IMU metrics.
    - `motion_state`, `platform_stability`, `motion_confidence`, `explanation`, `key_insights` from the LLM response.
- **MotionAgent**:
  - Uses the shared list‑windows tool.
  - Calls `analyze_motion_tool` per window with relevant ego‑motion axes from the ODD spec.
  - Saves aggregated outputs via `save_motion_output_tool`.

### 2.4 Collision tools (IMU + BEV + camera)

- **FunctionTool**: `analyze_collision_tool(window_id, odd_context)`:
  - Loads:
    - IMU (accel_x/y, gyro_z, roll/pitch, timestamps).
    - Camera image.
    - BEV channels (occupancy / height / roughness) if available.
  - Computes:
    - `peak_accel`, `avg_accel`, `peak_gyro`, `max_tilt`, `peak_jerk`.
  - Builds a comprehensive prompt that:
    - Presents the pre‑computed IMU metrics and collision thresholds (e.g., accel >10 m/s²).
    - Explains BEV‑based contact and proximity estimation (ignoring robot body).
    - Describes camera cues for impacts (blur, discontinuities).
    - Specifies the JSON schema with:
      - `collision_detected` (bool) + `confidence`.
      - `odd_measurements.collision_detected` (0/1) and `min_proximity_m`.
      - `proximity_estimate_m`, `explanation`, `key_insights`.
  - Calls Gemini Vision with this prompt and the camera + BEV images.
  - Returns a fused JSON using both IMU metrics and vision evidence.
- **CollisionAgent**:
  - Enumerates windows and calls `analyze_collision_tool` per window.
  - Aggregates and saves outputs via `save_collision_output_tool`.

### 2.5 Evaluator & Report

- **EvaluatorAgent**:
  - Consumes ODD spec + per‑window outputs.
  - Produces a structured COD region evaluation (e.g., IN_ODD/BORDERLINE/OUT_ODD) and aggregates metrics over windows.
- **ReportAgent**:
  - Consumes Evaluator + loop‑agent summaries (state + artifacts).
  - Calls `generate_report_tool` to produce the final JSON report and saves it as `odd_compliance_report.json`.

## 3. Data & Scenarios

- **Simulation scenarios**:
  - Short “two‑window” test runs (e.g., `sim_2win`) used during development to validate behavior quickly.
  - Longer production‑style scenarios (≈30 windows) that include nominal behavior, cluttered environments, and deliberate collisions.
- **Real robot scenarios**:
  - Go2 ROS2 logs exported and windowed (e.g., `real_*` datasets).
  - Include compression artifacts, varied lighting, and terrain changes beyond what is seen in sim.
- **Windowing**:
  - Fixed‑length windows shared across perception/motion/collision, each containing synchronized camera, BEV, and IMU samples.
- **Results archive**:
  - Manual runs: `data/archive/analysis_results/manual/<timestamp>/<scenario>/`.
  - Batch runs: `data/archive/analysis_results/automated/<timestamp>/`.
  - Each run saves `full_result.json` and `executive_summary.json` plus intermediate artifacts.

## 4. Evaluation & Testing

We use **ADK evaluation** for rubric‑based agent testing:

- Configs: `tests/evaluation/<agent>/test_config_*.json`.
- Metrics:
  - `rubric_based_tool_use_quality_v1`: tool usage + window coverage.
  - `rubric_based_final_response_quality_v1`: shape + completeness + insight quality.
  - `hallucinations_v1`: groundedness vs provided context (enabled for loop agents and evaluator).
- Summary of results: `tests/evaluation/RESULTS.md`.

In addition:
- We validate on:
  - **Sim test windows**: controlled scenarios to check expected COD outcomes.
  - **Real robot logs**: spot‑check behavior under real compression artifacts and noise.
- The pipeline supports manual runs (`scripts/run_odd_analysis.py`) and batch runs (`scripts/run_odd_batch_analysis.py`) over multiple scenarios with archived results.

## 5. Design Choices & Lessons

- **FunctionTool‑centric design**:
  - All heavy lifting (data loading, metric computation, prompt construction, vision calls) is done in Python FunctionTools with verbose, self‑contained prompts.
  - Tools do not assume KB access; they embed all necessary guidance directly in the prompt, making them robust to ADK session configuration.
- **Knowledge separation**:
  - ODD spec (session state) vs KB docs (reusable guidance). Agents are instructed to treat spec as authoritative and KB as advisory.
- **Artifacts for intermediate results**:
  - Loop agents save per‑domain outputs via dedicated save_* tools so Evaluator/Report can reliably consume them.
  - This decouples narrative/reporting from the internal agent traces.
- **Evaluation‑driven iteration**:
  - We used ADK rubrics to refine tool usage patterns, JSON schemas, and hallucination behavior, especially for perception and the evaluator/report pair.
- **Tradeoffs**:
  - We favored simple, robust FunctionTools with explicit prompts over more complex nested agent patterns to keep behavior predictable on real logs and under evaluation.

## 6. How this fits the Kaggle Capstone brief

- **Real problem**: Safety/ODD compliance for a quadruped robot using real and simulated sensor logs.
- **Rich tool use**:
  - File/artifact loading, BEV/camera/IMU processing, knowledge references, and multi‑tool agent orchestration for each domain.
- **Multiple agents & roles**:
  - Spec → loop agents → evaluator → report, each with clear responsibilities.
- **Evaluation story**:
  - Rubric‑based ADK eval suite + scenario runs on multiple datasets.
- **Extensibility**:
  - Architecture is designed to add new sensors (e.g., visual odometry, LiDAR odometry) and new agents (e.g., data quality auditor) without redoing the pipeline.

This document can be adapted into the Kaggle capstone write‑up (PDF or notebook) by adding figures (architecture diagram, sample outputs) and a short results section summarizing scores or qualitative findings from a few representative scenarios.

## 7. Implementation & Reproducibility

- **Environment**:
  - Python 3.10+ with dependencies from `requirements.txt`.
  - Google ADK installed and configured (agents, tools, evaluation).
  - Gemini API key available via `.env` or environment variable (used by ADK/GenAI client).
- **Repo layout (relevant pieces)**:
  - `odd_agents/agents/` – mainline agents (`odd_spec.py`, `perception.py`, `motion.py`, `collision.py`, `evaluator.py`, `report.py`).
  - `odd_agents/tools/` – FunctionTools for data loading, analysis, and artifact saving (`perception.py`, `motion.py`, `collision.py`, common helpers).
  - `docs/` – design docs, knowledge manifests, capstone report.
  - `data/` – raw and processed scenarios (sim and real), test subsets, and archived results.
  - `scripts/run_odd_analysis.py` – manual runner for a single scenario.
  - `scripts/run_odd_batch_analysis.py` – batch runner over multiple scenarios.
  - `tests/evaluation/` – ADK evaluation configs and tests for each agent.
- **How to run a single analysis** (example):
  - Configure `.env` with your Gemini API key.
  - Ensure a scenario exists under `data/production` or `data/test` (e.g., `sim_2win`).
  - Run:
    - `python scripts/run_odd_analysis.py`  
    - Select a scenario when prompted; results are saved under `data/archive/analysis_results/manual/...`.
- **How to run batch analyses**:
  - Use `python scripts/run_odd_batch_analysis.py` to process multiple scenarios (e.g., all production datasets) and log aggregate results.
- **How to run ADK evals**:
  - `pytest tests/test_adk_evaluation.py::test_perception_rubric_quality -q`
  - Similar rubric tests exist for motion, collision, evaluator, and report.

These commands and paths can be adapted directly into the Kaggle notebook or README for full reproducibility.

## 8. Limitations & Future Work

- **Model & prompt sensitivity**:
  - The pipeline currently relies on Gemini 2.5 Pro and carefully crafted prompts; behavior can drift if models or defaults change.
  - Some hallucination risk remains, especially in narrative fields (explanations, summaries); numeric odd_measurements are more constrained.
- **Grounding of narrative outputs**:
  - Evaluator and Report agents consume state + artifacts but still depend on LLM judgment. We do not yet have automatic cross‑checking against raw data in those stages.
  - ADK hallucination metrics help, but report hallucination checks are limited by current function_call grounding support.
- **No persistent memory service**:
  - Each run is independent; there is no long‑term memory across runs (e.g., VertexAiMemoryBankService). This is acceptable for batch logs, but future iterations could benefit from cross‑scenario learning or expectations.
- **Sensor coverage and realism**:
  - Current implementation uses camera, LiDAR‑derived BEV, and IMU. Visual odometry and LiDAR odometry are designed but not yet integrated; real BEV generation for LiDAR is still evolving.
  - Certain edge cases (extreme lighting, occlusions) are not exhaustively tested.
- **Future work**:
  - Integrate visual odometry and LiDAR odometry into the motion/collision pipeline, with dedicated tools and evaluation rubrics.
  - Tighten hallucination controls for Evaluator/Report once ADK provides better grounding for function_call outputs.
  - Add a data quality/coverage agent to flag windows where sensors are degraded or missing.
  - Explore persistent memory for longitudinal analysis across runs (e.g., long‑term COD statistics per site or robot).

These limitations and next steps can be used to frame the “what’s next” section of the Kaggle capstone submission.
