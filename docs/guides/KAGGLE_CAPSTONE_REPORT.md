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
- Tools are either:
  - **FunctionTools** (Python implementations for window listing, data loading, saving artifacts), or
  - **AgentTools** (child agents used as tools, which themselves can reason with KB and call function tools).

### 2.1 Knowledge & Session Context

- A **knowledge manifest** is attached to the session:
  - `docs/agent_knowledge/core/SENSOR_INTERPRETATION.md` – BEV, camera, IMU patterns.
  - `docs/agent_knowledge/profiles/ROBOT_GO2_PROFILE.md` – robot geometry, dynamics.
  - `docs/guides/ODD_COD_FUNDAMENTALS.md` – COD/axis definitions and naming rules.
- Mainline agents are instructed to:
  - Treat ODD spec JSON as authoritative for axis names and limits.
  - Use KB for interpretation patterns only (no re‑defining axes or limits).

### 2.2 Perception AgentTool (working pattern)

- **Tool**: `PerceptionWindowAgent` (AgentTool).
- **Helper function tool**: `analyze_window(window_id, prompt)`:
  - Loads camera + three BEV channels (occupancy/height/roughness) from disk.
  - Calls Gemini Vision with a KB‑aware, odd_spec‑aware prompt + images.
  - Parses JSON and returns:
    - `odd_measurements` (flat axes: lighting_conditions, terrain_type, obstacle_density, traversability_score, stairs_present, etc.).
    - `data_source` (sim vs real, confidence + indicators).
    - `explanation`, `key_insights`, `camera_summary`, `bev_summary`.
- **Child agent role**:
  - Receives `{window_id, odd_spec}`.
  - Builds the full vision prompt (ODD axes + BEV/camera interpretation guidance from KB).
  - Calls `analyze_window`.
  - Echoes the tool result JSON as its final answer.

This pattern keeps the prompt logic inside a KB‑aware agent while the function tool handles data loading and the actual vision API call.

### 2.3 Motion AgentTool (IMU + camera)

- **Tool**: `MotionWindowAgent` (AgentTool).
- **Helper function tool**: `analyze_motion(window_id, prompt)`:
  - Loads IMU JSON (accel, gyro, roll/pitch, timestamps) and camera image.
  - Computes deterministic metrics:
    - `peak_horiz_accel`, `peak_gyro_z`, `peak_gyro_x`, `peak_gyro_y`.
    - `max_roll`, `max_pitch`.
    - `peak_jerk` (change in horizontal acceleration).
  - Augments the child‑provided prompt with a **metrics block**:
    - Pre‑computed IMU metrics in text form.
    - Heuristic hints (e.g., near‑zero metrics → stationary unless vision contradicts).
  - Calls Gemini Vision with the combined prompt + image.
  - Returns:
    - `odd_measurements` derived deterministically from IMU metrics.
    - `explanation`, `key_insights`, `motion_state` from the LLM.
- **Child agent role**:
  - Receives `{window_id, odd_spec}`.
  - Builds a prompt that describes which ODD axes to focus on and how to interpret IMU + camera (using KB).
  - Relies on the helper to inject the actual numeric metrics and run the vision call.
  - Returns the final JSON (IMU‑grounded odd_measurements + LLM narrative) to the parent.

### 2.4 Collision AgentTool (IMU + BEV + camera)

- **Tool**: `CollisionWindowAgent` (AgentTool).
- **Helper function tool**: `analyze_collision(window_id, prompt)`:
  - Loads:
    - IMU (`accel_x/y`, `gyro_z`, roll/pitch, timestamps).
    - Camera image.
    - BEV channels (if available).
  - Computes metrics:
    - `peak_accel`, `peak_gyro`, `peak_jerk`, `max_tilt`.
  - Augments the prompt with a **collision metrics block**:
    - IMU thresholds (e.g., accel >10 m/s², gyro >5 rad/s, jerk >50 m/s³ → likely collision).
  - Calls Gemini Vision with combined prompt + camera + BEV images.
  - Returns:
    - `odd_measurements` with `collision_detected` (0/1), `min_proximity_m`.
    - `explanation`, `key_insights`, `collision_detected` (bool), `confidence`.
- **Child agent role**:
  - Receives `{window_id, odd_spec}`.
  - Crafts a prompt that references ODD collision‑related axes and sensor cues (from KB).
  - Delegates actual metric injection + vision call to `analyze_collision`.
  - Returns the fused JSON result to the parent.

### 2.5 Evaluator & Report

- **EvaluatorAgent**:
  - Consumes ODD spec + per‑window outputs.
  - Produces a structured COD region evaluation (e.g., IN_ODD/BORDERLINE/OUT_ODD) and aggregates metrics over windows.
- **ReportAgent**:
  - Consumes Evaluator + loop‑agent summaries (state + artifacts).
  - Calls `generate_report_tool` to produce the final JSON report and saves it as `odd_compliance_report.json`.

## 3. Evaluation & Testing

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

## 4. Design Choices & Lessons

- **AgentTool vs FunctionTool**:
  - Perception: AgentTool wraps a single vision call; prompt logic lives in the child agent, data loading in a function tool.
  - Motion/Collision: AgentTools are used to combine IMU metrics + vision in a single reasoning step, but deterministic metrics are still computed in Python for stability.
- **Knowledge separation**:
  - ODD spec (session state) vs KB docs (reusable guidance). Agents are instructed to treat spec as authoritative and KB as advisory.
- **Artifacts for intermediate results**:
  - Loop agents save per‑domain outputs via dedicated save_* tools so Evaluator/Report can reliably consume them.
  - This decouples narrative/reporting from the internal agent traces.
- **Evaluation‑driven iteration**:
  - We used ADK rubrics to refine tool usage patterns, JSON schemas, and hallucination behavior, especially for perception and the evaluator/report pair.

## 5. How this fits the Kaggle Capstone brief

- **Real problem**: Safety/ODD compliance for a quadruped robot using real and simulated sensor logs.
- **Rich tool use**:
  - File/artifact loading, BEV/camera/IMU processing, knowledge references, and AgentTools for sub‑tasks.
- **Multiple agents & roles**:
  - Spec → loop agents → evaluator → report, each with clear responsibilities.
- **Evaluation story**:
  - Rubric‑based ADK eval suite + scenario runs on multiple datasets.
- **Extensibility**:
  - Architecture is designed to add new sensors (e.g., visual odometry, LiDAR odometry) and new agents (e.g., data quality auditor) without redoing the pipeline.

This document can be adapted into the Kaggle capstone write‑up (PDF or notebook) by adding figures (architecture diagram, sample outputs) and a short results section summarizing scores or qualitative findings from a few representative scenarios.

