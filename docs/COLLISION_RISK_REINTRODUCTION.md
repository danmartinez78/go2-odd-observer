# Collision Signals (Fully Advisory)

**Purpose:** Both collision detection (binary) AND collision risk (0-1) are **advisory safety signals**, entirely outside ODD/COD computation. They are reported for awareness but do NOT affect IN_ODD/BOUNDARY/OUT_ODD verdicts.

**Rationale:** Collisions are safety events to be reported, not operational domain characteristics. A robot can be operating fully within its ODD and still experience a collision (user error, unexpected obstacle, sensor failure, etc.). Conversely, a robot outside its ODD may not have any collisions. The two concepts are orthogonal.

## References
- `docs/RESULTS_REVIEW_20251129.md` — recent production findings (false positives, stationarity, proximity cases).
- `docs/PROPOSED_ODD_UPDATE.md` — broader ODD relaxation context.

## Collision Signals (Both Advisory)
- **Binary collision (`collision_detected`):** True/false detection of actual contact. Advisory only.
- **Risk signal (`collision_risk`):**
  - Compute from proximity + density + motion state (and optionally heading/velocity).
  - Output: `collision_risk_score` (0–1), `risk_band` (LOW/MED/HIGH), `justification` (short, numeric: min distance, density %, speed).
  - Scenario-aware tolerance: higher tolerance in furniture-dense indoor runs; lower tolerance in open spaces.
  - Stationary runs: risk should be low unless there is strong proximity evidence.

## Tool/Agent Changes
- **Collision tool/agent:**
  - Output both `collision_detected` (bool) and `collision_risk` (0-1, with justification).
  - Evidence gating for binary detection (IMU + BEV proximity + camera confirmation).
  - Risk computed from proximity + density + motion state.
  - Neither signal maps to ODD/COD axes.
- **Evaluator:**
  - Ingest collision signals as context for reporting.
  - Do NOT alter ODD/COD verdict based on collisions or risk—these are orthogonal.
  - Include collision summary in rationale: "X collisions detected, risk band Y" for awareness.
- **Report:**
  - Dedicated "Collision Advisory" section showing binary events + risk timeline.
  - Clearly labeled as advisory (does not affect compliance verdict).

## Why Fully Advisory?
- ODD defines where the robot is *designed* to operate (terrain, lighting, motion profile, etc.).
- Collisions are *events* that can happen anywhere—inside or outside ODD.
- Conflating the two leads to confusing results (e.g., "IN_ODD but collision" or "OUT_ODD only because of collision").
- Separating them provides clearer signal: ODD verdict for domain compliance, collision signal for safety awareness.
