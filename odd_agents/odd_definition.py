"""
Centralized ODD (Operational Design Domain) Definition

This module provides the single source of truth for the robot's ODD description.
All scripts should import DEFAULT_ODD_DESCRIPTION from here rather than defining
their own copies.

Version: 2.0.0 (2025-11-29)
Changes:
- Added human/animal proximity constraint
- Softened terrain to allow low-pile carpet
- Removed collision references (collision is advisory, not ODD axis)
- Added BEV + camera fusion guidance for terrain assessment
"""

# Version tracking for ODD definition changes
ODD_DEFINITION_VERSION = "2.0.0"

DEFAULT_ODD_DESCRIPTION = """
The Unitree Go2 is a quadruped robot designed for general indoor navigation in 
residential and commercial spaces.

ROBOT PHYSICAL SPECIFICATIONS (EGO VEHICLE):
- Footprint: 0.65m length × 0.31m width (standing posture)
- Height: 0.40m (standing), 0.25m (crouching)
- Minimum passable gap: 0.4m width for straight corridors
- Comfortable clearance: 0.5m+ width for maneuvering around obstacles
- Turning radius: ~0.3m (can rotate in place)

ENVIRONMENT:
The robot operates in typical indoor environments including homes, offices, hallways, 
conference rooms, living rooms, and workspaces. It handles smooth floors (tile, 
hardwood, low-pile carpet) and requires adequate lighting for camera-based perception. 
Bright to moderate lighting is ideal; very dim areas are acceptable but pitch-black 
rooms are outside operational limits.

OBSTACLE HANDLING:
Designed for furniture-dense residential spaces with moderate to high obstacle density. 
The robot can navigate around sofas, coffee tables, dining chairs, desk legs, and 
typical household items. Close proximity to furniture is expected and normal during 
navigation. The robot is NOT designed for extreme clutter where clear navigation paths 
are blocked, doorways are obstructed, or the floor is covered with scattered objects.

MOTION CHARACTERISTICS:
The robot uses dynamic motion control appropriate for agile quadruped navigation:
- Smooth motion during open navigation in hallways and clear spaces
- Quick reactive maneuvers when avoiding obstacles (acceleration up to 10 m/s²)
- Brief "abrupt" motion is normal and expected during:
  * Obstacle avoidance reactions
  * Direction changes around furniture
  * Emergency stops when unexpected obstacles appear
  
The robot is NOT designed for:
- Aggressive high-speed racing or sustained high acceleration
- Violent or erratic motion when operating in open, obstacle-free spaces

TERRAIN:
Designed for flat, stable indoor surfaces. Can handle:
- Smooth floors (hardwood, tile, laminate)
- Low-pile carpet and area rugs (common residential flooring)
- Gentle transitions between rooms (door thresholds, slight elevation changes)
- Minor surface variations (rug edges, mat transitions)
- Gentle ramps (<15 degree incline)

NOT designed for:
- Staircases (multi-step elevation changes)
- Steep ramps (>15 degree incline)
- Outdoor terrain (gravel, grass, dirt, uneven ground)
- Unstable surfaces (sand, loose materials)
- High-pile carpet or shag rugs

HUMAN/ANIMAL PROXIMITY:
The robot is NOT designed to operate in close proximity to humans or animals.
- Persons or pets within ~0.5-1m while the robot is navigating = OUT OF ODD
- Robot should maintain safe distance from people and animals at all times
- Brief passing at >1m distance is acceptable; sustained close proximity is not

DEFINITELY NOT DESIGNED FOR:
- Outdoor environments (weather exposure, GPS reliance, rough terrain)
- Dark rooms where camera sensors cannot function
- Industrial environments with heavy machinery or hazardous materials
- Extreme clutter where navigation paths are completely blocked
- Environments requiring climbing (stairs, steep slopes >15°)
- High-speed applications or aggressive maneuvering
- Operating near humans or animals at close range (<1m while navigating)
"""

# Short summary for quick reference
ODD_SUMMARY = """
Indoor quadruped robot for residential/commercial navigation.
- Environment: Indoor, furniture-dense, adequate lighting
- Terrain: Smooth floors, low-pile carpet, gentle ramps (<15°)
- Motion: Agile with reactive maneuvers up to 10 m/s²
- Constraints: No stairs, no outdoor, no humans/animals within 0.5-1m
"""
