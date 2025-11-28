# Robot Profile: Go2 (v1.1.0)

**Purpose:** Platform-specific context for the Unitree Go2. Use alongside core fundamentals and sensor interpretation docs. Do not override the per-run ODD spec artifact.

## Capabilities & Envelope
- Designed for indoor commercial/residential environments.
- Comfortable speed envelope: up to ~1.5 m/s for navigation; higher speeds not typical indoors.
- Moderate acceleration bursts are normal during obstacle avoidance; sustained high accel is atypical.
- Turning in place is supported; tight maneuvers expected in furniture-dense areas.

## Sensor Hardware
- **Camera:** Forward-facing monocular RGB. 1280×720 resolution, global shutter. Occasional video artifacts observed in real-world data (compression, exposure shifts).
- **LiDAR:** Unitree L1 (forward-facing). Can produce single scans or accumulated point cloud maps. See `SENSOR_INTERPRETATION.md` for how scan type affects BEV.
- **IMU:** Integrated IMU with gravity-corrected acceleration. Stable signals; brief spikes during quick turns or stops are normal.

## Common Patterns (Indoor)
- Bright to moderate lighting; smooth floors; low to moderate obstacle density (furniture, desks).
- Close obstacle proximity is normal; clearances down to ~5–10 cm can occur in tight navigation.

## Cautions
- Avoid stairs/steep ramps (>~15°) and outdoor terrain.
- Feature-poor areas (blank walls, uniform floors) can challenge vision-based localization; cross-check with IMU.
- Do not infer new limits from this profile; use it as contextual guidance only.

---

## TODO: Robot Specification Migration
> **Future work:** Consider moving detailed robot specifications (dimensions, weight, sensor FOV, max speeds, etc.) from the natural language ODD and ODD Spec Agent output into this profile document. This would allow:
> - The NL ODD to simply state "the robot is a Go2 quadruped robot"
> - The ODD Spec Agent to either populate full specs from this knowledge profile, or all agents to reference this profile for salient robot information
> - Cleaner separation: ODD defines operational constraints, profile defines platform capabilities
