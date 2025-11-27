# Robot Profile: Go2 (v1.0.0)

**Purpose:** Platform-specific context for the Unitree Go2. Use alongside core fundamentals and sensor interpretation docs. Do not override the per-run ODD spec artifact.

## Capabilities & Envelope
- Designed for indoor commercial/residential environments.
- Comfortable speed envelope: up to ~1.5 m/s for navigation; higher speeds not typical indoors.
- Moderate acceleration bursts are normal during obstacle avoidance; sustained high accel is atypical.
- Turning in place is supported; tight maneuvers expected in furniture-dense areas.

## Sensor Notes
- **Camera:** Needs at least moderate lighting; very dark scenes reduce reliability.
- **LiDAR/BEV:** Accumulates clean indoor occupancy; expect low clutter. Cropping removes empty borders—focus on center activity.
- **IMU:** Stable signals; brief spikes can occur during quick turns or stops.

## Common Patterns (Indoor)
- Bright to moderate lighting; smooth floors; low to moderate obstacle density (furniture, desks).
- Close obstacle proximity is normal; clearances down to ~5–10 cm can occur in tight navigation.

## Cautions
- Avoid stairs/steep ramps (>~15°) and outdoor terrain.
- Feature-poor areas (blank walls, uniform floors) can challenge vision-based localization; cross-check with IMU.
- Do not infer new limits from this profile; use it as contextual guidance only.
