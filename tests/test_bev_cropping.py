"""
Unit tests for BEV auto-crop functionality.
"""

import pytest
import cv2
import numpy as np
from pathlib import Path

# Import using importlib to avoid dependency issues
import importlib.util

spec = importlib.util.spec_from_file_location(
    "utils",
    Path(__file__).parent.parent / "odd_agents" / "utils.py"
)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
auto_crop_bev = utils.auto_crop_bev

FIXTURES = Path(__file__).parent / "fixtures" / "bev_samples"

# Verify fixtures exist
if not FIXTURES.exists():
    raise FileNotFoundError(
        f"Test fixtures directory not found at {FIXTURES}. "
        "Please ensure BEV sample images are available in tests/fixtures/bev_samples/"
    )


def test_crop_reduces_size():
    """Cropped BEV should be smaller than original."""
    img = cv2.imread(str(FIXTURES / "real_01_w005_occupancy.png"))
    cropped = auto_crop_bev(img)

    assert cropped.shape[0] < img.shape[0], "Height should be smaller"
    assert cropped.shape[1] < img.shape[1], "Width should be smaller"
    assert cropped.shape[2] == img.shape[2], "Channels should match"


def test_crop_preserves_content():
    """All non-black pixels should be preserved."""
    img = cv2.imread(str(FIXTURES / "real_01_w005_occupancy.png"))
    original_white_pixels = np.sum(img > 10)  # Count non-background

    cropped = auto_crop_bev(img)
    cropped_white_pixels = np.sum(cropped > 10)

    # Should preserve all content (within small margin for edge effects)
    assert cropped_white_pixels >= original_white_pixels * 0.95


def test_empty_bev():
    """Empty BEV should return original."""
    empty = np.zeros((400, 400, 3), dtype=np.uint8)
    cropped = auto_crop_bev(empty)

    assert cropped.shape == empty.shape


def test_full_bev():
    """Fully occupied BEV should return original."""
    full = np.ones((400, 400, 3), dtype=np.uint8) * 255
    cropped = auto_crop_bev(full)

    assert cropped.shape == full.shape


def test_margin_applied():
    """Margin should be added around occupied region."""
    # Create 100x100 white square in center of 400x400 black image
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    img[150:250, 150:250] = 255

    cropped = auto_crop_bev(img, margin_percent=0.1)

    # Expected: 100px region + 10% margin on each side = ~120px
    # (actual size depends on implementation)
    assert cropped.shape[0] > 100, "Should be larger than bare region"
    assert cropped.shape[0] < 200, "Should be smaller than excessive crop"


def test_all_sample_images():
    """All sample images should crop successfully."""
    for img_path in FIXTURES.glob("*.png"):
        if img_path.stem == "README":
            continue

        img = cv2.imread(str(img_path))
        cropped = auto_crop_bev(img)

        assert cropped is not None, f"Failed on {img_path.name}"
        assert cropped.shape[0] > 0, f"Empty result for {img_path.name}"
        assert cropped.shape[1] > 0, f"Empty result for {img_path.name}"


def test_square_aspect_ratio():
    """Cropped image should be square."""
    img = cv2.imread(str(FIXTURES / "real_01_w005_occupancy.png"))
    cropped = auto_crop_bev(img)

    assert cropped.shape[0] == cropped.shape[1], "Cropped image should be square"


def test_grayscale_input():
    """Function should handle grayscale input."""
    img = cv2.imread(str(FIXTURES / "real_01_w005_occupancy.png"), cv2.IMREAD_GRAYSCALE)
    cropped = auto_crop_bev(img)

    assert len(cropped.shape) == 2, "Grayscale output should be 2D"
    assert cropped.shape[0] < img.shape[0], "Height should be smaller"


def test_none_input():
    """Function should handle None input gracefully."""
    result = auto_crop_bev(None)
    assert result is None


def test_single_pixel_occupied():
    """Single pixel occupied region should return reasonable size."""
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    img[200, 200] = 255  # Single white pixel

    cropped = auto_crop_bev(img)

    # Should return a small crop (not crash)
    assert cropped is not None
    assert cropped.shape[0] > 0
    assert cropped.shape[1] > 0
    # Should have some margin around the single pixel
    assert cropped.shape[0] >= 2


def test_custom_margin():
    """Custom margin percent should be applied."""
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    img[150:250, 150:250] = 255  # 100x100 white square

    cropped_10 = auto_crop_bev(img, margin_percent=0.1)
    cropped_20 = auto_crop_bev(img, margin_percent=0.2)

    # Larger margin should produce larger crop
    assert cropped_20.shape[0] > cropped_10.shape[0]


def test_size_reduction_percentage():
    """Typical BEVs should reduce by 50-75%."""
    img = cv2.imread(str(FIXTURES / "real_01_w005_occupancy.png"))
    cropped = auto_crop_bev(img)

    size_reduction = 1 - (cropped.size / img.size)

    # Should reduce size by at least 50%
    assert size_reduction >= 0.5, f"Expected >50% reduction, got {size_reduction*100:.1f}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
