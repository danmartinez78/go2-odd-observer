# FIXED AGENT DEFINITIONS

## Root Cause Analysis

The agents were calling `get_window_image()` with WRONG parameter names:
- Terrain was calling: `get_window_image(image_type="BEV")`  ❌
- Should call: `get_window_image(window_id="006", image_type="bev_occupancy")` ✅

## Fixed Instructions

### 1. Vision Analyzer - FIXED

Replace the entire instruction in the notebook cell with:

```python
vision_agent = Agent(
    name="Vision_Analyzer",
    model=Gemini(
        model=GEMINI_MODEL,
        api_key=GOOGLE_API_KEY
    ),
    tools=[scenario_data_tool, get_image_tool],
    instruction="""You are a computer vision expert for mobile robots analyzing camera images.

STEP-BY-STEP:
1. Call get_scenario_data() first
2. For EACH window returned, call: get_window_image(window_id="006", image_type="camera")
3. Analyze each camera image immediately
4. Extract: lighting_class, humans_visible, humans_very_close, environment_type, detected_hazards
5. Return JSON with all window results

CRITICAL: image_type MUST be exactly "camera" (not "Camera", not "camera_image")

Output JSON after analyzing ALL windows:
{
  "windows": [
    {
      "window_id": "006",
      "lighting_class": "bright",
      "humans_visible": false,
      "humans_very_close": false,
      "environment_type": "office",
      "detected_hazards": []
    }
  ]
}""",
    output_key="vision_features"
)
```

### 2. Terrain Analyzer - FIXED

Replace the entire instruction with:

```python
terrain_agent = Agent(
    name="Terrain_Analyzer",
    model=Gemini(
        model=GEMINI_MODEL,
        api_key=GOOGLE_API_KEY
    ),
    tools=[scenario_data_tool, get_image_tool],
    instruction="""You are a terrain analysis expert analyzing LiDAR Bird's Eye View (BEV) maps.

STEP-BY-STEP:
1. Call get_scenario_data() first
2. For EACH window, call get_window_image() FOUR times:
   - get_window_image(window_id="006", image_type="bev_occupancy")
   - get_window_image(window_id="006", image_type="bev_height")
   - get_window_image(window_id="006", image_type="bev_density")
   - get_window_image(window_id="006", image_type="bev_roughness")
3. Analyze each BEV map immediately
4. Determine: terrain_roughness_class, occupancy_ratio, obstacle_density, traversability_score
5. Return JSON with all window results

CRITICAL: image_type MUST be EXACTLY one of these four:
  - "bev_occupancy" (NOT "BEV", NOT "occupancy")
  - "bev_height" (NOT "BEV", NOT "height")
  - "bev_density" (NOT "BEV", NOT "density")
  - "bev_roughness" (NOT "BEV", NOT "roughness")

Output JSON after analyzing ALL windows:
{
  "windows": [
    {
      "window_id": "006",
      "terrain_roughness_class": "moderate",
      "occupancy_ratio": 0.25,
      "obstacle_density": 0.1,
      "traversability_score": 0.8,
      "hazard_regions": []
    }
  ]
}""",
    output_key="terrain_features"
)
```

### 3. Collision Detector - FIXED

Replace the entire instruction with:

```python
collision_agent = Agent(
    name="Collision_Detector",
    model=Gemini(
        model=GEMINI_MODEL,
        api_key=GOOGLE_API_KEY
    ),
    tools=[scenario_data_tool, get_image_tool],
    instruction="""You are a collision detection expert analyzing multiple sensor images.

STEP-BY-STEP:
1. Call get_scenario_data() first
2. For EACH window, call get_window_image() THREE times:
   - get_window_image(window_id="006", image_type="camera")
   - get_window_image(window_id="006", image_type="bev_occupancy")
   - get_window_image(window_id="006", image_type="bev_height")
3. Analyze each image immediately for collision risks
4. Look for obstacles, walls, and hazards
5. Determine: collision_suspected, collision_confidence, collision_type, risk_level
6. Return JSON with all window results

CRITICAL: image_type MUST be EXACTLY one of:
  - "camera" (NOT "Camera")
  - "bev_occupancy" (NOT "BEV", NOT "occupancy")
  - "bev_height" (NOT "BEV", NOT "height")

Output JSON after analyzing ALL windows:
{
  "windows": [
    {
      "window_id": "006",
      "collision_suspected": false,
      "collision_confidence": 0.0,
      "collision_type": "none",
      "risk_level": "safe",
      "notes": "No obstacles detected"
    }
  ]
}""",
    output_key="collision_features"
)
```

## Summary

The key issue was that the agents were not calling `get_window_image()` with the correct function signature and parameter values. The tool requires:

```python
get_window_image(window_id="<id>", image_type="<exact_type>")
```

Valid `image_type` values:
- `"camera"` - Front camera image
- `"bev_occupancy"` - Bird's Eye View occupancy map
- `"bev_height"` - BEV height map
- `"bev_density"` - BEV density map
- `"bev_roughness"` - BEV roughness map

❌ Wrong names that cause errors:
- `"BEV"` (too generic)
- `"Camera"` (capitalized)
- `"camera_image"` (wrong name)
- `"occupancy"` (needs `bev_` prefix)

The fixed instructions explicitly show the exact function calls to make, preventing the agents from guessing or using wrong parameter names.
