# 2025-11-29 Automated Run Review (production batch `20251129_064408`)

Use this doc to capture accuracy issues and pipeline tweaks while we walk the seven scenarios. Each row should record what we saw, why it might be wrong, and the action to take.

## Quick run metadata
- Batch path: `data/archive/analysis_results/automated/20251129_064408`
- Scenarios: `real_173442`, `real_173813`, `real_174232`, `real_174321`, `real_174503`, `real_174604`, `sim_1`
- Verdict mix: 0 IN_ODD, 2 BOUNDARY, 5 OUT_ODD
- Known symptom across summaries: `data_quality.warnings` include “No perception/motion/collision data available” and empty `scenario_overview`/`key_observations`, despite successful runs. Likely a report builder/handoff issue.

## Findings & Fixes Log

| Scenario | Verdict | What looks wrong | Suspected cause | Action / owner |
| --- | --- | --- | --- | --- |
| real_173442 | OUT_ODD | (fill during review) |  |  |
| real_173813 | BOUNDARY | Executive summary missing observations; data warnings say no perception/motion/collision data. Agent outputs actually present (perception.summary_insights populated). | Report builder reading scenario context instead of artifacts (post-artifact refactor) or not loading agent_outputs in batch mode. | Fix report builder to consume `agent_outputs`/artifacts; verify batch run passes paths; rerun on a subset. |
| real_174232 | OUT_ODD |  |  |  |
| real_174321 | OUT_ODD |  |  |  |
| real_174503 | BOUNDARY |  |  |  |
| real_174604 | OUT_ODD |  |  |  |
| sim_1 | OUT_ODD | Exec summary “no perception/motion/collision data” | Same as above | Same as above |

## Cross-cutting issues to check
- **Report builder sourcing:** Validate it reads artifacts (perception/motion/collision outputs) after we moved away from scenario-context passing. The warnings suggest it’s still looking at empty context.
- **Tool save calls:** Confirm perception/motion/collision tool calls still save artifacts in batch mode (no gating on manual runs).
- **Evaluator/report contracts:** Ensure evaluator artifacts are present and report builder uses them to populate `scenario_overview`, `key_observations`, and `measurement_summary`.- **Collision as advisory:** Per `IMPROVEMENT_PLAN_ODD_AGENTS.md`, collision (binary + risk) is now fully advisory and should NOT affect ODD/COD verdict. Actions below should be read in that context—collision accuracy still matters for safety reporting, but won't flip verdicts.
## Next steps
- Open HTML reports in `docs/reports/<scenario>_report.html` while cross-referencing `full_result.json`.
- For each scenario, fill the table above (what looks wrong → suspected cause → action).
- Apply fixes, rerun a small subset (e.g., `real_173813`, `sim_1`) to confirm summaries populate correctly. 

## Thematic Tweaks (prompt/logic)

### 1) Obstacle density overestimation
- **Current prompt:** In `odd_agents/tools/perception.py`, obstacle_density is guided qualitatively (0.0–1.0 with loose bins) and suggests counting “bright pixels in upper half of BEV occupancy.” It can over-call “dense” based on camera clutter cues.
- **Recommendation:**
  - Ground density in BEV occupancy fraction: explicitly ask for “fraction of forward-path non-ground pixels” with a numeric % reported, and tie the 0.2/0.5/0.8 bins to concrete % (e.g., <20% clear, 20–50% light, 50–80% moderate, >80% dense).
  - Require a short numeric justification in the output (e.g., `obstacle_density_pct` and `top_clusters` counts).
  - Emphasize BEV > camera for density; camera only to confirm object types, not to inflate density.

### 2) Stairs nuance (up vs down, presence vs hazard)
- **Current prompt:** Perception marks stairs_present as a hard constraint (“Stairs are a HARD constraint for most robots”) without direction/proximity nuance.
- **Recommendation:**
  - Update stairs guidance to classify direction and proximity: `stairs: {present: bool, direction: up|down|unknown, proximity_m: <float>, risk: low|med|high, justification}`.
  - Policy: Only trigger OUT_ODD when (a) ODD forbids stairs outright, or (b) downward stairs intersect path / are very near (<~1.5 m) without clearance. Upward stairs in view but not intersecting path → INFO/BOUNDARY unless ODD bans stairs.
  - Add this logic to the perception prompt and ensure collision/report use the structured fields rather than a blanket “stairs = hard constraint.”

## Scenario Notes

### real_173442 (expected IN_ODD, pipeline OUT_ODD)
- **Findings:** 10 false-positive collision events; stairs presence treated as OOD; terrain should be within ODD; obstacle density overestimated.
- **Suspected causes:**
  - Collision prompt too eager on IMU spikes/BEV proximity, lacking path-intersection checks; stairs treated as hard hazard regardless of direction/proximity.
  - Terrain misflag could come from roughness/BEV normalization or prompt conflating texture with elevation.
  - Obstacle density: same BEV percentage/justification gap noted above.
