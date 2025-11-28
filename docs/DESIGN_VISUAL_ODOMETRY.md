# Visual Odometry Integration (Data Generation → Agents)

## Goal
Generate visual-odometry (VO) velocities/rotations from the full image sequence during data generation, persist them alongside motion JSON, and surface them to agents as a distinct, labeled source (`visual_odometry_*`), matching existing odometry field names where applicable.

## Inputs
- Full camera image sequence for each scenario window (timestamps preserved).
- Optional BEV image timestamps if needed for pairing, but primary source is camera RGB.
- Existing window index CSV (`index_*.csv`) that maps window_id → file paths.

## Outputs (Schemas)
1) **Per-window VO sample file** (new): `vo_<window_id>.json`
```json
{
  "window_id": "010",
  "source": "visual_odometry",
  "frames": ["cam_sim_1_0_w010.png", "cam_sim_1_0_w011.png"],
  "timestamp_range": [173000.00, 173005.00],
  "vo_linear_mps": { "vx": 0.12, "vy": 0.01, "vz": 0.00 },
  "vo_angular_radps": { "wx": 0.00, "wy": 0.00, "wz": 0.95 },
  "quality": {
    "num_tracks": 126,
    "inlier_ratio": 0.82,
    "rmse_pixels": 0.71,
    "status": "stable"   // stable | marginal | failed
  }
}
```
2) **Merged motion window file** (existing motion JSON) gains a VO block:
```json
"visual_odometry": {
  "vx": 0.12, "vy": 0.01, "vz": 0.00,
  "wx": 0.00, "wy": 0.00, "wz": 0.95,
  "quality": { "num_tracks": 126, "inlier_ratio": 0.82, "rmse_pixels": 0.71, "status": "stable" }
}
```
3) **Index CSV** gains a `visual_odometry` column pointing to `vo_<window_id>.json`.

Field naming aligns with prior odometry placeholders (`odom_vx`…); all VO-specific fields are grouped under `visual_odometry` to keep provenance explicit.

## Algorithm (per scenario)
1. **Frame pairing**: Load ordered camera frames for each window (use timestamps from index CSV). For windows with multiple frames, use consecutive pairs; for single-frame windows, skip VO (mark as failed).
2. **Feature extraction & tracking**:
   - Detect keypoints (ORB/SIFT) on frame t.
   - Track via pyramidal Lucas-Kanade optical flow to frame t+1.
   - Outlier rejection via RANSAC (Essential matrix) to keep inliers.
3. **Motion estimation**:
   - Recover relative pose (R, t) with assumed camera intrinsics (from calibration or default fov/pixels).
   - Scale: derive approximate scale from IMU magnitude envelope or known frame cadence × nominal speed bound (fallback).
   - Compute linear velocity vector (m/s) and angular rates (rad/s) over Δt (timestamps from frames).
4. **Quality metrics**:
   - num_tracks, inlier_ratio, pixel RMSE of flow inliers.
   - Status heuristic: stable if inlier_ratio ≥0.7 and num_tracks ≥80 and rmse ≤2 px; marginal if weaker; failed otherwise.
5. **Failure handling**:
   - If insufficient tracks or bad conditioning, set VO block to zeros and status `failed`; still write file.

## Data Generation Integration
- Extend `scripts/extract_windows.py` (or the current window extractor) to:
  - Load all frames for the window.
  - Run VO pipeline and emit `vo_<window_id>.json`.
  - Add `visual_odometry` column to the index CSV.
  - Inject VO block into the existing motion JSON before writing (so tools get a single merged motion file).
- Configuration:
  - CLI flags: `--enable-visual-odometry` (default on), `--vo-min-tracks`, `--vo-inlier-threshold`, `--vo-intrinsics` (fx, fy, cx, cy), `--vo-scale-mode` (imu|fixed|none).
  - Env/defaults stored near extractor config; ensure deterministic seeds for tests.

## Agent Integration
- **Motion tool**: If `visual_odometry` present, use it to estimate `max_speed_mps`, angular velocity, and to cross-check IMU-derived motion. Keep IMU as primary; VO as supporting evidence. Propagate VO quality in `key_insights`.
- **Collision tool**: Optionally use VO angular rates to corroborate rotation spikes; treat `status=failed` as “no VO signal”.
- **Evaluator**: COD construction can include VO-derived speed/rotation in `measurements` when available (labelled as VO). If VO status is failed/marginal, down-weight.
- **Report**: Mention VO availability/quality in scenario metadata if provided (e.g., “Visual odometry stable (inlier 0.82, 126 tracks)”).

## Knowledge & Documentation
- Add VO brief to knowledge manifest (fundamentals): “Visual odometry is derived from camera optical flow; use as secondary evidence. Check status/quality; treat failed VO as missing.”
- Document intrinsics/assumptions in data generation README.

## VO Quality Tagging (where to flag bad frames)
- **Option A: Preprocessing only (deterministic flags)**  
  - Run cheap image checks per window (blur/sharpness, exposure/low-light, saturation/clipping, motion streaks).  
  - Emit `vo_risk` in metadata (e.g., `{"status":"degraded","blur":"high","low_light":"medium","artifacts":true}`) and store with VO outputs (in `vo_<window>.json` and/or motion JSON).
- **Option B: Dynamic (agent) only**  
  - Perception computes a lightweight blur/exposure score on the frame it already loads, sets a local `vo_status`, and includes it in its output. Slower and less consistent, but no preprocessing dependency.
- **Option C: Both (recommended)**  
  - Do primary tagging in preprocessing, and also allow Perception to add an advisory check. Perception passes `vo_risk` through; Motion/Evaluator use it to decide VO trust (down-weight VO or fall back to IMU-only).

## Testing & Validation
- Unit: synthetic frame pairs with known translation/rotation → verify recovered velocities within tolerance.
- Integration: run extractor on `data/test/sim/sim_test_w010_w011`; confirm `vo_*.json` written, index column populated, motion JSON contains `visual_odometry`.
- Agent smoke: rerun motion agent on updated scenario; ensure it reads VO block without regression when VO is missing/failed.

## Open Decisions (to confirm)
- Camera intrinsics source: existing calibration vs. default focal length/fov.
- Scale strategy: IMU-assisted scale vs. fixed nominal speed per frame cadence.
- Storage location: embed VO block only in motion JSON vs. also keeping separate `vo_*.json` (design above keeps both for clarity).
