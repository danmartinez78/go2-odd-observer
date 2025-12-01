# Adapting ODD Observer to New Robots

This guide explains how to apply the ODD Observer pipeline to a different robot platform or application domain.

## Overview

The ODD Observer system is designed to be **robot and application agnostic** at the reasoning level. The agents work with:
- **Camera images** (any RGB camera)
- **LiDAR BEV images** (bird's eye view from 3D point clouds)
- **IMU/motion data** (acceleration, angular velocity, orientation)

To adapt for a new robot, you need to:
1. Prepare your sensor data in the expected format
2. Create a robot profile for the knowledge layer
3. Write an appropriate ODD specification
4. (Optional) Tune tool thresholds for your platform

---

## 1. Data Format Requirements

### Directory Structure

Each scenario should be a directory with these files per time window:

```
my_scenario/
├── index_my_scenario.csv          # Window index file
├── cam_my_scenario_w000.png       # Camera image (window 0)
├── bev_occupancy_my_scenario_w000.png  # LiDAR BEV - obstacles only
├── bev_height_my_scenario_w000.png     # LiDAR BEV - terrain height
├── bev_roughness_my_scenario_w000.png  # LiDAR BEV - terrain roughness
├── motion_my_scenario_w000.json   # IMU/motion data
├── cam_my_scenario_w001.png
├── ...
```

### Index CSV Format

```csv
window_id,start_time,end_time,motion_path,cam_image_path,bev_occupancy_path,bev_height_path,bev_roughness_path
0,1234567890.0,1234567892.0,motion_my_scenario_w000.json,cam_my_scenario_w000.png,bev_occupancy_my_scenario_w000.png,bev_height_my_scenario_w000.png,bev_roughness_my_scenario_w000.png
1,1234567891.0,1234567893.0,motion_my_scenario_w001.json,cam_my_scenario_w001.png,...
```

### Camera Images

- **Format:** PNG or JPEG
- **Resolution:** Any (typically 640x480 to 1920x1080)
- **Content:** Forward-facing RGB image
- **Agents use this for:** Environment classification, human/animal detection, lighting assessment

### BEV Images

Three channels, each as a grayscale PNG:

| Channel | Content | Pixel Meaning |
|---------|---------|---------------|
| **Occupancy** | Obstacles only (ground filtered) | Brighter = obstacle present |
| **Height** | Full terrain elevation | Grayscale mapped to height range |
| **Roughness** | Height variance per cell | Brighter = rougher terrain |

- **Resolution:** Typically 256x256 pixels
- **Coverage:** Typically 10m x 10m centered on robot
- **Robot position:** Center of image, facing "up"

If you don't have LiDAR, you can:
- Generate synthetic BEV from depth cameras
- Use blank images (agents will note "no LiDAR data")
- Focus on camera-only analysis

### Motion JSON Format

```json
{
  "window_id": 0,
  "start_time": 1234567890.0,
  "end_time": 1234567892.0,
  "samples": [
    {
      "timestamp": 1234567890.1,
      "pos_x": 0.0,
      "pos_y": 0.0,
      "pos_z": 0.0,
      "roll": 0.0,
      "pitch": 0.0,
      "yaw": 0.0,
      "accel_x": 0.1,
      "accel_y": 0.0,
      "accel_z": 9.8,
      "gyro_x": 0.0,
      "gyro_y": 0.0,
      "gyro_z": 0.0
    }
  ],
  "derived_speed": 0.5,
  "derived_yaw_rate": 0.1
}
```

Key fields:
- **Position** (`pos_x/y/z`): Odometry position in meters
- **Orientation** (`roll/pitch/yaw`): Radians
- **IMU** (`accel_x/y/z`, `gyro_x/y/z`): Raw IMU readings
- **Derived** (`derived_speed`, `derived_yaw_rate`): Computed from position differentiation

---

## 2. Creating a Robot Profile

Robot profiles provide context to agents about typical operating patterns.

### Location

`docs/agent_knowledge/profiles/ROBOT_<NAME>_PROFILE.md`

### Template

```markdown
# <Robot Name> Robot Profile

**Version:** v1.0.0  
**Changelog:** Initial profile for <Robot Name>

## Platform Overview

<Brief description of the robot, its purpose, and typical deployment>

## Physical Specifications

| Attribute | Value |
|-----------|-------|
| Dimensions (L×W×H) | X × Y × Z cm |
| Weight | X kg |
| Max Speed | X m/s |
| Degrees of Freedom | X |
| Locomotion Type | wheeled/tracked/legged |

## Sensor Suite

| Sensor | Model/Type | Purpose |
|--------|------------|---------|
| Camera | <model> | Visual perception |
| LiDAR | <model> | 3D mapping, obstacle detection |
| IMU | <model> | Motion state estimation |

## Typical Operating Patterns

### Indoor Operation
- Typical speed: X-Y m/s
- Acceleration patterns: <description>
- Common environments: <list>

### Terrain Handling
- Smooth floors: <performance>
- Transitions: <how it handles doorways, ramps>
- Limits: <what terrain it cannot handle>

## Known Limitations

- <Limitation 1>
- <Limitation 2>

## ODD Considerations

When defining ODDs for this robot, consider:
- <Consideration 1>
- <Consideration 2>
```

### Registering the Profile

Add to `docs/agent_knowledge/KNOWLEDGE_MANIFEST.md`:

```markdown
| `ref:robot_<name>_profile` | profiles/ROBOT_<NAME>_PROFILE.md | Robot-specific patterns |
```

---

## 3. Writing an ODD Specification

The ODD (Operational Design Domain) defines safe operating boundaries in **natural language**. The ODD Spec Agent parses this into structured axes that downstream agents use for compliance evaluation.

### Writing Effective Natural Language ODDs

The key to a good ODD spec is **clarity and measurability**. Agents need concrete thresholds they can evaluate against sensor data.

#### ✅ Good ODD Statements

| Statement | Why It Works |
|-----------|--------------|
| "Maximum speed: 2.5 m/s" | Clear numeric threshold |
| "Gentle ramps (<15 degree incline)" | Specific angle limit |
| "Humans within 0.5-1m while navigating = OUT OF ODD" | Explicit boundary + consequence |
| "Bright to moderate lighting is ideal; pitch-black rooms are outside operational limits" | Range with explicit exclusion |
| "Indoor warehouse with concrete floors, artificial lighting (200-1000 lux)" | Specific environment + quantified lighting |

#### ❌ Poor ODD Statements

| Statement | Problem | Better Version |
|-----------|---------|----------------|
| "Normal indoor lighting" | Too vague | "Adequate lighting (50+ lux); pitch-black (<10 lux) is OUT OF ODD" |
| "Don't go too fast" | No threshold | "Maximum operational speed: 2.5 m/s" |
| "Avoid rough terrain" | Undefined | "Smooth floors only; terrain roughness variance >0.05m is OUT OF ODD" |
| "Be careful around people" | No action | "Humans within 1m = immediate OUT OF ODD" |

#### Writing Tips

1. **Use SI units consistently** - m/s for speed, m/s² for acceleration, degrees for angles, meters for distances
2. **Define both "designed for" AND "not designed for"** - Explicit negatives help agents identify violations
3. **Quantify ranges, not just limits** - "0.5-2.0 m/s typical speed" is more useful than just "max 2.5 m/s"
4. **Explain expected behaviors** - "Brief acceleration bursts during obstacle avoidance are expected" prevents false positives
5. **Use progressive severity language**:
   - "Designed for" = normal operation
   - "Can handle" = within limits but not optimal  
   - "NOT designed for" = violation, triggers concern
   - "DEFINITELY NOT" = hard constraint, immediate OUT_ODD

### ODD Structure

Follow the structure used in `odd_agents/odd_definition.py`. Each section maps to evaluation axes:

```python
nl_odd_description = """
<Robot Name> - Operational Design Domain

ROBOT PHYSICAL SPECIFICATIONS (EGO VEHICLE):
# Used for: Clearance analysis, passability assessment
- Footprint: X.Xm length × X.Xm width
- Height: X.Xm
- Minimum passable gap: X.Xm width
- Turning radius: X.Xm

ENVIRONMENT:
# Used for: Environment classification, lighting assessment
<Describe typical operating environments - indoor/outdoor, lighting requirements,
expected conditions. Be specific about what is normal vs edge cases.>
Example: "Indoor warehouse with concrete floors, artificial lighting (200-1000 lux).
Very dim areas (<50 lux) are outside operational limits."

OBSTACLE HANDLING:
# Used for: Obstacle density evaluation, navigation feasibility
<Describe obstacle density expectations, navigation around objects, what level
of clutter is acceptable vs outside design limits.>
Example: "Moderate furniture density expected. Blocked navigation paths
(no clear route to destination) = OUT OF ODD."

MOTION CHARACTERISTICS:
# Used for: Speed compliance, acceleration anomaly detection
The robot uses <motion type> appropriate for <application>:
- Maximum operational speed: X.X m/s
- Maximum acceleration: X.X m/s² (normal operation)
- Maximum pitch/roll: X degrees

# Explain expected reactive behaviors to prevent false positives:
"Brief acceleration bursts up to 8 m/s² during obstacle avoidance are normal."

The robot is NOT designed for:
- <Motion limitation 1>
- <Motion limitation 2>

TERRAIN:
# Used for: Surface classification, traversability assessment
Designed for <surface types>. Can handle:
- <Surface 1>
- <Surface 2>
- <Incline limit, e.g., "Gentle ramps (<15 degree incline)">

NOT designed for:
- <Terrain limitation 1>
- <Terrain limitation 2>

HUMAN/ANIMAL PROXIMITY:
# Used for: Safety zone evaluation, immediate OUT_ODD triggers
<Define rules with specific distances and consequences>
Example: "Humans or animals within 0.5-1m while navigating = OUT OF ODD.
Brief passing at >1.5m distance is acceptable."

DEFINITELY NOT DESIGNED FOR:
# Used for: Hard constraint violations - any match = immediate OUT_ODD
- <Hard constraint 1>
- <Hard constraint 2>
- <Hard constraint 3>
"""
```

### Example: Warehouse Robot ODD

```python
nl_odd_description = """
Warehouse Mobile Robot - Operational Design Domain

ROBOT PHYSICAL SPECIFICATIONS (EGO VEHICLE):
- Footprint: 0.8m length × 0.6m width
- Height: 0.4m
- Minimum passable gap: 0.8m (standard aisle width)
- Turning radius: 0.5m

ENVIRONMENT:
The robot operates in indoor warehouse facilities with concrete floors,
artificial lighting (200-1000 lux), and organized shelving aisles. 
It handles standard warehouse conditions including loading docks and
staging areas. Very dim areas (<50 lux) are outside operational limits.

OBSTACLE HANDLING:
Designed for structured warehouse environments with pallets, shelving units,
and stationary equipment. The robot navigates standard aisles (1.2m+ width)
and avoids temporary obstacles like dropped boxes. NOT designed for
unstructured storage areas or extremely narrow aisles (<0.8m).

MOTION CHARACTERISTICS:
The robot uses differential drive appropriate for warehouse logistics:
- Maximum operational speed: 1.5 m/s
- Maximum acceleration: 3.0 m/s²
- Smooth motion with gradual stops (no abrupt maneuvers)

The robot is NOT designed for:
- Speeds exceeding 1.5 m/s
- Aggressive acceleration or emergency stops without warning
- Operation on forklifts or elevated platforms

TERRAIN:
Designed for flat industrial floors. Can handle:
- Polished concrete
- Painted floor markings
- Smooth epoxy coatings
- Minor cracks and expansion joints
- Gentle ramps (<5 degree incline)

NOT designed for:
- Outdoor loading areas (rain, ice)
- Gravel or unpaved surfaces
- Ramps steeper than 5 degrees
- Dock plates or levelers

HUMAN/ANIMAL PROXIMITY:
The robot operates in designated autonomous zones:
- Humans NOT ALLOWED in active autonomous zones during operation
- Robot must stop if human enters zone (safety interlock)
- Manual mode required for human-occupied areas

DEFINITELY NOT DESIGNED FOR:
- Outdoor operation
- Human-occupied areas during autonomous mode
- Wet, oily, or contaminated floors
- Steep ramps (>5 degrees)
- Freezer or extreme temperature environments
"""
```

### ODD Specification Guidelines

1. **Start with physical specs** - Agents need robot dimensions for clearance analysis
2. **Be specific about environment** - Indoor/outdoor, surfaces, lighting ranges
3. **Define motion limits with units** - Speed (m/s), acceleration (m/s²), angles (degrees)
4. **List prohibited conditions explicitly** - What triggers immediate OUT_ODD
5. **Include human/animal rules** - Distance thresholds, zero-tolerance vs acceptable
6. **Use "NOT designed for" sections** - Clear negative constraints help agents reason

---

## 4. Tool Threshold Tuning

Default thresholds are calibrated for the Unitree Go2. For different robots, you may need to adjust:

> **🔮 Future Architecture Note:** Planned improvements will enable tools to access the knowledge base directly, allowing VLM prompts to automatically incorporate robot profiles and ODD context. This will reduce the need for manual threshold tuning—tools will adapt based on the knowledge layer rather than hardcoded values. See `docs/DESIGN_TOOL_KNOWLEDGE_ACCESS.md` for the design.

### Motion Tool (`odd_agents/tools/motion.py`)

```python
# Collision detection thresholds
COLLISION_ACCEL_THRESHOLD = 5.0  # m/s² - sudden deceleration
COLLISION_SPEED_DROP = 0.3       # m/s - speed drop threshold

# Adjust for heavier/lighter robots
```

### Perception Tool (`odd_agents/tools/perception.py`)

```python
# BEV analysis parameters
OBSTACLE_DENSITY_THRESHOLD = 0.15  # Fraction of BEV with obstacles
CLOSE_OBSTACLE_RADIUS = 30         # Pixels from center = "close"

# Adjust based on your BEV resolution and robot size
```

---

## 5. Running Analysis

Once data is prepared:

```bash
# Interactive mode - select your scenario
python scripts/run_odd_analysis.py

# Direct scenario path
python scripts/run_odd_analysis.py --scenario /path/to/my_scenario

# With custom ODD
python scripts/run_odd_analysis.py --odd-file my_odd.txt
```

---

## 6. Example: Adapting for a Drone

### Data Differences

| Aspect | Ground Robot | Drone |
|--------|--------------|-------|
| BEV source | LiDAR looking outward | Downward-facing depth or LiDAR |
| Motion axes | Roll/pitch small | Roll/pitch can be large (banking) |
| Speed range | 0-3 m/s | 0-15+ m/s |
| Altitude | N/A | Critical ODD axis |

### ODD Adjustments

```python
nl_odd_description = """
Inspection Drone - Operational Design Domain

ENVIRONMENT:
- Setting: Outdoor industrial facility
- Weather: Clear to light overcast, wind < 10 m/s
- Altitude: 5-50 meters AGL

DYNAMIC LIMITS:
- Maximum speed: 10 m/s
- Maximum climb rate: 3 m/s
- Maximum bank angle: 30 degrees
- Maximum descent rate: 2 m/s

PROHIBITED:
- Flight over personnel
- Flight in rain or fog
- Altitude below 5m in populated areas
- GPS-denied environments
"""
```

### Additional Axes

For drones, you might add custom axes:
- `altitude_agl` - Height above ground
- `gps_quality` - Satellite fix quality
- `battery_voltage` - Power state

Extend the Evaluator agent to handle these.

---

## 7. Validation Checklist

Before running on a new platform:

- [ ] Data directory has correct structure
- [ ] Index CSV has all required columns
- [ ] Motion JSON includes position OR derived_speed
- [ ] BEV images are grayscale, robot-centered
- [ ] Robot profile exists in knowledge layer
- [ ] ODD specification covers all relevant axes
- [ ] Test run on 2-3 windows before full batch

---

## 8. Common Issues

### "No motion data available"

- Check motion JSON has `samples` array or `derived_speed`
- Verify timestamps match window boundaries

### "BEV shows no obstacles"

- Check ground filtering isn't removing everything
- Verify point cloud is in correct coordinate frame
- Adjust height threshold for your sensor height

### "Agent hallucinating environment type"

- Camera image may be too dark/overexposed
- Add explicit environment hints to ODD spec
- Check robot profile has relevant examples

---

## Need Help?

- Open an issue on [GitHub](https://github.com/danmartinez78/go2-odd-observer/issues)
- Include: robot type, sensor suite, sample data (if possible)
- Tag with `adaptation` label