- **Actions:**
  - Apply stair nuance prompt update (direction/proximity/risk) in perception/collision; only mark OOD for downward/near-path stairs or ODD-ban.
  - Tighten collision false-positive filters: require combined IMU + BEV proximity + camera confirmation; include path-intersection gating.
  - Terrain: ensure roughness uses height/roughness BEV, not texture; verify normalization constants; add prompt reminder that carpet/tile ≠ rough terrain.
  - Obstacle density: apply BEV-percentage grounding and numeric justification.

### real_173813 (BOUNDARY, largely correct but conservative)
- **Findings:** Obstacle density overestimated; 5 low-impact collision flags even though motion agent says the robot was stationary; collision summaries still imply repeated contacts.
- **Suspected causes:**
  - Collision agent allows “low-force” collisions without motion gating (no IMU spikes, but flags anyway).
  - No cross-agent consistency check between MotionAgent (stationary) and CollisionAgent (collision streak).
  - Same BEV-driven density inflation as noted above.
- **Actions:**
  - Add motion-state gating in collision: require nonzero motion or significant IMU evidence, or downgrade to info when stationary.
  - Add consistency check: if MotionAgent reports stationary across windows, collision flags need strong evidence (IMU + visual contact) to count.
  - Apply obstacle-density prompt update (BEV percentage + numeric justification).

### real_174232 (OUT_ODD, collisions expected)
- **Findings:** Obstacle density and terrain type misflags similar to other scenarios. Collision detections are expected/valid (robot intentionally hit a cardboard box).
- **Suspected causes:** Same BEV density/roughness prompt gaps; collision is fine here.
- **Actions:**
  - Apply obstacle-density BEV-percentage grounding and roughness clarification (texture ≠ elevation).
  - No collision change needed for this scenario (detection is correct).

### real_174321 (OUT_ODD, ramp traversal)
- **Findings:** Correctly flagged pitch/roll exceeding ODD on the ramp. Many collisions detected (~20) from ramp contacts and hitting a cabinet; may be slightly over-counted but directionally correct. Obstacle density overestimated; terrain flagged as rough (arguably warranted due to ramp traversal).
- **Suspected causes:** Same density prompt gap; collision count could be tuned with stronger IMU+path gating to reduce duplicates.
- **Actions:**
  - Apply density grounding updates; keep terrain allowance for ramps but ensure roughness ties to elevation, not texture.
  - Tune collision clustering: merge closely spaced ramp contacts to reduce duplicate events; require IMU + BEV/path evidence before incrementing counts.

### real_174503 (BOUNDARY, smooth ramp traversal)
- **Findings:** Smooth ramp run; high pitch detected but stayed within ODD limits. No terrain or obstacle-density violations flagged here.
- **Notes:** This is closer to desired behavior on ramp traversal—keep as a reference when tuning collision/density thresholds so we don’t regress.

### real_174604 (OUT_ODD, humans/animals present, stationary robot)
- **Findings:** Robot stationary; obstacle density overestimated; traversability underestimated; many false-positive collisions despite zero motion. Humans/animals present, but no ODD violation flagged for close proximity (human walked up close; should be OOD).
- **Suspected causes:** Collision lacks motion gating; perception/collision not enforcing human/animal proximity limits; density/traversability prompts still too aggressive.
- **Actions:**
  - Add motion-state gating to collision (as with 173813) to suppress collisions when stationary unless IMU/visual contact is strong.
  - Add explicit human/animal proximity rule in perception/collision: flag OOD when person/animal within safety radius; include distance estimate if possible.
  - Apply density/traversability prompt updates (BEV percentage, roughness grounding).

### sim_1 (OUT_ODD, deliberate impacts)
- **Findings:** Deliberate collisions present (robot driven through objects). Max roll violation noted but not well reasoned in results. Overall not bad; still inherits density bias.
- **Actions:** Improve roll/pitch reasoning narrative in reports; apply density prompt update. Collision handling can stay as-is for this scenario.

## Evaluator Verbosity (cross-agent reasoning)
- The evaluator has the holistic view (all agent outputs + ODD spec) and should provide detailed, audit-friendly rationales to catch/mitigate upstream mistakes.
- Recommendations:
  - Per critical axis, list: measured value(s) from agents, ODD limit, distance, and a one-line justification.
  - Roll/pitch: max values, windows, and why OUT/BOUNDARY.
  - Collisions: enumerate with evidence flags (IMU/BEV/camera) and note motion state; downweight low-evidence collisions when stationary.
  - Humans/animals: proximity and whether it violates ODD.
  - Stairs: direction/proximity/risk and whether ODD bans them.
  - Density/roughness: include %/Δz used in the decision.
  - Consistency checks: call out conflicts (e.g., stationary motion vs multiple low-evidence collisions; smooth terrain vs “high density”).
  - Surface COD vs ODD distance per axis, stability (STABLE/MIXED/DEGRADING), and a concise “Why” section ordered by impact.
  - Consume artifacts/`agent_outputs` directly (not scenario context).
