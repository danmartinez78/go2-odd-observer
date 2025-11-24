# BEV Sample Images for Testing

Sample bird's-eye-view (BEV) images used for testing the auto-crop functionality.

## Files

### Real Robot Samples (collection_20251122_173442, window 5)
- `real_01_w005_occupancy.png` - Binary obstacle map (white = occupied)
- `real_01_w005_height.png` - Height map (brighter = taller obstacles)
- `real_01_w005_density.png` - Point cloud density (brighter = more points)
- `real_01_w005_roughness.png` - Terrain roughness metric

### Simulation Sample (sim scenario, window 10)
- `sim_01_w010_occupancy.png` - Binary obstacle map from simulation

## Characteristics

All BEVs are 400x400 pixels with:
- **Robot at center** (200, 200)
- **Facing upward** (top of image = forward direction)
- **Black background** for empty space
- **50-75% empty borders** (target for cropping)

## Expected Cropping Behavior

Auto-crop should:
1. Find bounding box of non-black pixels
2. Add 10% margin around occupied region
3. Maintain aspect ratio (square BEVs)
4. Handle edge cases:
   - Empty BEV (all black) → return as-is
   - Full BEV (no empty space) → return as-is
   - Sparse BEV (few points) → reasonable crop with margin

## Usage in Tests

```python
import cv2
from pathlib import Path

fixtures_dir = Path(__file__).parent / "fixtures" / "bev_samples"
occupancy = cv2.imread(str(fixtures_dir / "real_01_w005_occupancy.png"))
cropped = auto_crop_bev(occupancy)

# Verify cropped is smaller
assert cropped.shape[0] < occupancy.shape[0]
assert cropped.shape[1] < occupancy.shape[1]
```
