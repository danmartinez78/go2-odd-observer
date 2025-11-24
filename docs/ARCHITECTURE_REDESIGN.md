# ODD Observer Architecture Redesign

**Date:** November 24, 2025  
**Status:** Planning Phase - Not Yet Implemented

## Executive Summary

This document outlines a fundamental redesign of the ODD compliance evaluation system to fix critical architectural flaws discovered during production use.

**Core Issues with Current System:**
1. **Averaging destroys critical violations**: COD agent averages per-window observations, hiding OUT_ODD windows (e.g., dark lighting window averaged to "bright")
2. **Collision agent produces false positives**: Risk scoring flags too many scenarios; should detect actual collisions only
3. **COD represents fictional point in space**: Averaging creates a point that never existed vs. representing the actual operational region
4. **Compliance agent is too narrow**: Only checks ODD violations, ignores other critical findings (sensor noise, fusion issues)
5. **Binary pass/fail lacks nuance**: No differentiation between "1 isolated violation" vs "frequent violations throughout scenario"

**Key Insight:** ODD and COD define multidimensional spaces in abstract operational condition space, not single points. A scenario's COD is the **region** the robot operated within along ODD axes, which must be compared against the ODD **region** to determine overlap. Severity scoring enables nuanced assessment beyond binary pass/fail.

---

## Conceptual Foundation

### ODD as Multidimensional Space

The Operational Design Domain defines a **region** in abstract multidimensional space along operational axes representing safe operating conditions:

```
ODD Space Example (Abstract Operational Axes):
- lighting: {"bright", "dim"} (allowed categorical values)
- obstacle_density: [0.0, 0.6] (IN_ODD numeric range)
- terrain: {"smooth", "slightly_rough"} (allowed categorical values)
- max_accel: [0.0, 2.5] m/s² (IN_ODD numeric range)

This defines a 4-dimensional region in operational condition space.
Operating within this region = IN_ODD.
```

### COD as Operational Region (Not Point!)

The Current Operating Domain represents the **region in abstract operational space** that the robot actually operated within during the scenario:

**Key Distinction:** COD is NOT physical space traversed (position, trajectory). It's the range of operational conditions (lighting, terrain, obstacles, motion dynamics) experienced mapped to the same axes as ODD.
 in operational space
{
  "lighting": "bright",          // Majority vote lost "dark" window
  "obstacle_density": 0.42,      // Average lost peak of 0.85
  "terrain": "smooth"            // Mode lost "slightly_rough" observation
}
```

**CORRECT (proposed):**
```json
// COD as region in operational space - preserves all observations
{
  "categorical": {
    "lighting": ["bright", "dim", "dark"],  // All observed lighting conditions
    "terrain": ["smooth"]                   // Only smooth terrain observed
  },
  "numeric": {
    "obstacle_density": {
      "min": 0.2,
      "max": 0.85,
      "range": [0.2, 0.85]          // Range of obstacle clutter experienced
    },
    "max_accel": {
      "min": 0.3,
      "max": 2.1,
      "range": [0.3, 2.1]           // Range of accelerations experienced
      "min": 0.1,
      "max": 1.0,
      "range": [0.1, 1.0]
    }
  }
}
```

### Compliance as Region Overlap

**Question:** Does the COD region (in abstract operational space) overlap with OUT_ODD boundaries?

**Example:**
```
ODD: obstacle_density IN_ODD = [0.0, 0.6], BOUNDARY = [0.6, 0.8], OUT_ODD = [0.8, 1.0]
COD: obstacle_density range = [0.2, 0.85]

