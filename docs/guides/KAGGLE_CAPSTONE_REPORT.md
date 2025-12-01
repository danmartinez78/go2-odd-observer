# Agents Intensive Capstone – Go2 ODD Observer

This document outlines how the Go2 ODD Observer project maps to the Kaggle **Agents Intensive – Capstone Project** requirements: a real, multi-agent system that uses tools, knowledge, and evaluation to solve a concrete problem.

> 📌 **See also:** [Capstone Overview (HTML)](../capstone.html) for a visual summary with sample outcomes.

## 1. Problem Statement

Legged robots like the Unitree Go2 are starting to operate in real indoor spaces such as offices and labs. Safe use requires more than a robot that usually behaves well—we need to know whether it is being used inside the conditions it was actually designed and validated for.

**The Operational Design Domain (ODD)** describes the environment and conditions the robot is designed and validated to operate safely in: indoor, level floors, limited clutter, specific lighting, speed or tilt limits.

**The Current Operating Domain (COD)** is the environment and conditions the robot is actually operating in during a specific run.

If the COD does not match the ODD, there can be serious safety problems. A robot validated for clean, well-lit corridors might end up operating in darker, tighter, more cluttered areas than the ODD assumed, and its behavior is no longer guaranteed to be safe.

In practice, teams have logs, plots, and some ad hoc rules, but they do not have a clear, end-to-end answer to:

> *"For this specific run, did the robot stay inside its ODD, and if not—where, when, and by how much did it go out of bounds?"*

**ODD Observer answers that question.** Given:
- A natural language ODD description,
- A recorded run with camera images, LiDAR bird's eye view (BEV) images, and IMU data,
- Scenario metadata,

the system reconstructs the COD for that run, compares COD to the ODD, and labels time windows and axes as **IN_ODD**, **BOUNDARY**, or **OUT_ODD**. It then produces a human-readable report that explains where the run was clearly safe, where it was near the edge, and where it left the intended design domain.

### 1.1 Inputs & Outputs

- **Inputs**:
  - Synchronized camera frames, LiDAR-derived BEV images, and IMU/motion traces, grouped into fixed time windows.
  - A natural-language ODD description (environment, ego limits, actors).
  - A shared knowledge base for sensors, robot profile, and COD fundamentals.
- **Outputs**:
  - A structured COD/region verdict (IN_ODD / BOUNDARY / OUT_ODD) with supporting axes.
  - Per-window ODD measurements for perception, motion, and collision.
  - A narrative report with compliance summary, key findings, and recommendations.

## 2. Why Agents?

The problem naturally breaks into several reasoning tasks:

1. Turn a free-form ODD description into a structured spec with numeric ranges, categories, and rules.
2. Turn raw sensor data (images, BEV, IMU) into semantic descriptions per time window.
3. Aggregate those descriptions into a COD for the run.
4. Compare COD and ODD, generate verdicts, and explain them to a human reviewer.

Each step has different inputs and a different style of reasoning. Treating this as one giant prompt makes it harder to debug and trust. A multi-agent setup works better:

| Agent | Focus |
|-------|-------|
| Spec agent | Schema-compliant ODD parsing |
| Perception agent | Images and BEV maps |
| Motion agent | IMU and motion reasoning |
| Collision agent | Proximity and impact detection |
| Evaluator agent | COD vs ODD comparison |
| Report agent | Clear human summary |

This also improves **traceability**. When a window is marked OUT_ODD, we can inspect the artifacts from each agent instead of guessing what happened inside a single black-box call.

## 3. Agent Architecture

High-level pipeline (single run):

1. **ODD Spec Agent** – converts NL ODD description into a structured axis schema (environment/actors/ego).
2. **Perception Agent** – loops over windows and estimates ODD-relevant environment axes (lighting, terrain, obstacle density, data source).
3. **Motion Agent** – loops over windows and computes ego motion metrics (IMU-based plus camera cues).
4. **Collision Agent** – loops over windows and detects collisions / near-misses (IMU + BEV + camera).
5. **Evaluator Agent** – aggregates all per-window results into a COD region verdict and COD metadata.
6. **Report Agent** – synthesizes the final human-readable report and saves it as an artifact.

All loop agents use **Google ADK**:

- Agents are implemented as ADK `Agent`s backed by **Gemini 2.5 Pro**.
- Tools are **FunctionTools** wrapping Python functions for:
  - Window listing.
  - Data loading + Gemini Vision calls.
  - Saving per-domain outputs as artifacts.

### 3.1 Knowledge Layer

Agents share a common knowledge foundation:

- **ODD and COD fundamentals**: Robot-agnostic descriptions of what ODD and COD mean and what the main axes are (`docs/guides/ODD_COD_FUNDAMENTALS.md`).
- **Go2 profile**: Typical indoor operating patterns and thresholds for concepts like "moderate clutter" or "narrow corridor" for this platform (`docs/agent_knowledge/profiles/ROBOT_GO2_PROFILE.md`).
- **Sensor interpretation**: BEV, camera, IMU patterns and how to interpret them (`docs/agent_knowledge/core/SENSOR_INTERPRETATION.md`).

