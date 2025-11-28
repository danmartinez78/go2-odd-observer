# Sensor Interpretation (Core)

**Purpose:** Shared, robot-agnostic guidance for interpreting BEV, camera, and IMU data. Keep prompts slim by referencing this doc; do not override per-run ODD spec or tool outputs.

**Version:** v1.1.0 (knowledge-only)

## BEV Basics
- **Channels:**
  - **Occupancy:** Obstacles only (points >10cm above ground filtered). Use for collision detection, obstacle density, path clearance.
  - **Height:** All points including ground (full terrain elevation). Grayscale: darker=lower, brighter=higher. Use for terrain analysis, slope detection, elevation changes.
  - **Roughness:** All points (terrain height variance per pixel). Bright=rough/variable, dark=smooth/flat. Use for surface quality, traversability assessment.
- **Key insight:** Height and roughness show the full terrain (richer signal), while occupancy is filtered to show only obstacles above ground level.
- **Cropping:** BEVs are auto-cropped to remove empty borders; focus on the active region.
- **Scale:** 0.05m/pixel (20px = 1m), ~20m × 20m coverage, robot at center facing up.
- **Patterns to trust:** stable high-occupancy blobs near path, consistent height gradients for ramps/curbs, roughness spikes for uneven terrain.
- **Common pitfalls:** shadows/texture in camera ≠ occupancy; sparse speckle noise near edges; LiDAR dropouts can mimic empty space.
- **Directional conventions:** use provided window metadata for orientation; do not assume north/up without metadata.
- **Real vs Sim:** Real LiDAR data is noisier than simulation; expect more texture/speckle in real BEVs.

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

## Sim vs Real Data Characteristics
- **Simulation:** Clean, idealized sensor data. Uniform lighting, perfect textures, low noise.
- **Real-world:** Expect sensor noise, lighting variation, motion blur, occasional artifacts.
- **LiDAR:** Real scans are noisier with more speckle; sim scans are clean geometric shapes.
- **Camera:** Real images have natural imperfections, compression artifacts, exposure variation.
- **IMU:** Real IMU has more baseline noise; sim IMU is smoother.
- When analyzing data, consider whether observed patterns are sensor artifacts vs actual environment features.

## LiDAR Scan Types
- **Single scan:** One LiDAR sweep at a point in time. Sparser coverage, shows instantaneous view.
- **Accumulated map:** Multiple scans aggregated over time/motion. Denser coverage, shows traversed area.
- BEV interpretation differs: accumulated maps show more complete environment but may have motion artifacts if robot moved significantly.

## LiDAR Self-Hits
- **What are self-hits?** LiDAR beams can reflect off the robot's own body (legs, chassis) and appear as detected points. These "self-hits" show up in the point cloud and BEV images.
- **How they appear:** Small clusters of occupied pixels very close to the robot position (BEV center). Often appear as a consistent pattern across frames since the robot geometry is fixed.
- **Interpretation guidance:** When analyzing BEV occupancy near the robot center, consider that very small, close-proximity clusters may be self-hits rather than external obstacles. This is especially relevant for collision or clearance analysis—a persistent pattern at the same relative position across multiple windows is more likely self-hit than a real obstacle.
- **Not a strict rule:** Context matters. A genuine obstacle can also be very close to the robot. Use temporal consistency, motion context, and camera imagery to disambiguate when needed.

## Optional Profiles (robot/app-specific)
- Profiles add robot-specific hardware details (sensor specs, known artifacts, FOV). Profiles should not redefine channel meanings—only add platform context.

**Usage reminder:** Cite sections via the knowledge manifest. Always follow the current run’s ODD spec and tool interfaces as the source of truth for required axes and outputs.
