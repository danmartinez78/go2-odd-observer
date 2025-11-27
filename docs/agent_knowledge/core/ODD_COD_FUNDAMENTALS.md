# ODD & COD Fundamentals (Core)

**Purpose:** Shared, robot-agnostic reference for agents to keep terminology and judgment consistent. Use this for grounding; do not override the per-run ODD spec artifact.

**Version:** v1.0.0 (knowledge-only; no schema changes)

## Scope & Composition
- **Core fundamentals (this file):** Generic definitions, verdict rules, axis naming conventions, sensor reasoning patterns.
- **Platform/application profiles:** Optional per-robot or per-application addenda (e.g., `robot:go2_profile_v1`, `app:warehouse_nav_profile_v1`). These live in separate docs and should not redefine axis names—only add context or examples.
- **Manifest:** A lightweight mapping (e.g., `ref:knowledge_manifest`) can list which docs apply for a run: fundamentals, robot profile, app/ODD profile. Agents read the manifest instead of hardcoding doc names.

## Core Definitions
- **Operational Design Domain (ODD):** Allowed operating envelope for the robot. Defined per-axis (environment, actors, ego) with categorical, numeric, or boolean constraints.
- **Current Operating Domain (COD):** What the robot actually experienced in this run (per window) along the same axes as the ODD spec.
- **COD Distance:** Distance between COD and ODD regions. Smaller = closer to ODD; 0 means fully compliant. Higher implies more or larger violations.

## Verdict Criteria
- **IN_ODD:** All axes within ODD limits for the window. Minor noise that does not cross limits is acceptable.
- **BOUNDARY:** At or near edge of ODD limits (e.g., within tolerance of a max/min, ambiguous categorical state). Treat as caution, not automatic failure.
- **OUT_ODD:** One or more axes exceed ODD limits or violate disallowed categorical/boolean states. Persistent OUT_ODD windows drive scenario-level failure.

## Axis Types & Naming (stay aligned with ODD Spec agent)
- **Environment categorical:** `environment_type`, `lighting_conditions`, `terrain_type`, `weather_conditions`
- **Environment numeric:** `obstacle_density`, `traversability_score`, `temperature_c`
- **Environment boolean:** `stairs_present`, `outdoor_environment`
- **Actors categorical:** `actor_types`
- **Actors numeric:** `min_proximity_m`, `actor_density`
- **Actors boolean:** `humans_present`
- **Ego categorical:** `motion_state`
- **Ego numeric:** `max_speed_mps`, `max_accel_mps2`, `max_roll_deg`, `max_pitch_deg`, `max_angular_velocity_radps`, `peak_jerk_mps3`
- **Ego boolean:** `collision_detected`

Use the axis definitions from the ODD spec artifact as the source of truth for ranges and allowed values. This list is for naming consistency only.

## Sensor Interpretation Guidance
- **LiDAR BEV (3 channels):** Occupancy, height, roughness. Occupancy = obstacles/present surfaces; height = vertical relief; roughness = surface variability. Empty borders are auto-cropped—focus on the active area.
- **Camera:** Use for semantic cues (lighting, weather hints, obstacles/actors) and for corroborating BEV patterns.
- **IMU:** Primary source for motion state, acceleration/jerk spikes, and collision signatures. Treat gravity-corrected horizontal acceleration as the main signal.

## Reasoning Patterns
- Prefer the ODD spec artifact for thresholds; use this doc only for definitions and patterns.
- For numeric axes, respect hazard/quality/envelope semantics:
  - Hazard (e.g., obstacle_density): upper bounds matter; lower bound often 0.
  - Quality (e.g., traversability_score): lower bounds matter; upper bound often 1.0.
  - Envelope (e.g., speed, acceleration, temperature): both bounds matter.
- When uncertain, classify as **BOUNDARY** rather than forcing IN/OUT; cite why.

## Manifest Hook (when enabled)
- Memory key idea: `ref:knowledge_manifest` → `{ "fundamentals": "artifact:odd_cod_fundamentals_v1", "sensors": "artifact:sensor_interpretation_core_v1", "robot": "artifact:robot_go2_profile_v1" }`.
- Agents may read the manifest to locate the right docs. Fundamentals are always included; robot/app profiles are optional and additive.

---

**Usage reminder:** This document is a knowledge/reference source. Do not invent limits from it; always derive constraints from the provided ODD spec artifact for the run.
