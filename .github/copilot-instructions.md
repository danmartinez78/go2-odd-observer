# Copilot Instructions for Go2 ODD Observer

## Project Overview

This is a multi-agent AI system for autonomous robot safety assessment. It analyzes sensor data (camera, LiDAR BEV, IMU) to determine if a robot is operating within its Operational Design Domain (ODD).

## Key Architecture

### Agent Pipeline (6 agents)
1. **OddSpecAgent** - Parses natural language ODD into structured specification
2. **PerceptionAgent** - Analyzes camera + 3 BEV channels (occupancy, height, roughness)
3. **MotionAgent** - Analyzes IMU data for motion state and anomalies
4. **CollisionAgent** - Binary collision detection from multimodal data
5. **EvaluatorAgent** - Constructs COD, computes compliance verdict
6. **ReportAgent** - Generates executive summary and recommendations

### Key Directories
- `odd_agents/` - Agent definitions and tools
- `scripts/` - Pipeline runners and data processing
- `data/production/` - Production datasets (sim + real)
- `data/test/` - Test datasets (2-window quick tests)
- `docs/agent_knowledge/` - Knowledge docs for agent grounding

## Versioning Guidelines

### Knowledge Documents (`docs/agent_knowledge/`)

When editing knowledge documents, follow this versioning policy:

| Change Type | Version Bump | Examples |
|-------------|--------------|----------|
| **Major (vX.0.0)** | Breaking changes to structure or semantics | Rename sections, remove guidance, change interpretation rules |
| **Minor (v0.X.0)** | New content that agents should know about | Add new sections (e.g., self-hit guidance), new patterns |
| **Patch (v0.0.X)** | Clarifications, typo fixes, wording improvements | Fix typos, improve phrasing, add examples |

**Required steps when editing knowledge docs:**
1. Update the version number in the doc header
2. Add a changelog entry below the version line
3. Update the version table in `docs/agent_knowledge/README.md`

### Agent Versions (`odd_agents/agents/`)

Agent versions are tracked in `odd_agents/agents/__init__.py` via `AGENT_VERSIONS` dict.

Update agent version when:
- Changing prompt text significantly
- Modifying tool signatures
- Changing output schema

### Data Versions (`data/DATA_VERSIONS.md`)

Update when regenerating production or test data with different:
- Window parameters (length, stride)
- BEV processing (ground filtering, channels)
- Source bagfiles

## BEV Channel Semantics

**Critical for perception agents:**
- **Occupancy:** Obstacles only (points >10cm above ground filtered)
- **Height:** ALL points including ground (full terrain elevation)
- **Roughness:** ALL points (terrain height variance per pixel)

Height and roughness show full terrain; occupancy is filtered to obstacles only.

## LiDAR Self-Hits

Small occupied pixel clusters very near the robot center (~15px radius) in BEV may be LiDAR self-hits (robot's own legs/body). Consider temporal consistency when analyzing close-proximity obstacles.

## Real vs Sim Data

- **Sim:** Point cloud in sensor frame, requires TF transform
- **Real:** Point cloud often already in odom frame (auto-detected)
- Real data is noisier than simulation
- **IMPORTANT:** Always source `go2_ros2_sdk` before extraction (for IMU message types)

## Motion Data Fields

### Derived Motion (Position-Based)
Motion JSON files include position-derived fields that work reliably for both sim and real:

| Field | Description | Source |
|-------|-------------|--------|
| `derived_speed` | Speed magnitude (m/s) | Position differentiation |
| `derived_yaw_rate` | Angular velocity (rad/s) | Yaw differentiation |
| `pos_x/y/z` | Odometry position | Raw from odom |

### IMU Data (When Available)
- `accel_x/y/z` - Linear acceleration
- `gyro_x/y/z` - Angular velocity
- `roll/pitch/yaw` - Orientation

**Motion Tool v10.0.0 Strategy:**
- Speed: Always from `derived_speed` (more reliable than odom velocity)
- Acceleration: From IMU if available, else `None`
- Angular velocity: From IMU if available, else `derived_yaw_rate`

## Knowledge Layer

Knowledge seeding is **enabled by default**. The runner seeds:
- `ref:knowledge_manifest` - Artifact references
- `ref:odd_cod_fundamentals` - Core ODD/COD definitions
- `ref:sensor_interpretation` - BEV/camera/IMU patterns

Use `--no-knowledge` flag to disable for testing.

## Common Commands

```bash
# Run analysis (interactive)
python scripts/run_odd_analysis.py

# Run specific scenario
python scripts/run_odd_analysis.py --scenario sim_2win

# Extract windows from bagfile (IMPORTANT: source ROS2 first!)
source /opt/ros/humble/setup.bash
source /workspaces/go2-odd-observer/go2_ros2_sdk/install/setup.bash
python scripts/extract_windows.py --rosbag <path> --output data/production/<name> --run-id <name>

# Regenerate all production data
bash scripts/regenerate_all_data.sh

# Run tests
pytest tests/ -v
```

## Important Notes

- Always test on 2-window test sets before batch runs
- Cost is ~$0.025/window with current model configuration
- Pipeline takes ~2 minutes for 2 windows
- Knowledge docs are in `docs/agent_knowledge/` - update versions when editing!
