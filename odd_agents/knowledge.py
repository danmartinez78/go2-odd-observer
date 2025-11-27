"""
Knowledge/Reference manifest helpers.

These utilities keep knowledge artifacts modular and swappable:
- A core fundamentals doc (robot-agnostic).
- Optional robot/application/ODD overlays.
- A manifest mapping to tell agents which docs apply for a run.

Usage:
    manifest = build_reference_manifest(
        fundamentals_artifact="artifact:odd_cod_fundamentals_v1",
        robot_artifact="artifact:robot_go2_v1",
        app_artifact="artifact:app_generic_v1",
        odd_artifact=None,
    )
    memory_seed = build_memory_seed_entries(
        manifest=manifest,
        fundamentals_sections=default_fundamentals_sections(
            fundamentals_artifact="artifact:odd_cod_fundamentals_v1"
        ),
    )
The resulting dict can be written into session memory (e.g., ADK SessionService).
"""

from typing import Dict, Optional, Any


def build_reference_manifest(
    *,
    fundamentals_artifact: str,
    robot_artifact: Optional[str] = None,
    app_artifact: Optional[str] = None,
    odd_artifact: Optional[str] = None,
    sensors_artifact: Optional[str] = None,
    sensor_overlay_artifact: Optional[str] = None,
) -> Dict[str, str]:
    """Create a manifest of knowledge artifacts for a run.

    All keys are additive; omit entries you do not need.
    """
    manifest: Dict[str, str] = {"fundamentals": fundamentals_artifact}
    if robot_artifact:
        manifest["robot"] = robot_artifact
    if app_artifact:
        manifest["app"] = app_artifact
    if odd_artifact:
        manifest["odd"] = odd_artifact
    if sensors_artifact:
        manifest["sensors"] = sensors_artifact
    if sensor_overlay_artifact:
        manifest["sensors_overlay"] = sensor_overlay_artifact
    return manifest


def default_fundamentals_sections(
    *,
    fundamentals_artifact: str,
) -> Dict[str, Any]:
    """Painless default section pointers for the fundamentals doc.

    Agents can use these anchors to cite specific parts of the doc
    without loading the entire thing.
    """
    return {
        "artifact": fundamentals_artifact,
        "sections": {
            "definitions": f"{fundamentals_artifact}#core-definitions",
            "verdicts": f"{fundamentals_artifact}#verdict-criteria",
            "axis_naming": f"{fundamentals_artifact}#axis-types--naming-stay-aligned-with-odd-spec-agent",
            "sensors": f"{fundamentals_artifact}#sensor-interpretation-guidance",
            "reasoning": f"{fundamentals_artifact}#reasoning-patterns",
        },
    }


def default_sensor_sections(
    *,
    sensors_artifact: str,
    sensors_overlay_artifact: Optional[str] = None,
) -> Dict[str, Any]:
    """Default section pointers for sensor interpretation docs.

    If an overlay is provided, return both core and overlay references so
    agents can prefer overlay-specific cautions without losing the core.
    """
    sections = {
        "artifact": sensors_artifact,
        "sections": {
            "bev": f"{sensors_artifact}#bev-basics",
            "camera": f"{sensors_artifact}#camera-basics",
            "imu": f"{sensors_artifact}#imu-basics",
            "collision_cues": f"{sensors_artifact}#collisionanomaly-cues",
        },
    }
    if sensors_overlay_artifact:
        sections["overlay"] = {
            "artifact": sensors_overlay_artifact,
            "sections": {
                "bev": f"{sensors_overlay_artifact}#bev-basics",
                "camera": f"{sensors_overlay_artifact}#camera-basics",
                "imu": f"{sensors_overlay_artifact}#imu-basics",
                "collision_cues": f"{sensors_overlay_artifact}#collisionanomaly-cues",
            },
        }
    return sections


def build_memory_seed_entries(
    *,
    manifest: Dict[str, str],
    fundamentals_sections: Optional[Dict[str, Any]] = None,
    sensor_sections: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prepare memory key/value pairs for seeding session memory.

    Returns a dict suitable for writing directly to a memory store.
    """
    seeds: Dict[str, Any] = {
        "ref:knowledge_manifest": manifest,
    }
    if fundamentals_sections:
        seeds["ref:odd_cod_fundamentals"] = fundamentals_sections
    if sensor_sections:
        seeds["ref:sensor_interpretation"] = sensor_sections
    return seeds
