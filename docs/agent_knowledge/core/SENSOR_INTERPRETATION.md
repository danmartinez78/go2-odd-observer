# Sensor Interpretation (Core)

**Purpose:** Shared, robot-agnostic guidance for interpreting BEV, camera, and IMU data. Keep prompts slim by referencing this doc; do not override per-run ODD spec or tool outputs.

**Version:** v1.0.0 (knowledge-only)

## BEV Basics
- **Channels:** occupancy (obstacles/surfaces), height (vertical relief), roughness (surface variability).
- **Cropping:** BEVs are auto-cropped to remove empty borders; focus on the active region.
- **Patterns to trust:** stable high-occupancy blobs near path, consistent height gradients for ramps/curbs, roughness spikes for uneven terrain.
- **Common pitfalls:** shadows/texture in camera ≠ occupancy; sparse speckle noise near edges; LiDAR dropouts can mimic empty space.
- **Directional conventions:** use provided window metadata for orientation; do not assume north/up without metadata.

## Camera Basics
- Use for semantic context: lighting class, weather hints, obstacle/actor presence and type, surface quality cues.
- Cross-check with BEV: obstacles in camera should align with occupancy clusters; lighting changes can explain BEV sparsity.
- Avoid over-reliance on blur alone for motion; corroborate with IMU or per-window metadata.

## IMU Basics
- **Signals:** gravity-corrected acceleration, angular velocity, derived jerk.
- **Motion states:** combine magnitude + stability (smooth vs jerky) to infer steady walk, start/stop, turns.
- **Noise handling:** brief spikes may be sensor noise—look for duration/persistence.

## Collision/Anomaly Cues
- Collision signatures: sharp acceleration spikes, angular velocity anomalies, and high jerk within the same window.
- Confirm with perception context when available (e.g., obstacle proximity) but avoid hallucinating collisions without IMU evidence.

## Optional Profiles (robot/app-specific)
- Profiles may add sensor quirks (e.g., typical IMU noise, LiDAR FOV gaps) or environment-specific patterns. Profiles should not redefine channel meanings—only add cautions/examples.

**Usage reminder:** Cite sections via the knowledge manifest. Always follow the current run’s ODD spec and tool interfaces as the source of truth for required axes and outputs.