Analysis:
- COD range [0.2, 0.85] overlaps OUT_ODD [0.8, 1.0]
- Overlap region: [0.8, 0.85]
- Conclusion: OUT_ODD violation detected (robot experienced excessive obstacle density)
```

**Distance Metric:**
- COD fully inside ODD → distance = 0 (perfectly compliant)
- COD touches BOUNDARY zone → distance = 0, but flag BOUNDARY
- COD overlaps OUT_ODD → distance = size of overlap
- COD entirely outside ODD → distance = how far outside

### Severity-Based Assessment (NEW!)

Instead of binary pass/fail, use **window distribution** to calculate **severity score**:

**Window Distribution:**
Count windows by compliance status:
- `in_odd`: Number of fully compliant windows
- `boundary`: Number of windows at ODD boundaries
- `out_odd`: Number of windows violating ODD

**Severity Levels:**
```
MINIMAL:  0.0-1.0  (e.g., 9 IN_ODD, 1 BOUNDARY, 0 OUT_ODD)
LOW:      1.0-3.0  (e.g., 9 IN_ODD, 0 BOUNDARY, 1 OUT_ODD - isolated violation)
MEDIUM:   3.0-5.0  (e.g., 7 IN_ODD, 2 BOUNDARY, 1 OUT_ODD)
HIGH:     5.0-7.0  (e.g., 5 IN_ODD, 2 BOUNDARY, 3 OUT_ODD - frequent violations)
CRITICAL: 7.0-10.0 (e.g., 2 IN_ODD, 0 BOUNDARY, 8 OUT_ODD - predominantly out of ODD)
```

**Severity Formula (example):**
```python
severity_score = (
    (num_out_odd * 2.0) +      # OUT_ODD weighted heavily
    (num_boundary * 0.5) +      # BOUNDARY minor contribution
    (num_in_odd * 0.0)          # IN_ODD no contribution
) / total_windows * 10
```

**Key Benefits:**
- **Nuanced assessment**: "1 isolated violation" vs "8 frequent violations"
- **Actionable**: MINIMAL severity → investigate, CRITICAL severity → do not deploy
- **Captures boundary warnings**: Without false-failing compliant scenarios
- **Works with COD region**: Region shows WHAT violations, severity shows HOW BAD

---

## Redesigned Agent Architecture

### 1. Perception Agents (No Change)

**PerceptionImageAgent** → camera image analysis  
**PerceptionBevAgent** → BEV occupancy analysis  
**PerceptionSummaryAgent** → aggregate perception findings

**Output:** Per-window perception classifications + flags
```json
{
  "per_window_perception": [
    {
      "window_id": "001",
      "lighting_class": "dark",
      "terrain_roughness_class": "smooth",
      "obstacle_density": 0.35,
      "flags": []
    },
    {
      "window_id": "002",
      "lighting_class": "bright",
      "terrain_roughness_class": "smooth",
      "obstacle_density": 0.48,
      "flags": ["significant_camera_noise"]
    }
  ]
}
```

### 2. Motion Agents (No Change)

**MotionWindowAgent** → per-window IMU analysis  
**MotionSummaryAgent** → aggregate motion findings

**Output:** Per-window motion classifications + flags
```json
{
  "per_window_motion": [
    {
      "window_id": "001",
      "motion_smoothness": "smooth",
      "max_accel_mps2": 1.2,
      "flags": []
    },
    {
      "window_id": "002",
      "motion_smoothness": "abrupt",
      "max_accel_mps2": 3.5,
      "flags": ["imu_anomaly_detected"]
    }
  ],
  "overall_stats": {
    "max_horizontal_accel_mps2": 3.5
  }
}
```

### 3. Collision Agent (MAJOR REWORK)

**Current (wrong):** Collision risk scoring produces false positives  
**Proposed:** Binary collision detection only

**New Purpose:** Detect actual collisions from available sensor data (IMU signatures, contact sensors if available), NOT risk assessment

**Output:**
```json
{
  "collisions_detected": [
    {
      "window_id": "005",
      "collision_detected": true,
      "evidence": "IMU spike 15.2 m/s² linear acceleration + 8.3 rad/s angular velocity change",
      "timestamp": "12.3s"
    }
  ],
  "collision_count": 1
}
```

**Remove:** 
- Collision risk scoring
- Collision likelihood scores
- Risk-based ODD compliance checks

**Add:** 
- Actual collision detection logic based on IMU signatures:
  - Sudden acceleration spikes (threshold: >10 m/s²)
  - Sharp angular velocity changes (rotation impact)
  - Pattern: spike followed by oscillation (bounce/recoil)
- Contact sensor integration (if available in Phase 0 audit)
- Motor current spikes (if available - indicates sudden load)

**Note:** Without odometry velocity, collision detection relies on IMU acceleration/gyro patterns. High acceleration spike + angular velocity change + damped oscillation is strong collision signature.

**Rationale:** Collision risk is operational telemetry, not an ODD axis. ODD defines environment conditions (lighting, terrain, obstacles), not operational risk during navigation.

### 4. COD Agent (COMPLETE REDESIGN)

**New Name:** `CodAnalysisAgent` (analysis, not just classification)

**Inputs:**
- ODD specification
- Per-window perception data
- Per-window motion data
- Collision detection results (binary, not risk scores)

**Responsibilities:**

#### 4a. Per-Window ODD Compliance
Compare each window's operational conditions against ODD thresholds:
```json
{
  "per_window_compliance": [
    {
      "window_id": "001",
      "compliance": "OUT_ODD",
      "violations": [
        {
          "axis": "lighting",
          "observed": "dark",
          "odd_allowed": ["bright", "dim"]
        }
      ]
    },
    {
      "window_id": "002",
      "compliance": "BOUNDARY",
      "violations": [
        {
          "axis": "obstacle_density",
          "observed": 0.65,
          "odd_in_odd": [0.0, 0.6],
          "odd_boundary": [0.6, 0.8]
        }
      ]
    }
  ]
}
```

#### 4b. Scenario COD Construction
Build multidimensional region from all windows:
```json
{
  "scenario_cod": {in operational space from all windows:
```json
{
  "scenario_cod": {
    "categorical": {
      "environment_type": ["indoor_office"],
      "lighting": ["bright", "dim", "dark"],  // All lighting conditions observed
      "terrain": ["smooth"]                   // Only smooth terrain observed
    },
    "numeric": {
      "obstacle_density": {
        "min": 0.2,
        "max": 0.85,
        "range": [0.2, 0.85]        // Range of obstacle clutter experienced
      },
      "traversability_score": {
        "min": 0.3,
        "max": 0.9,
        "range": [0.3, 0.9]         // Range of path clearance experienced
      },
      "max_accel_mps2": {
        "min": 0.5,
        "max": 2.1,
        "range": [0.5, 2.1]         // Range of accelerations experienced
      }
    }
  }
}
```Overlap Analysis
Calculate overlap between COD region and ODD boundaries in operational space:
```json
{
  "odd_overlap_analysis": {
    "cod_within_odd": false,
    "overlap_detected": true,
    "categorical_violations": [
      {
        "axis": "lighting",
        "cod_values": ["bright", "dim", "dark"],
        "odd_allowed": ["bright", "dim"],
        "violation_value": "dark",
        "windows_affected": ["001"]
      }
    ],
    "numeric_violations": [
      {
        "axis": "obstacle_density",
        "cod_range": [0.2, 0.85],
        "odd_in_odd": [0.0, 0.6],
        "odd_out_odd": [0.8, 1.0],
        "overlap_with_out_odd": [0.8, 0.85],
        "overlap_amount": 0.05,
        "windows_affected": ["004", "007"]
      }
    ]
  }
}
```

**Key Change:** COD agent handles both per-window compliance AND scenario-level region analysis. Evaluator then synthesizes these with other agent findings
**Key Change:** COD agent now does ODD comparison (was in Compliance agent), but outputs detailed per-window + scenario analysis for Evaluator to synthesize.

### 5. Evaluator Agent (Renamed from Compliance)

**New Name:** `EvaluatorAgent`

**Purpose:** Synthesize ALL findings into nuanced, actionable assessment (not just ODD compliance)

**Inputs:**
- COD analysis (per-window compliance, scenario COD region, ODD overlap)
- Perception flags (camera noise, sensor fusion issues)
- Motion flags (IMU anomalies)
- Collision detections (binary, not risk scores)

**Output:**
```json
{
  "window_distribution": {
    "in_odd": 9,
    "boundary": 1,
    "out_odd": 0,
    "total": 10
  },
  
  "severity": {
    "score": 0.5,
    "level": "MINIMAL",
    "assessment": "Compliant - minor boundary condition detected"
  },
  
  "odd_analysis": {
    "scenario_cod_region": {
      "categorical": {"lighting": ["bright"], "terrain": ["smooth"]},
      "numeric": {"obstacle_density": {"min": 0.2, "max": 0.58}}
    },
    "cod_within_odd": true,
    "violations": [],
    "boundary_warnings": [
      {
        "axis": "obstacle_density",
        "windows_affected": ["003"],
        "details": "Approached boundary (0.58/0.6 threshold)"
      }
    ]
  },
  
  "operational_issues": {
    "collisions_detected": [],
    "sensor_quality_flags": [],
    "motion_anomalies": []
  },
  
  "investigation_flags": [
    "Window 003: Approached boundary on obstacle_density (0.58/0.6 threshold) - monitor trend in future deployments"
  ],
  
  "executive_summary": "Scenario is compliant with ODD. Robot operated within allowed conditions throughout, with one window approaching boundary on obstacle density. No collisions detected, no sensor quality issues."
}
```

**Example 2: Isolated Violation**
```json
{
  "window_distribution": {
    "in_odd": 9,
    "boundary": 0,
    "out_odd": 1,
    "total": 10
  },
  
  "severity": {
    "score": 2.0,
    "level": "LOW",
    "assessment": "Isolated ODD exit detected"
  },
  
  "odd_analysis": {
    "scenario_cod_region": {
      "categorical": {"lighting": ["bright", "dark"], "terrain": ["smooth"]},
      "numeric": {"obstacle_density": {"min": 0.2, "max": 0.5}}
    },
    "cod_within_odd": false,
    "violations": [
      {
        "axis": "lighting",
        "violation_value": "dark",
        "windows_affected": ["005"]
      }
    ]
  },
  
  "investigation_flags": [
    "Window 005: OUT_ODD due to dark lighting - occurred during brief shadow passage through doorway"
  ],
  
  "executive_summary": "Scenario has isolated ODD exit (severity: LOW). Robot briefly operated in dark lighting conditions in window 005. This appears to be transient environmental condition during doorway passage, not systemic issue."
}
```

**Example 3: Frequent Violations**
```json
{
  "window_distribution": {
    "in_odd": 5,
    "boundary": 2,
    "out_odd": 3,
    "total": 10
  },
  
  "severity": {
    "score": 6.5,
    "level": "HIGH",
    "assessment": "Frequent ODD violations throughout scenario"
  },
  
  "odd_analysis": {
    "scenario_cod_region": {
      "categorical": {"lighting": ["bright", "dim"], "terrain": ["smooth", "slightly_rough"]},
      "numeric": {"obstacle_density": {"min": 0.3, "max": 0.92}}
    },
    "cod_within_odd": false,
    "violations": [
      {
        "axis": "obstacle_density",
        "windows_affected": ["002", "005", "008"],
        "details": "Exceeded OUT_ODD threshold (0.8)"
      },
      {
        "axis": "terrain",
        "violation_value": "slightly_rough",
        "windows_affected": ["004", "007"]
      }
    ]
  },
  
  "operational_issues": {
    "collisions_detected": [],
    "sensor_quality_flags": [
      {
        "windows": ["005", "008"],
        "issue": "camera_noise_detected",
        "severity": "medium"
      }
    ]
  },
  
  "investigation_flags": [
    "HIGH SEVERITY: Windows 002, 005, 008 exceeded obstacle density threshold (>0.8)",
    "Windows 004, 007: Operated on slightly rough terrain (OUT_ODD)",
    "Camera noise detected in windows 005, 008 - may affect perception accuracy"
  ],
  
  "executive_summary": "Scenario has HIGH severity ODD violations. Robot frequently operated in excessively cluttered environments (3/10 windows >0.8 obstacle density) and on rough terrain (2/10 windows). Camera noise detected during high-density windows may indicate correlation between environmental complexity and sensor degradation. Recommend restricting deployment to less cluttered indoor environments."
}
```

**Key Capabilities:**
1. **Severity scoring** from window distribution
2. **Formal ODD/COD region comparison** using overlap analysis
3. **Comprehensive synthesis** of ODD violations + sensor issues + collisions + anomalies
4. **Actionable investigation flags** specific to windows and conditions
5. **Executive summary** for human decision-makers

### 6. Report Agent (Minor Changes)

**Purpose:** Format Evaluator output into HTML report

**Changes Needed:**
- Add per-window compliance table (show which windows violated ODD)
- Visualize COD region vs ODD boundaries (if possible)
- Separate severity levels clearly (MINIMAL/LOW/MEDIUM/HIGH/CRITICAL)
- Show investigation flags by priority
- **Add pipeline metadata/telemetry** (see below)

---

## Pipeline Metadata & Telemetry (NEW!)

**Problem:** As we iterate on ODD specs and agent prompts, we need to track which version of what produced each result.

**Solution:** Add comprehensive metadata to every analysis output

### Metadata Structure

Every analysis result should include:

```json
{
  "pipeline_metadata": {
    "analysis_timestamp": "2025-11-24T01:23:45Z",
    "pipeline_version": "2.0.0-cod-region-redesign",
    
    "odd_specification": {
      "version": "v1.2.0",
      "hash": "a3f5e9d2...",  // SHA256 of ODD spec JSON
      "source": "embedded" | "file://path/to/odd.json",
      "full_spec": { /* entire ODD spec for reproducibility */ }
    },
    
    "agent_versions": {
      "perception_image": {
        "version": "1.3.0",
        "model": "gemini-2.0-flash-lite",
        "prompt_hash": "b7c2d4e1..."  // Hash of prompt template
      },
      "perception_bev": {
        "version": "1.3.0",
        "model": "gemini-2.0-flash-lite",
        "prompt_hash": "f8a1c3d9..."
      },
      "motion_window": {
        "version": "1.2.0",
        "model": "gemini-2.0-flash-lite",
        "prompt_hash": "e4b9a2f1..."
      },
      "cod_analysis": {
        "version": "2.0.0",  // New agent in redesign
        "model": "gemini-3-pro",
        "prompt_hash": "d1f7c8a3..."
      },
      "evaluator": {
        "version": "2.0.0",  // Renamed from compliance
        "model": "gemini-3-pro",
        "prompt_hash": "c9e2b4f7..."
      },
      "collision_detection": {
        "version": "2.0.0",  // Reworked in redesign
        "model": "gemini-2.0-flash-lite",
        "prompt_hash": "a8d3f1c2..."
      }
    },
    
    "data_processing": {
      "bev_cropping_enabled": true,
      "image_encoding": "jpeg-85",
      "tool_split_version": "2.0"  // Which data each agent received
    },
    
    "execution_stats": {
      "total_duration_seconds": 45.3,
      "total_tokens_used": 125000,
      "agent_timings": {
        "perception_image": 8.2,
        "perception_bev": 6.5,
        "motion_window": 4.1,
        "cod_analysis": 12.3,
        "evaluator": 8.7
      }
    }
  },
  
  "scenario_info": {
    "scenario_id": "real_01_173442",
    "source_bagfile": "data/raw_rosbags/real/collection_20251122_173442.db3",
    "window_count": 12,
    "duration_seconds": 24.5
  },
  
  // ... rest of analysis results (COD, evaluator output, etc.)
}
```

### Implementation Requirements

#### 1. ODD Versioning
```python
# In ODD spec agent or config
ODD_SPEC_VERSION = "v1.2.0"

def load_odd_spec():
    spec = {...}  # Load ODD
    spec_hash = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    return {
        "version": ODD_SPEC_VERSION,
        "hash": spec_hash[:16],  # Short hash
        "full_spec": spec
    }
```

#### 2. Agent Versioning
```python
# In each agent module
AGENT_VERSION = "2.0.0"

def create_agent(...):
    prompt_hash = hashlib.sha256(prompt_template.encode()).hexdigest()
    agent.metadata = {
        "version": AGENT_VERSION,
        "model": model_name,
        "prompt_hash": prompt_hash[:16]
    }
    return agent
```

#### 3. Pipeline Orchestration
```python
# In workflow.py
def run_odd_analysis(scenario_path, odd_spec):
    start_time = time.time()
    
    # Collect agent versions
    agent_versions = {
        "perception_image": perception_image_agent.metadata,
        "perception_bev": perception_bev_agent.metadata,
        # ... all agents
    }
    
    # Run pipeline
    results = workflow.run(...)
    
    # Add metadata
    results["pipeline_metadata"] = {
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "pipeline_version": PIPELINE_VERSION,
        "odd_specification": odd_spec_metadata,
        "agent_versions": agent_versions,
        "execution_stats": {
            "total_duration_seconds": time.time() - start_time,
            # ... token counts, timings
        }
    }
    
    return results
```

### Benefits

**Debugging:**
- "This result used ODD v1.2.0 with COD agent v2.0.0 on Gemini 3 Pro"
- Compare results across ODD versions: "v1.1.0 had 40% false positives, v1.2.0 has 8%"

**Reproducibility:**
- Full ODD spec embedded → can reproduce exact analysis
- Agent prompt hashes → know if prompt changed between runs

**A/B Testing:**
- "COD agent v1.0 (averaging) vs v2.0 (region): 45% accuracy improvement"
- "Gemini 3 Pro vs flash-lite on evaluator: +12% synthesis quality"

**Performance Tracking:**
- Token usage trends over time
- Identify slow agents for optimization
- Cost tracking per agent/model combination

**Report Display:**
Add metadata footer to HTML reports:
```
Analysis produced by:
- Pipeline: v2.0.0-cod-region-redesign
- ODD Spec: v1.2.0 (hash: a3f5e9d2)
- COD Agent: v2.0.0 (gemini-3-pro)
- Evaluator: v2.0.0 (gemini-3-pro)
- Generated: 2025-11-24 01:23:45 UTC
- Total tokens: 125k | Duration: 45s
```

---

## Implementation Phases

### Phase 0: Data Source Discovery (Quick Investigation)
**Goal:** Identify all available sensor data in bagfiles, find missed opportunities

**Rationale:** Pipeline may be missing valuable data sources. Before refactoring, ensure we're leveraging all available information.

**Tasks:**

#### 0.1 Bagfile Topic Audit
Systematically inspect all topics in representative bagfiles:

```python
# Quick audit script
import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

def audit_bagfile(bag_path):
    reader = rosbag2_py.SequentialReader()
    reader.open(bag_path)
    
    topic_stats = {}
    
    while reader.has_next():
        (topic, data, t) = reader.read_next()
        
        if topic not in topic_stats:
            topic_stats[topic] = {
                'count': 0,
                'message_type': None,
                'sample_message': None,
                'all_zeros': True,
                'has_data': False
            }
        
        # Deserialize and inspect
        msg = deserialize_message(data, get_message(topic))
        topic_stats[topic]['count'] += 1
        
        if topic_stats[topic]['sample_message'] is None:
            topic_stats[topic]['sample_message'] = msg
            topic_stats[topic]['message_type'] = type(msg).__name__
        
        # Check if populated (not all zeros)
        if has_nonzero_data(msg):
            topic_stats[topic]['has_data'] = True
            topic_stats[topic]['all_zeros'] = False
    
    return topic_stats

def has_nonzero_data(msg):
    """Check if message contains actual data vs zeros"""
    # Inspect common field patterns
    if hasattr(msg, 'data') and msg.data:
        return True
    if hasattr(msg, 'linear') and (msg.linear.x != 0 or msg.linear.y != 0):
        return True
    if hasattr(msg, 'angular') and msg.angular.z != 0:
        return True
    # ... check other field patterns
    return False
```

#### 0.2 Current vs Available Data

**Currently Used:**
- ✅ `/camera/color/image_raw` - Camera images
- ✅ `/lidar_bev_image` - BEV occupancy maps
- ✅ `/imu/data` - IMU (linear_acceleration, angular_velocity)
- ❌ `/odom` - **Not available - robot does not publish odometry**

**Investigate (Potentially Available):**
- `/cmd_vel` or `/go2/cmd_vel` - Commanded velocities (may infer motion intent)
- `/joint_states` - Joint positions/velocities (leg movement patterns, gait analysis)
- `/battery_state` - Battery level (affects performance?)
- `/contact_states` or `/foot_contacts` - Ground contact sensors (collision detection!)
- `/tf` or `/tf_static` - Transforms (robot pose, frame relationships)
- `/lidar/scan` or `/pointcloud` - Raw LiDAR data (before BEV processing)
- Force/torque sensors (if available on legs)
- Motor current/temperature (may indicate collisions or difficult terrain)

#### 0.3 Data Quality Assessment

For each topic, determine:
1. **Message rate:** How frequently published? (Hz)
2. **Data validity:** All zeros? Constant values? Changing over time?
3. **Coverage:** Available in all scenarios or sporadic?
4. **Utility:** Could this improve any agent?

**Example findings format:**
```
Topic: /joint_states
  Rate: 100 Hz  
  Status: ✅ POPULATED - positions/velocities changing
  Coverage: Available in all bags
  Utility: MEDIUM - gait analysis for terrain classification?
  
Topic: /cmd_vel
  Rate: 10 Hz
  Status: ✅ POPULATED - linear.x varies 0.0-0.8 m/s
  Coverage: Available in all bags
  Utility: MEDIUM - intended motion vs actual (IMU) for anomaly detection
  
Topic: /contact_states
  Rate: 20 Hz
  Status: ❌ ALL ZEROS or NOT PRESENT
  Coverage: N/A
  Utility: Would be HIGH if available (collision/contact detection)
```

#### 0.4 Integration Opportunities

Based on audit, identify quick wins:

**High Priority:**
- If `/joint_states` shows leg dynamics → Add to terrain/motion analysis (gait patterns on rough terrain)
- If `/cmd_vel` available → Compare commanded vs actual motion (IMU) for anomaly detection

**Medium Priority:**
- If `/tf` available → Better spatial reasoning for BEV analysis
- If `/lidar/scan` or raw point cloud available → Enhanced obstacle detection, terrain features
- If motor currents available → Detect high-resistance situations (collisions, difficult terrain)

**Low Priority:**
- Battery correlation with performance degradation
- Metadata topics (diagnostics, status)
- Configuration topics (usually static)

**Note:** Since odometry/velocity is not available, collision detection must rely on IMU signatures alone (acceleration spikes, rotation anomalies) combined with any available contact sensors.

#### 0.5 Documentation Updates

Document findings:
- Update `DATA_NAMING_CONVENTION.md` with all available topics
- Add "Available Sensors" section to architecture docs
- Flag missing sensors that would be valuable (for future hardware)

**Success Criteria:**
- ✅ Complete topic inventory for 2-3 representative bagfiles
- ✅ Identify at least 1 new data source to integrate
- ✅ Document which topics are populated vs empty
- ✅ Prioritized list of integration opportunities

**Time Estimate:** 2-4 hours (quick investigation)

**Deliverables:**
- Topic audit report (CSV or JSON with all findings)
- Integration recommendations (prioritized)
- Updated sensor documentation

---

## Phase 1: Architecture Refactor + Critical Data Fixes

**Goal:** Fix fundamental design flaws, critical data gaps, and validate new approach

**Rationale:** Current architecture is fundamentally flawed (averaging destroys violations, missing terrain data). Need working pipeline with complete data before systematic measurement. Manual testing on 3-5 diverse scenarios validates macro-level correctness.

**Tasks:**

### 1.1 BEV Data Enhancement (CRITICAL - Do First!)
**Current Issue:** Agents only receive `bev_occupancy`, missing height/density/roughness needed for terrain analysis

**Solution Part A - Add Missing BEV Channels:**
- Perception tool: Load all 4 BEV channels (occupancy, height, density, roughness)
- Collision tool: Load all 4 BEV channels
- Update prompts to explain each channel:
  - Occupancy: Binary obstacle map
  - Height: Elevation data (critical for terrain roughness!)
  - Density: Point cloud density (sensor quality indicator)
  - Roughness: Terrain surface variation (directly computed metric)

**Solution Part B - Auto-Crop BEVs:**
**Issue:** BEVs are 50-75% empty black borders (wasted tokens)
**Why Now:** Adding 4 BEVs without cropping = 4x token usage!

```python
def auto_crop_bev(bev_image):
    """Crop to occupied region + 10% margin."""
    occupied = np.where(bev_image != background_color)
    if len(occupied[0]) == 0:
        return bev_image  # Empty BEV, keep as-is
    
    min_x, max_x = occupied[1].min(), occupied[1].max()
    min_y, max_y = occupied[0].min(), occupied[0].max()
    
    # Add 10% margin
    margin = 0.1
    height, width = bev_image.shape[:2]
    margin_x = int((max_x - min_x) * margin)
    margin_y = int((max_y - min_y) * margin)
    
    crop = bev_image[
        max(0, min_y - margin_y):min(height, max_y + margin_y),
        max(0, min_x - margin_x):min(width, max_x + margin_x)
    ]
    return crop
```

**Expected Impact:**
- 50-75% BEV size reduction per image
- 4 cropped BEVs ≈ same total size as current 1 uncropped BEV
- Agents can now accurately assess terrain roughness

**Deliverables:**
- Update `odd_agents/tools/perception.py` to load 4 BEVs
- Update `odd_agents/tools/collision.py` to load 4 BEVs
- Add `auto_crop_bev()` to BEV rendering pipeline
- Reprocess all windows with 4 cropped BEVs
- Update prompts with BEV channel explanations

### 1.2 Collision Agent Rework
- Remove collision risk scoring logic entirely
- Implement binary collision detection:
  - IMU spike detection (threshold: >10 m/s² acceleration)
  - Velocity drop analysis (sudden stop detection)
  - Force sensor integration (if available)
- Update output schema (collisions_detected list, no risk scores)
- **Manual test:** Run on 2-3 scenarios, verify no false positive risk alerts

### 1.3 COD Agent Redesign
- Implement per-window ODD compliance checking
  - Compare each window's conditions against ODD thresholds
  - Output IN_ODD / BOUNDARY / OUT_ODD per window
- Implement scenario COD region construction
  - Categorical: collect all unique observed values
  - Numeric: extract min/max/range for each axis
- Implement ODD overlap analysis
  - Detect categorical violations (observed value not in allowed set)
  - Detect numeric overlap with OUT_ODD ranges
- **Manual test:** Run on 2-3 scenarios, verify:
  - All per-window violations preserved (no averaging)
  - COD region captures all observations
  - Overlap analysis identifies violations correctly

### 1.4 Evaluator Agent Creation
- Rename Compliance → Evaluator agent
- Implement severity calculation from window distribution
  - Formula: `(out_odd × 2.0 + boundary × 0.5) / total × 10`
  - Map to severity levels (MINIMAL/LOW/MEDIUM/HIGH/CRITICAL)
- Integrate all flags:
  - ODD violations from COD agent
  - Sensor quality issues from Perception
  - Motion anomalies from Motion agents
  - Collision detections from Collision agent
- Generate investigation flags (specific, actionable)
- Generate executive summary
- **Manual test:** Run on 3-5 diverse scenarios:
  - Fully compliant (expect MINIMAL severity, 0 flags)
  - Isolated violation (expect LOW severity, specific flag)
  - Frequent violations (expect HIGH severity, multiple flags)

### 1.5 Manual Validation Suite
Select 3-5 representative scenarios:
1. **Fully compliant**: All windows IN_ODD, expect severity=MINIMAL
2. **Boundary case**: 9 IN_ODD + 1 BOUNDARY, expect severity=MINIMAL, investigation flag
3. **Isolated violation**: 9 IN_ODD + 1 OUT_ODD, expect severity=LOW, specific violation flag
4. **Mixed violations**: 7 IN_ODD + 2 BOUNDARY + 1 OUT_ODD, expect severity=MEDIUM
5. **Frequent violations**: 4 OUT_ODD + 6 IN_ODD, expect severity=HIGH

**Success Criteria:**
- ✅ Agents receive all 4 BEV channels (verified in tool inputs)
- ✅ BEVs are auto-cropped (50-75% size reduction measured)
- ✅ Agents can accurately classify terrain roughness (manual spot-check)
- ✅ COD regions preserve all per-window observations
- ✅ Severity scores differentiate isolated vs frequent violations
- ✅ Collision detection has high precision (no false positives)
- ✅ Evaluator provides actionable nuanced assessment
- ✅ Manual review of 3-5 scenarios confirms correctness

**Deliverables:**
- Auto-crop BEV implementation in rendering pipeline
- All windows reprocessed with 4 cropped BEVs
- Updated perception.py and collision.py tools (4 BEV loading)
- Refactored COD agent with region-based logic
- New Evaluator agent implementation
- Updated Collision agent (binary detection)
- Test results on validation scenarios
- Updated agent prompts and tool definitions

---

## Phase 2: Performance Optimization & Data Enhancement

**Goal:** Improve efficiency and add visual/LiDAR odometry for richer motion analysis

**Tasks:**

### 2.1 Tool Splitting by Data Type
5. **Frequent violations**: 5 IN_ODD + 5 OUT_ODD, expect severity=HIGH/CRITICAL

For each scenario, manually verify:
- Per-window compliance matches expectations
- COD region preserves all observed conditions
- Severity score aligns with violation distribution
- Investigation flags are specific and actionable
- No violations averaged away or lost

**Success Criteria:**
- ✅ New pipeline runs end-to-end without errors
- ✅ COD regions capture all observations (no fictional averaged points)
- ✅ Severity scores differentiate scenarios appropriately
- ✅ No violations averaged away (compare to known ground truth)
- ✅ Outputs are human-readable and logical
- ✅ Investigation flags are actionable

**Deliverables:**
- Updated agent code (collision, COD, evaluator)
- Manual validation results documented
- List of edge cases discovered during testing

### Phase 2: Performance Optimization & Data Enhancement
**Goal:** Improve efficiency and add visual/LiDAR odometry for richer motion analysis

**Tasks:**

#### 2.1 Tool Splitting by Data Type
**Issue:** Motion agent receives BEV data it never uses

**Solution:** Split tools by required data:
- `camera_image_tool` → Perception Image Agent only
- `bev_occupancy_tool` → Perception BEV Agent only  
- `imu_data_tool` → Motion agents only

**Expected gain:** 30-40% token reduction, faster execution

#### 2.2 Image Encoding Optimization
**Current:** PNG base64 for all images

**Solution:**
- Camera images: JPEG at quality 85-90 (photographic content)
- BEV images: PNG (sharp geometric features)

**Expected gain:** 40-60% size reduction for camera images

#### 2.3 Visual & LiDAR Odometry Integration (NEW!)
**Goal:** Add reliable motion estimates from high-rate sensor data

**Background:** Phase 0 findings showed no velocity data available:
- `/odom` twist = [0, 0, 0] (not populated)
- `/go2_states` not available on real robot
- Only option: Compute odometry from visual/LiDAR sensors

**Approach:**
1. Create standalone odometry functions:
   - `scripts/compute_visual_odometry.py` - Feature tracking (ORB/SIFT) between camera frames
   - `scripts/compute_lidar_odometry.py` - ICP alignment between point cloud scans
2. Validate accuracy on test scenarios (visual vs LiDAR agreement)
3. Add to window preprocessing - enrich motion JSON with odometry data
4. Update motion tool to use odometry (additive - preserves existing IMU arrays)

**Data Schema Addition (Additive - No Breaking Changes):**
```json
{
  "motion": {
    // Existing fields preserved
    "accel_x": [...], "gyro_x": [...], "timestamps": [...],
    
    // NEW: Precomputed odometry
    "visual_odometry": {
      "distance_traveled": 2.3,
      "avg_velocity": 0.46,
      "max_velocity": 0.62,
      "trajectory_points": [[0,0], [0.5,0.1], [1.0,0.2], ...],
      "confidence": 0.85,
      "method": "ORB_feature_tracking"
    },
    "lidar_odometry": {
      "distance_traveled": 2.4,
      "avg_velocity": 0.48,
      "max_velocity": 0.61,
      "trajectory_points": [[0,0], [0.5,0.15], [1.1,0.25], ...],
      "confidence": 0.92,
      "method": "ICP_alignment"
    },
    "odometry_agreement": {
      "distance_diff_meters": 0.1,
      "agreement_level": "high",  // high/medium/low
      "recommended_source": "lidar"
    }
  }
}
```

**Dependencies:**
- OpenCV for visual odometry (add to requirements.txt)
- Open3D for LiDAR ICP (add to requirements.txt)

**Validation Criteria:**
- Visual and LiDAR odometry agree within 10% on test scenarios
- Documented drift characteristics over time
- Confidence scoring based on feature quality / ICP convergence

**Expected Impact:**
- Motion agent can now estimate velocity (differentiate stationary vs moving)
- Cross-validation between visual/LiDAR increases confidence
- Odometry discrepancies flag potential sensor issues

**Success Criteria:**
- ✅ 30-50% overall token reduction (from other Phase 2 items)
- ✅ Faster execution times (measure on 10-scenario batch)
- ✅ Same accuracy as Phase 1 (no quality degradation)
- ✅ Visual/LiDAR odometry implemented and validated
- ✅ Motion data enriched with odometry (all windows reprocessed)
- ✅ Agents can now estimate velocity and detect motion

**Deliverables:**
- Tool refactoring (split by data type)
- Image encoding updates
- Visual odometry implementation (`compute_visual_odometry.py`)
- LiDAR odometry implementation (`compute_lidar_odometry.py`)
- Odometry validation report
- Window enrichment script (add odometry to motion JSON)
- Updated motion tool prompts (explain odometry usage)
- Performance benchmark comparison (before/after)

### Phase 3: Evaluation Framework (Systematic Refinement)
**Goal:** Create systematic measurement framework for continuous improvement

**Rationale:** Phase 1 validates macro-level correctness via manual testing. Phase 3 enables systematic measurement of edge cases, prompt tuning, and quantified improvement tracking.

**Tasks:**

#### 3.1 Ground Truth Dataset Creation
Create 5-10 hand-labeled scenarios with definitive labels:

**Diversity criteria:**
- **Compliant scenarios (2-3):** Fully IN_ODD, no violations
- **Boundary scenarios (2-3):** Approaching limits, no violations
- **Violation scenarios (3-4):** Clear OUT_ODD conditions
- **Mixed scenarios (1-2):** Some windows IN_ODD, some OUT_ODD

**Labeling requirements:**
- Per-window labels: IN_ODD / BOUNDARY / OUT_ODD
- Axis-specific violations: Which ODD axis violated, observed value, expected range
- Expected severity level: MINIMAL / LOW / MEDIUM / HIGH / CRITICAL
- Expected COD region: Categorical sets, numeric ranges

#### 3.2 Evaluator Setup
**Model:** Gemini 3 Pro (most capable Google model available)

**Evaluation rubric:**
1. **Per-window accuracy:** % of windows correctly classified
2. **Violation detection:** Precision, recall for OUT_ODD windows
3. **False positive rate:** % of IN_ODD scenarios incorrectly flagged
4. **Severity alignment:** Severity score matches expected level
5. **COD region accuracy:** Region captures all observations, no hallucinations

#### 3.3 Baseline Measurement
Run Phase 1 architecture on ground truth dataset:
- Document per-window accuracy
- Measure false positive rate
- Identify failure modes
- Classify errors (prompt issue, data quality, edge case)

#### 3.4 Iterative Refinement
Based on eval results:
- Tune prompts for agents with <95% accuracy
- Adjust severity thresholds if misaligned
- Add edge case handling
- Re-run evals, measure improvement

**Success Criteria:**
- ✅ Per-window accuracy >95%
- ✅ False positive rate <10% (down from 40-60% baseline)
- ✅ Severity scoring aligns with ground truth (±1 level)
- ✅ COD regions preserve all observations (0 hallucinations)
- ✅ Clear failure mode taxonomy documented

**Deliverables:**
- Ground truth dataset (5-10 labeled scenarios)
- Evaluation framework code
- Baseline metrics report
- Iterative tuning log (what changed, impact measured)
- Final performance metrics

### Phase 4: Model Testing & Report Updates
**Goal:** Test best available models on complex agents, update reports for new outputs

**Tasks:**

#### 4.1 Model Performance Testing
Test **Gemini 3 Pro** on complex reasoning agents:

**COD Agent:**
- Complexity: Multi-window aggregation, region construction, overlap detection
- Test: Run Gemini 3 Pro vs flash-lite on eval dataset
- Measure: Accuracy improvement, latency increase, cost impact
- Decision: Keep if accuracy gain >5% and cost <2x

**Evaluator Agent:**
- Complexity: Multi-source synthesis, severity calculation, investigation flags
- Test: Run Gemini 3 Pro vs flash-lite on eval dataset
- Measure: Synthesis quality, flag specificity, executive summary coherence
- Decision: Keep if qualitative improvement justifies cost

**Perception/Motion Agents:**
- Keep flash-lite (simple classification, well-defined tasks)

#### 4.2 Report Updates
Update HTML reports to display new architecture outputs:

**Add:**
- Per-window compliance table (window ID, status, violations)
- Severity score and level visualization
- COD region summary (categorical sets, numeric ranges)
- Window distribution chart (IN_ODD / BOUNDARY / OUT_ODD)
- Investigation flags section (separated by severity)
- Executive summary (from Evaluator agent)

**Update:**
- Scenario overview section (link to per-window details)
- Remove collision risk charts (no longer generated)
- Add collision detection events (if any)

**Improve:**
- Visual hierarchy (high-severity violations prominent)
- Contextual alerts (not just counts, but specific windows + conditions)

**Success Criteria:**
- ✅ Reports show which specific windows violated ODD
- ✅ Severity clearly communicated (color-coded, visual)
- ✅ Investigation flags actionable and specific
- ✅ Executive summary provides high-level assessment

**Deliverables:**
- Model performance comparison report
- Updated HTML report template
- Example reports for each severity level
- Model selection recommendation

### Why COD as Abstract Operational Space (Not Physical Space)?
**COD maps to ODD's operational axes, not physical coordinates:**
- ODD defines constraints on lighting, terrain, obstacles, motion dynamics
- COD represents the region in that same abstract space the robot operated within
- Physical position/trajectory is irrelevant for ODD compliance
- Enables direct comparison: does COD region overlap OUT_ODD region?

**Example:** Robot drives 10 meters through office. Physical path is irrelevant. What matters:
- Lighting conditions experienced: ["bright", "dim"]
- Obstacle density range: [0.2, 0.6]
- Terrain observed: ["smooth"]

This is the COD region - operational conditions, not physical space.

### Why Per-Window + Region (Not Just Region)?
**Per-window compliance enables:**
1. **Debugging:** Which specific window caused violation?
2. **Temporal analysis:** When during scenario did violation occur?
3. **Severity calculation:** How many windows violated? How frequently?
4. **Reporting:** Show user exactly where issues happened

**Scenario region enables:**
- Formal ODD/COD comparison (overlap detection)
- Understanding operational envelope
- "Robot operated in lighting conditions X, Y, Z"

Both needed: per-window for specificity, region for overall assessment.

### Why Severity Scoring (Not Binary Pass/Fail)?
**Binary approach problems:**
- "1 isolated violation" treated same as "8 frequent violations"
- Boundary conditions cause false failures
- No differentiation of risk levels

**Severity scoring benefits:**
- **Nuanced:** MINIMAL vs LOW vs HIGH severity
- **Actionable:** Low severity = investigate, High severity = restrict deployment
- **Flexible:** Severity thresholds tunable based on risk tolerance
- **Informative:** Distribution visible (9 IN_ODD + 1 BOUNDARY vs 5 IN_ODD + 5 OUT_ODD)

### Why Separate COD and Evaluator Agents?
**Separation of concerns:**
- COD Agent: Technical analysis (region construction, distance calculation, ODD comparison)
- Evaluator Agent: Synthesis and decision-making (integrate all flags, generate recommendations)

Keeps each agent focused, easier to test/debug/improve independently.

### Why Keep COD Agent at All?
Could Evaluator do everything? Yes, but:
1. **Testability:** COD output can be validated independently
2. **Reusability:** Other systems might want COD region without evaluation
3. **Clarity:** Separates "what happened" (COD) from "is this okay?" (Evaluator)

---

## Success Metrics

### Phase 1 (Manual Validation)
- ✅ New pipeline runs end-to-end without errors
- ✅ COD regions preserve all observed conditions (no averaging)
- ✅ Severity scores differentiate scenarios logically
- ✅ Outputs human-readable and match expectations
- ✅ No violations lost (compare to known ground truth)

### Phase 2 (Performance)
- ✅ 30-50% overall token reduction
- ✅ Faster execution times
- ✅ Same accuracy as Phase 1

### Phase 3 (Evaluation)
- ✅ Per-window accuracy >95%
- ✅ False positive rate <10% (down from 40-60%)
- ✅ False negative rate <5%
- ✅ Severity alignment with ground truth (±1 level)
- ✅ COD regions accurate (0 hallucinations)

### Phase 4 (Final)
- ✅ Reports show per-window violations clearly
- ✅ Severity visually communicated
- ✅ Investigation flags actionable
- ✅ Model performance justified cost tradeoffs

### Qualitative Improvements
- No more "IN_ODD scenario with dark lighting window" contradictions
- Nuanced assessment: "isolated violation" vs "frequent violations"
- Sensor quality issues visible and integrated
- COD represents actual operational region, not fictional point

---

## Migration Strategy

**Approach:** Refactor architecture first, then systematically measure and refine

1. **Phase 1 (Architecture):** Implement new agent designs, validate manually on 3-5 scenarios
2. **Phase 2 (Performance):** Optimize before adding eval overhead
3. **Phase 3 (Evaluation):** Build measurement framework, iterate on prompts/thresholds
4. **Phase 4 (Polish):** Model testing, report updates
5. **Deployment:** Only after Phase 3 metrics meet success criteria

**Feature Branch Development:**
- Implement all changes in `feature/cod-region-redesign` branch
- Keep main branch stable with current (flawed but functional) system
- Merge only after Phase 3 validation complete

**Rationale for Phase Order:**
- Can't measure what doesn't exist (need architecture before evals)
- Manual testing validates macro-level correctness quickly
- Evals catch edge cases and enable fine-tuning
- Performance optimization reduces eval iteration cost

---

## Open Questions

1. **Severity formula tuning:** Current formula `(out_odd × 2.0 + boundary × 0.5) / total × 10` is initial guess
   - May need adjustment based on Phase 3 eval results
   - Should BOUNDARY weight be 0.5 or higher/lower?
   - Should OUT_ODD weight scale with number of axes violated?
   
2. **Overlap quantification:** How to measure "amount" of overlap for numeric axes?
   - Current: Simple range overlap [0.8, 0.85] when COD max exceeds OUT_ODD min
   - Alternative: Weighted by percentage of COD region in OUT_ODD space
   - Needs testing in Phase 1 manual validation
   
3. **COD region visualization:** How to show multidimensional region in 2D report?
   - Per-axis range bars? (simple, clear)
   - Radar chart? (shows multiple axes, but complex)
   - Just tables? (most clear, least visual)
   - Decision: Defer to Phase 4 based on Phase 1 manual review feedback

4. **Collision detection thresholds:** What sensor signatures reliably indicate collision?
   - IMU spike alone? (might be rough terrain, not collision)
   - IMU + velocity drop? (more reliable, but may miss glancing collisions)
   - Need ground truth collision data in Phase 3 to calibrate
   
5. **Model selection cost/quality tradeoff:** When is Gemini 3 Pro worth 2-3x cost?
   - Defer to Phase 4 testing
   - Measure accuracy gain vs cost increase
   - May be worth it for COD/Evaluator, probably not for Perception/Motion

---

## Related Documentation

- **[Current COD Agent](agents/COD_CLASSIFIER.md)**: Current averaging-based implementation
- **[Current Compliance Agent](agents/COMPLIANCE.md)**: Current ODD-only checking
- **[Collision Agent](agents/COLLISION.md)**: Current risk scoring approach
- **[Main Agent Architecture](agents/README.md)**: Current workflow overview
- **[Model Selection Guide](MODEL_SELECTION_GUIDE.md)**: Model recommendations
- **[Lessons Learned](LESSONS_LEARNED.md)**: Production deployment insights

---

## Appendix: Example Scenario Walkthrough

### Scenario: Indoor office with brief dark lighting patch

**Windows:**
```
Window 1: lighting=bright, obstacle_density=0.3, terrain=smooth
Window 2: lighting=bright, obstacle_density=0.4, terrain=smooth
Window 3: lighting=dark,   obstacle_density=0.5, terrain=smooth  ← Problem!
Window 4: lighting=bright, obstacle_density=0.4, terrain=smooth
```

### Current System Output (WRONG)
```json
{
  "cod_classification": {
    "categorical": {
      "lighting": "bright",           // Majority vote lost "dark"
      "terrain": "smooth"
    },
    "numeric": {
      "obstacle_density": 0.4         // Average: (0.3+0.4+0.5+0.4)/4
    }
  },
  "odd_compliance": {
    "overall_compliance": "IN_ODD"    // ✗ WRONG! Window 3 was OUT_ODD
  }
}
```

### Proposed System Output (CORRECT)
```json
{
  "per_window_compliance": [
    {"window_id": "001", "compliance": "IN_ODD"},
    {"window_id": "002", "compliance": "IN_ODD"},
    {
      "window_id": "003",
      "compliance": "OUT_ODD",
      "violations": [
        {"axis": "lighting", "observed": "dark", "allowed": ["bright", "dim"]}
      ]
    },
    {"window_id": "004", "compliance": "IN_ODD"}
  ],
  
  "scenario_cod": {
    "categorical": {
      "lighting": ["bright", "dark"],  // ✓ Preserves "dark" observation
      "terrain": ["smooth"]
    },
    "numeric": {
      "obstacle_density": {"min": 0.3, "max": 0.5}
    }
  },
  
  "odd_overlap_analysis": {
    "cod_within_odd": false,
    "categorical_violations": [
      {
        "axis": "lighting",
        "cod_values": ["bright", "dark"],
        "odd_allowed": ["bright", "dim"],
        "violation_value": "dark",
        "windows_affected": ["003"]
      }
    ]
  },
  
  "window_distribution": {
    "in_odd": 3,
    "boundary": 0,
    "out_odd": 1,
    "total": 4
  },
  
  "severity": {
    "score": 2.0,      // (1 × 2.0 + 0 × 0.5) / 4 × 10 = 5.0... wait, formula needs work
    "level": "LOW",    // Isolated violation
    "assessment": "Isolated ODD exit detected"
  },
  
  "investigation_flags": [
    "Window 003: OUT_ODD due to dark lighting - occurred during brief shadow passage"
  ],
  
  "executive_summary": "Scenario has isolated ODD exit (severity: LOW). Robot briefly operated in dark lighting conditions in window 003. Appears to be transient environmental condition, not systemic issue."
}
```

**Key Difference:** Redesigned system preserves the critical OUT_ODD window instead of averaging it away, provides nuanced severity assessment, and generates specific investigation flag.
