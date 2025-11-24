# BEV Auto-Crop Integration Guide

This document explains how to integrate the `auto_crop_bev()` function into existing BEV processing pipelines.

## Overview

The `auto_crop_bev()` function removes empty black borders from bird's-eye-view (BEV) images while preserving occupied regions with a configurable margin. This typically reduces 400x400 BEV images by 50-75%, significantly reducing token usage when processing multiple BEV channels.

## Function Location

```python
from odd_agents.utils import auto_crop_bev
```

## Basic Usage

```python
import cv2
from odd_agents.utils import auto_crop_bev

# Load BEV image
bev_image = cv2.imread("path/to/bev_occupancy.png")

# Crop with default 10% margin
cropped = auto_crop_bev(bev_image)

# Crop with custom 15% margin
cropped = auto_crop_bev(bev_image, margin_percent=0.15)
```

## Integration Options

### Option A: Postprocess Existing BEVs

Create a script to batch-process existing BEV images:

```python
# scripts/postprocess_crop_bevs.py
import cv2
from pathlib import Path
from odd_agents.utils import auto_crop_bev

def crop_all_bevs(data_dir: Path, output_dir: Path):
    """Crop all BEV images in a directory."""
    bev_types = ['occupancy', 'height', 'density', 'roughness']
    
    for window_dir in data_dir.glob("**/w*"):
        for bev_type in bev_types:
            bev_path = window_dir / f"bev_{bev_type}.png"
            if bev_path.exists():
                img = cv2.imread(str(bev_path))
                cropped = auto_crop_bev(img)
                
                output_path = output_dir / window_dir.name / f"bev_{bev_type}.png"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(output_path), cropped)
                
                print(f"Cropped {bev_path.name}: {img.shape[:2]} -> {cropped.shape[:2]}")

if __name__ == "__main__":
    import sys
    data_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    crop_all_bevs(data_dir, output_dir)
```

### Option B: Integrate into BEV Generation

Modify existing BEV rendering/extraction scripts to auto-crop during generation:

```python
# In scripts/render_bev.py or extract_windows.py
import cv2
from odd_agents.utils import auto_crop_bev

def save_bev_image(bev_array, output_path):
    """Render and save BEV image with auto-cropping."""
    # Existing BEV rendering logic
    bev_image = render_to_image(bev_array)
    
    # Add auto-cropping
    cropped_bev = auto_crop_bev(bev_image)
    
    cv2.imwrite(output_path, cropped_bev)
```

### Option C: On-the-Fly Cropping in Agent

Crop BEV images when loading them in the perception agent:

```python
# In odd_agents/tools/perception.py
from odd_agents.utils import auto_crop_bev

def load_bev_for_analysis(bev_path: Path) -> np.ndarray:
    """Load and crop BEV image for agent analysis."""
    bev_image = cv2.imread(str(bev_path))
    return auto_crop_bev(bev_image)
```

## Recommendations

1. **Option A (Postprocessing)** is recommended for existing datasets - one-time batch processing.

2. **Option B (Integration)** is recommended for new data pipelines - ensures all new BEVs are cropped.

3. **Option C (On-the-fly)** is useful for development/testing but adds processing overhead at runtime.

## Performance Impact

| Metric | Before Crop | After Crop | Improvement |
|--------|-------------|------------|-------------|
| Image Size | 400x400 | ~150x250 | ~60% smaller |
| Token Usage | ~1000 tokens/image | ~400 tokens/image | ~60% reduction |
| 4 BEV Channels | ~4000 tokens | ~1600 tokens | ~2400 tokens saved |

## Edge Cases Handled

- **Empty BEV**: Returns original image (no content to crop)
- **Full BEV**: Returns original image (nothing to remove)
- **Single pixel**: Returns minimum crop with margin
- **Grayscale/RGB**: Handles both formats automatically

## Testing

Run the test suite to verify the function:

```bash
pytest tests/test_bev_cropping.py -v
```
