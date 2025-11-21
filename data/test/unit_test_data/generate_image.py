#!/usr/bin/env python3
"""Generate test image for agent testing."""
from PIL import Image, ImageDraw
import os

# Create a simple test image with some colored rectangles
img = Image.new('RGB', (400, 300), color='white')
draw = ImageDraw.Draw(img)

# Add some shapes
draw.rectangle([50, 50, 150, 150], fill='red', outline='darkred')
draw.rectangle([200, 100, 350, 200], fill='blue', outline='darkblue')
draw.ellipse([75, 200, 175, 280], fill='green', outline='darkgreen')

# Add some text
draw.text((150, 10), "Test Image", fill='black')

# Save
os.makedirs('/workspaces/go2-odd-observer/test_data', exist_ok=True)
img.save('/workspaces/go2-odd-observer/test_data/sample_detection.png')
print("Test image created: /workspaces/go2-odd-observer/test_data/sample_detection.png")
