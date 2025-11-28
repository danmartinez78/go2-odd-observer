# LiDAR Odometry Integration (Per-Scan Clouds)

## Goal
Compute LiDAR odometry (LO) from per-scan point clouds (base_link if available, else odom + TF) during data generation. Produce velocity/rotation estimates per window, align with existing odometry-style fields, and label provenance as `lidar_odometry`.

## Preconditions
- **Sim:** already have per-scan, robot-centric clouds (base_link).
- **Real:** must have per-scan clouds (not accumulated) and TF for odom→base_link over time. No calibration beyond TF needed.
- Window index CSV provides timestamps for each window.

## Outputs (Schemas)
1) **Per-window LO file:** `lo_<window_id>.json`
```json
{
  "window_id": "010",
  "source": "lidar_odometry",
  "scans": ["pc_w010_00.pcd", "pc_w010_01.pcd"],   // references to scan files or bag offsets
  "timestamp_range": [173000.0, 173002.0],
  "lo_linear_mps": { "vx": 0.05, "vy": -0.01, "vz": 0.0 },
  "lo_angular_radps": { "wx": 0.0, "wy": 0.0, "wz": 0.12 },
  "quality": {
    "num_pairs": 3,
    "fitness_mean": 0.82,
    "rmse_mean": 0.04,
    "status": "stable"   // stable | marginal | failed
  }
}
```
2) **Merged motion JSON block:** add `lidar_odometry` with same fields/quality, so tools read a single motion file.
3) **Index CSV:** add a `lidar_odometry` column pointing to `lo_<window_id>.json`.

## Algorithm (per window)
1. **Scan selection:** collect scans whose timestamps fall in the window. If <2 scans → mark LO as failed (all zeros, status `failed`).
2. **Frame normalization:**
   - If scans already in base_link, use directly.
   - If odom-frame scans, transform each scan to base_link at its timestamp using TF (odom→base_link).
3. **Pairwise registration:**
   - Use voxel downsample (e.g., 0.05–0.1 m) for speed.
   - Estimate normals; run point-to-plane ICP (or NDT) between consecutive scans.
   - Extract relative pose ΔR, Δt; compute Δt time from scan timestamps.
4. **Velocity/rotation estimation:**
   - Linear velocity = Δt_vec / Δtime.
   - Angular rates from ΔR (e.g., log map) / Δtime.
   - Aggregate across pairs (mean/median); record per-pair fitness/RMSE.
5. **Quality metrics:**
   - num_pairs, mean fitness, mean RMSE.
   - Status heuristic: stable if fitness ≥0.7 and rmse ≤0.1 m; marginal if weaker; failed if ICP diverges or insufficient pairs.
6. **Failure handling:**
   - On ICP failure or insufficient overlap: zero velocities, status `failed`, still emit file.

## Data Generation Integration
- Extend `extract_windows.py` (real/sim per-scan path):
  - Gather scans in window; transform to base_link if needed.
  - Run LO pipeline; write `lo_<window>.json`; inject `lidar_odometry` block into motion JSON; add index column.
  - CLI flags: `--enable-lidar-odometry` (default on when per-scan available), `--lo-voxel-size`, `--lo-max-pairs`, `--lo-min-fitness`, `--lo-frame` (base_link|odom).

## Agent Integration
- **Motion tool:** consume `lidar_odometry` if present; use to refine `max_speed_mps` and angular velocity; cross-check with IMU and VO; if `status=failed`, ignore LO.
- **Collision tool:** can use angular spikes from LO as corroboration; ignore if failed.
- **Evaluator:** include LO-derived speeds/rotations in `measurements` when status stable/marginal; down-weight or skip if failed.
- **Report:** optional metadata note (“LiDAR odometry stable (fitness 0.82, rmse 0.04 m)”).

## Knowledge & Documentation
- Add to knowledge manifest (fundamentals): “LiDAR odometry uses scan-to-scan ICP; treat as secondary evidence. Check quality (fitness/RMSE/status); failed LO = missing.”
- Document defaults and assumptions in data generation docs when implemented (voxel size, frame handling, fitness thresholds).

## Quality/Artifact Handling
- Preprocess scans: remove NaNs/inf, optional ground removal before ICP to reduce drift on planar surfaces.
- If only few scans per window, lower confidence; encode in status/quality.
- For real data, ensure TF is continuous; gaps → mark LO as marginal/failed.

## Testing & Validation
- Unit/integration: synthetic or controlled trajectory with known motion → check LO velocities within tolerance.
- Run on `data/test/sim/sim_test_w010_w011` (sim path) to verify end-to-end.
- Once real per-scan exists: run on a short bag, inspect LO outputs, confirm motion JSON embedding and index column wiring; check stability vs. IMU/VO.
