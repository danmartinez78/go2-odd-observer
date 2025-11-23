"""
Generate Demo Data for ODD/COD Workflow

Creates sample window data for testing the Jupyter notebook without
requiring actual ROS bag processing.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Configuration
OUTPUT_DIR = Path("data/processed/runs/demo_run")
NUM_WINDOWS = 10
WINDOW_LENGTH = 2.0  # seconds
STRIDE = 1.0  # seconds

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_motion_data(window_id: int, is_violation: bool = False) -> dict:
    """Generate synthetic motion data for a window."""
    num_samples = 20
    timestamps = np.linspace(0, WINDOW_LENGTH, num_samples).tolist()
    
    if is_violation:
        # Generate data with ODD violations
        cmd_vx = (np.random.rand(num_samples) * 0.5 + 1.8).tolist()  # High speed
        odom_vx = (cmd_vx + np.random.randn(num_samples) * 0.2).tolist()
        roll = (np.random.randn(num_samples) * 5 + 18).tolist()  # High roll
        pitch = (np.random.randn(num_samples) * 5 + 2).tolist()
    else:
        # Generate compliant data
        cmd_vx = (np.random.rand(num_samples) * 0.5 + 0.8).tolist()
        odom_vx = (cmd_vx + np.random.randn(num_samples) * 0.05).tolist()
        roll = (np.random.randn(num_samples) * 2 + 3).tolist()
        pitch = (np.random.randn(num_samples) * 2 + 1).tolist()
    
    return {
        "timestamps": timestamps,
        "cmd_vx": cmd_vx,
        "cmd_wz": (np.random.randn(num_samples) * 0.1).tolist(),
        "odom_vx": odom_vx,
        "odom_wz": (np.random.randn(num_samples) * 0.1).tolist(),
        "roll": roll,
        "pitch": pitch,
        "yaw": (np.random.rand(num_samples) * 360).tolist(),
        "accel_x": (np.random.randn(num_samples) * 0.5).tolist(),
        "accel_y": (np.random.randn(num_samples) * 0.3).tolist(),
        "accel_z": (np.random.randn(num_samples) * 0.2 + 9.81).tolist(),
    }


def generate_camera_image(window_id: int, width: int = 640, height: int = 480) -> Image.Image:
    """Generate a synthetic camera image."""
    # Create a simple gradient image to simulate indoor scene
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    # Background gradient (floor to ceiling)
    for y in range(height):
        color_val = int(120 + (y / height) * 100)
        draw.rectangle([(0, y), (width, y+1)], fill=(color_val, color_val, color_val))
    
    # Add some "obstacles" or features
    for i in range(3):
        x = np.random.randint(50, width - 50)
        y = np.random.randint(height // 2, height - 50)
        size = np.random.randint(30, 80)
        color = tuple(np.random.randint(50, 200, 3).tolist())
        draw.rectangle([x, y, x + size, y + size], fill=color)
    
    # Add text overlay
    try:
        draw.text((10, 10), f"Demo Window {window_id}", fill=(255, 255, 255))
    except:
        pass  # Font may not be available
    
    return img


def generate_bev_image(channel: str, window_id: int, size: int = 400) -> Image.Image:
    """Generate a synthetic BEV image for a specific channel."""
    img = Image.new('L', (size, size))
    draw = ImageDraw.Draw(img)
    
    if channel == 'occupancy':
        # Binary presence grid
        for _ in range(50):
            x, y = np.random.randint(0, size, 2)
            radius = np.random.randint(2, 10)
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=255)
    
    elif channel == 'height':
        # Height map (gradient with some features)
        for y in range(size):
            for x in range(size):
                val = int(128 + 30 * np.sin(x / 50) + 30 * np.sin(y / 50))
                img.putpixel((x, y), max(0, min(255, val)))
    
    elif channel == 'density':
        # Density map
        for _ in range(100):
            x, y = np.random.randint(0, size, 2)
            radius = np.random.randint(5, 20)
            intensity = np.random.randint(100, 200)
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=intensity)
    
    elif channel == 'roughness':
        # Roughness map (mostly smooth)
        base = Image.new('L', (size, size), 50)
        for _ in range(20):
            x, y = np.random.randint(0, size, 2)
            radius = np.random.randint(3, 15)
            draw = ImageDraw.Draw(base)
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=150)
        img = base
    
    return img


def main():
    """Generate complete demo dataset."""
    print("Generating demo data...")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Generate windows
    index_data = []
    
    for i in range(NUM_WINDOWS):
        window_id = i
        start_time = i * STRIDE
        end_time = start_time + WINDOW_LENGTH
        
        # Make windows 7 and 8 violations for demo
        is_violation = i in [7, 8]
        
        # Generate motion data
        motion_data = generate_motion_data(window_id, is_violation)
        motion_path = f"motion_demo_run_w{window_id:03d}.json"
        with open(OUTPUT_DIR / motion_path, 'w') as f:
            json.dump(motion_data, f, indent=2)
        
        # Generate camera image
        cam_img = generate_camera_image(window_id)
        cam_path = f"cam_demo_run_w{window_id:03d}.png"
        cam_img.save(OUTPUT_DIR / cam_path)
        
        # Generate BEV images for all channels
        bev_base_path = f"bev_demo_run_w{window_id:03d}.png"
        for channel in ['occupancy', 'height', 'density', 'roughness']:
            bev_img = generate_bev_image(channel, window_id)
            bev_channel_path = f"bev_{channel}_demo_run_w{window_id:03d}.png"
            bev_img.save(OUTPUT_DIR / bev_channel_path)
        
        # Also save a default BEV (occupancy) for backward compatibility
        bev_img = generate_bev_image('occupancy', window_id)
        bev_img.save(OUTPUT_DIR / bev_base_path)
        
        # Add to index
        index_data.append({
            'window_id': window_id,
            'start_time': start_time,
            'end_time': end_time,
            'motion_path': motion_path,
            'cam_image_path': cam_path,
            'bev_image_path': bev_base_path,
        })
        
        print(f"  Generated window {window_id}")
    
    # Save index CSV
    index_df = pd.DataFrame(index_data)
    index_path = OUTPUT_DIR / "index_demo_run.csv"
    index_df.to_csv(index_path, index=False)
    print(f"\n✓ Generated {len(index_data)} windows")
    print(f"✓ Index saved to: {index_path}")
    
    # Generate manifest
    manifest_data = [{
        'run_id': 'demo_run',
        'is_sim': True,
        'environment': 'demo',
        'notes': 'Synthetic demo data for testing workflow',
    }]
    manifest_df = pd.DataFrame(manifest_data)
    manifest_path = Path("data/processed/manifest.csv")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_df.to_csv(manifest_path, index=False)
    print(f"✓ Manifest saved to: {manifest_path}")
    
    print("\n✓ Demo data generation complete!")
    print(f"\nYou can now run the Jupyter notebook with this demo scenario.")


if __name__ == "__main__":
    main()