This keeps the reasoning consistent across runs and agents. Mainline agents are instructed to treat ODD spec JSON as authoritative for axis names and limits, and use KB for interpretation patterns only.

### 3.2 Perception Tools (camera + BEV)

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

### 3.3 Motion Tools (IMU + camera)

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

### 3.4 Collision Tools (IMU + BEV + camera)

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

### 3.5 Evaluator & Report

- **EvaluatorAgent**:
  - Consumes ODD spec + per‑window outputs.
  - Produces a structured COD region evaluation (e.g., IN_ODD/BORDERLINE/OUT_ODD) and aggregates metrics over windows.
- **ReportAgent**:
  - Consumes Evaluator + loop‑agent summaries (state + artifacts).
  - Calls `generate_report_tool` to produce the final JSON report and saves it as `odd_compliance_report.json`.

## 4. Data & Scenarios

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

## 5. Evaluation & Testing

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

## 6. Design Choices & Lessons

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

## 7. How This Fits the Kaggle Capstone Brief

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

## 8. Implementation & Reproducibility

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


## 9. Demo & Static Site

The repository includes a static site under `docs/` that can be hosted on GitHub Pages. It has:

- **A landing page** with a short project overview and links to documentation and scenario results.
- **Per-scenario HTML reports** that show:
  - The overall verdict (IN_ODD, BOUNDARY, or OUT_ODD),
  - Key metrics such as percentage of windows OUT_ODD,
  - Selected camera and BEV frames for important events,
  - Tables that compare ODD assumptions to the observed COD,
  - A short narrative summary.
- **A dashboard** that aggregates multiple scenarios and lets you compare runs.

To demonstrate the system on a new run:
1. Generate a scenario directory with images, BEV tiles, IMU windows, and an ODD description.
2. Run the analysis script.
3. Run a report generator that produces an HTML report for that scenario and updates the site.

An interactive Jupyter notebook (`notebooks/odd_analysis_demo.ipynb`) walks through the full pipeline on a sample scenario.

## 10. Versioning

Because this is safety-related analysis, we track which data and which agent configuration produced each result.

- **Data level**: Raw logs and processed scenario directories are tracked with explicit data versions. A simple manifest documents which raw collections, preprocessing steps, and parameter settings produced each derived data set. A scenario in the dashboard can be traced back to the original collection date, bag files, and preprocessing pipeline.

- **Analysis level**: Each run of the ODD Observer pipeline attaches structured metadata to its JSON output. This includes a unique analysis run ID, the ODD description used, the data version and scenario ID, the configured agent bundle, and the model family and model names used for each agent. When the code is run from a Git repository, the current commit hash is also recorded.

- **Reporting level**: The HTML reports and dashboard ingest that metadata and surface it alongside the human-readable content. A scenario report can tell you which version of the data, which agent configuration, which model family, and which code revision produced the verdict.

The net effect is that each scenario is not just a one-off result—it is a reproducible experiment with enough version information to be rerun or audited later.

See [VERSIONING.html](../VERSIONING.html) for details.

## 11. Limitations

- **Model & prompt sensitivity**: The pipeline currently relies on Gemini 2.5 Pro and carefully crafted prompts; behavior can drift if models or defaults change. Some hallucination risk remains, especially in narrative fields.

- **Grounding of narrative outputs**: Evaluator and Report agents consume state + artifacts but still depend on LLM judgment. ADK hallucination metrics help, but report hallucination checks are limited by current function_call grounding support.

- **No persistent memory service**: Each run is independent; there is no long-term memory across runs. This is acceptable for batch logs, but future iterations could benefit from cross-scenario learning.

- **Sensor coverage**: Current implementation uses camera, LiDAR-derived BEV, and IMU. Visual odometry and LiDAR odometry are designed but not yet integrated.

## 12. Future Work

| Area | Description |
|------|-------------|
| **Memory & Retrieval Layer** | Finish run-level and ODD-level memory; let agents reference similar past scenarios and aggregated statistics when judging a new run. |
| **Broader Environment Coverage** | Include more buildings, lighting conditions, clutter patterns, and edge features such as stairs, ramps, and glass surfaces. |
| **Operator Dashboard** | Turn the dashboard into a more complete tool that supports filtering by ODD, robot, date, or severity, drilling into single runs, and exporting PDF-style reports for reviews and audits. |
| **Toward Real-Time** | Experiment with a lightweight variant of the pipeline that can run close to real time to warn when the COD is approaching or leaving the ODD during operation. |

---

**In its current form, ODD Observer shows that a small set of focused agents, grounded in ODD and COD knowledge and fed with real robot data, can reconstruct the COD of a Go2 run and compare it to the design ODD in a structured, understandable way.**
