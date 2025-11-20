# FIXED Vision, Terrain, Collision Agent Definitions
# Copy these cells into the notebook to replace the existing agent definitions

# ============================================================================
# VISION ANALYZER - FIXED
# ============================================================================

vision_agent_fixed = Agent(
    name="Vision_Analyzer",
    model=Gemini(
        model=GEMINI_MODEL,
        api_key=GOOGLE_API_KEY
    ),
    tools=[scenario_data_tool, get_image_tool],
    instruction="""You are a computer vision expert for mobile robots analyzing camera images.

STEP-BY-STEP INSTRUCTIONS:
1. Call get_scenario_data() - this returns a list of windows
2. For EACH window in the response, you MUST call get_window_image() exactly like this:
   get_window_image(window_id="006", image_type="camera")
   Do NOT use get_window_image("camera") or other formats.
3. When you get the camera image, analyze it FOR THAT WINDOW ONLY
4. Extract: lighting_class, humans_visible, humans_very_close, environment_type, detected_hazards
5. After analyzing ALL windows, output JSON with results for each

CRITICAL: image_type parameter MUST be exactly: "camera"
If image_type is "Camera" or "CAMERA" or "camera_image", the tool will return an error.

Output this JSON structure after analyzing all windows:
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

# ============================================================================
# TERRAIN ANALYZER - FIXED
# ============================================================================

terrain_agent_fixed = Agent(
    name="Terrain_Analyzer",
    model=Gemini(
        model=GEMINI_MODEL,
        api_key=GOOGLE_API_KEY
    ),
    tools=[scenario_data_tool, get_image_tool],
    instruction="""You are a terrain analysis expert analyzing LiDAR Bird's Eye View (BEV) maps.

STEP-BY-STEP INSTRUCTIONS:
1. Call get_scenario_data() - this returns a list of windows
2. For EACH window in the response, you MUST call get_window_image() FOUR times with these EXACT parameters:
   - get_window_image(window_id="006", image_type="bev_occupancy")
   - get_window_image(window_id="006", image_type="bev_height")
   - get_window_image(window_id="006", image_type="bev_density")
   - get_window_image(window_id="006", image_type="bev_roughness")
3. When you get each BEV image, analyze it immediately
4. Use all four BEV maps to determine: terrain_roughness_class, occupancy_ratio, obstacle_density, traversability_score
5. After analyzing ALL windows, output JSON with results for each

CRITICAL: image_type parameter MUST be EXACTLY one of:
  - "bev_occupancy" (not "BEV", not "bev", not "occupancy", exactly "bev_occupancy")
  - "bev_height" (not "BEV", not "height", exactly "bev_height")
  - "bev_density" (not "BEV", not "density", exactly "bev_density")
  - "bev_roughness" (not "BEV", not "roughness", exactly "bev_roughness")

If you use "BEV" or any variation, the tool will return an error.

Output this JSON structure after analyzing all windows:
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

# ============================================================================
# COLLISION DETECTOR - FIXED
# ============================================================================

collision_agent_fixed = Agent(
    name="Collision_Detector",
    model=Gemini(
        model=GEMINI_MODEL,
        api_key=GOOGLE_API_KEY
    ),
    tools=[scenario_data_tool, get_image_tool],
    instruction="""You are a collision detection expert analyzing multiple sensor images.

STEP-BY-STEP INSTRUCTIONS:
1. Call get_scenario_data() - this returns a list of windows
2. For EACH window in the response, you MUST call get_window_image() THREE times with these EXACT parameters:
   - get_window_image(window_id="006", image_type="camera")
   - get_window_image(window_id="006", image_type="bev_occupancy")
   - get_window_image(window_id="006", image_type="bev_height")
3. When you get each image, analyze it immediately for collision risks
4. Look for obstacles, walls, and other collision hazards in all three image types
5. Determine: collision_suspected, collision_confidence, collision_type, risk_level
6. After analyzing ALL windows, output JSON with results for each

CRITICAL: image_type parameter MUST be EXACTLY one of:
  - "camera" (not "Camera", not "cam", exactly "camera")
  - "bev_occupancy" (not "BEV", not "occupancy", exactly "bev_occupancy")
  - "bev_height" (not "BEV", not "height", exactly "bev_height")

If you use wrong names like "BEV" or "Camera", the tool will return an error.

Output this JSON structure after analyzing all windows:
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

print("✅ Fixed agents defined: vision_agent_fixed, terrain_agent_fixed, collision_agent_fixed")
print("\nTo use these in your workflow:")
print("1. Replace vision_agent with vision_agent_fixed")
print("2. Replace terrain_agent with terrain_agent_fixed")
print("3. Replace collision_agent with collision_agent_fixed")
print("4. In parallel_sensor_team, update the sub_agents list to use the fixed versions")
