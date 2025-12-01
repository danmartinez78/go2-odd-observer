"""
ODD specification tools with strict parameter enforcement.

Ensures ODD spec structure is consistent for downstream COD construction.

Data flow:
- Artifact: odd_spec.json (full structured spec for COD tool)
- State: temp:odd_spec_summary (text summary for agent prompts)
"""

import json
from typing import Any, Dict, List
from google.adk.tools import FunctionTool
import google.genai.types as gtypes


def create_odd_spec_tools():
    """Create tools for ODD specification agent."""

    async def save_odd_spec_tool(
        # Environment axes
        environment_categorical: List[Dict[str, Any]],
        environment_numeric: List[Dict[str, Any]],
        environment_boolean: List[Dict[str, Any]],
        # Actors axes (optional - may be empty)
        actors_categorical: List[Dict[str, Any]],
        actors_numeric: List[Dict[str, Any]],
        actors_boolean: List[Dict[str, Any]],
        # Ego axes
        ego_categorical: List[Dict[str, Any]],
        ego_numeric: List[Dict[str, Any]],
        ego_boolean: List[Dict[str, Any]],
        tool_context
    ) -> Dict[str, Any]:
        """Save ODD specification as artifact with enforced structure.

        ARTIFACTS (structured data for tools):
        - odd_spec.json: Full ODD specification for COD construction

        Args:
            environment_categorical: List of enum axes for environment domain.
                Each: {"name": str, "allowed": [str], "description": str}
            environment_numeric: List of range axes for environment domain.
                Each: {"name": str, "min": float, "max": float, "description": str}
            environment_boolean: List of bool axes for environment domain.
                Each: {"name": str, "allowed": 0 or 1, "description": str}
            actors_categorical: List of enum axes for actors domain.
            actors_numeric: List of range axes for actors domain.
            actors_boolean: List of bool axes for actors domain.
            ego_categorical: List of enum axes for ego domain.
            ego_numeric: List of range axes for ego domain.
            ego_boolean: List of bool axes for ego domain.
            tool_context: ADK tool context for artifact/state access.

        Example call:
            save_odd_spec_tool(
                environment_categorical=[
                    {"name": "lighting_conditions", "allowed": ["bright", "moderate", "dim"], "description": "Ambient light level"},
                    {"name": "terrain_type", "allowed": ["smooth", "slightly_rough"], "description": "Ground surface"}
                ],
                environment_numeric=[
                    {"name": "obstacle_density", "min": 0.0, "max": 0.7, "description": "Spatial obstacle density (0-1)"},
                    {"name": "clearance_index", "min": 0.3, "max": 1.0, "description": "Navigation ease from BEV (0-1)"}
                ],
                environment_boolean=[
                    {"name": "stairs_present", "allowed": 0, "description": "Whether stairs are accessible"}
                ],
                actors_categorical=[],
                actors_numeric=[
                    {"name": "min_proximity_m", "min": 0.3, "max": 10.0, "description": "Min safe distance to actors"}
                ],
                actors_boolean=[],
                ego_categorical=[],
                ego_numeric=[
                    {"name": "max_speed_mps", "min": 0.0, "max": 1.5, "description": "Max linear velocity"},
                    {"name": "max_accel_mps2", "min": 0.0, "max": 10.0, "description": "Max acceleration"}
                ],
                ego_boolean=[]
            )
        """
        print("\n🟡 [SAVE_ODD_SPEC] Building structured ODD specification...")

        def build_domain(categorical: List[Dict], numeric: List[Dict], boolean: List[Dict]) -> Dict[str, Any]:
            """Build domain structure from axis lists."""
            domain = {"categorical": {}, "numeric": {}, "boolean": {}}

            for axis in categorical:
                name = axis.get("name", "unknown")
                domain["categorical"][name] = {
                    "type": "enum",
                    "allowed": axis.get("allowed", []),
                    "description": axis.get("description", "")
                }

            for axis in numeric:
                name = axis.get("name", "unknown")
                domain["numeric"][name] = {
                    "type": "range",
                    "min": axis.get("min", 0.0),
                    "max": axis.get("max", 1.0),
                    "description": axis.get("description", "")
                }

            for axis in boolean:
                name = axis.get("name", "unknown")
                domain["boolean"][name] = {
                    "type": "bool",
                    "allowed": axis.get("allowed", 0),
                    "description": axis.get("description", "")
                }

            return domain

        # Build the full ODD specification structure
        odd_specification = {
            "odd_specification": {
                "environment": build_domain(
                    environment_categorical,
                    environment_numeric,
                    environment_boolean
                ),
                "actors": build_domain(
                    actors_categorical,
                    actors_numeric,
                    actors_boolean
                ),
                "ego": build_domain(
                    ego_categorical,
                    ego_numeric,
                    ego_boolean
                )
            }
        }

        # Count axes per domain
        env_count = len(environment_categorical) + \
            len(environment_numeric) + len(environment_boolean)
        actors_count = len(actors_categorical) + \
            len(actors_numeric) + len(actors_boolean)
        ego_count = len(ego_categorical) + len(ego_numeric) + len(ego_boolean)
        total_axes = env_count + actors_count + ego_count

        print(
            f"🟡 [SAVE_ODD_SPEC] Environment: {len(environment_categorical)} cat, {len(environment_numeric)} num, {len(environment_boolean)} bool")
        print(
            f"🟡 [SAVE_ODD_SPEC] Actors: {len(actors_categorical)} cat, {len(actors_numeric)} num, {len(actors_boolean)} bool")
        print(
            f"🟡 [SAVE_ODD_SPEC] Ego: {len(ego_categorical)} cat, {len(ego_numeric)} num, {len(ego_boolean)} bool")
        print(f"🟡 [SAVE_ODD_SPEC] Total axes: {total_axes}")

        try:
            # === ARTIFACT: Full structured spec for COD tool ===
            json_bytes = json.dumps(
                odd_specification, indent=2).encode('utf-8')
            artifact = gtypes.Part.from_bytes(
                data=json_bytes, mime_type="application/json")
            version = await tool_context.save_artifact(filename="odd_spec.json", artifact=artifact)
            print(f"🟡 [SAVE_ODD_SPEC] Saved artifact v{version}")

            # Build axis name lists for summary
            env_axes = [a["name"] for a in environment_categorical +
                        environment_numeric + environment_boolean]
            actor_axes = [a["name"] for a in actors_categorical +
                          actors_numeric + actors_boolean]
            ego_axes = [a["name"]
                        for a in ego_categorical + ego_numeric + ego_boolean]

            # Return full spec plus metadata (agent will create summary)
            return {
                "status": "saved",
                "artifact": "odd_spec.json",
                "version": version,
                "odd_specification": odd_specification,  # Full spec for agent
                "total_axes": total_axes,
                "domains": {
                    "environment": {"count": env_count, "axes": env_axes},
                    "actors": {"count": actors_count, "axes": actor_axes},
                    "ego": {"count": ego_count, "axes": ego_axes}
                }
            }
        except Exception as e:
            print(f"🟡 [SAVE_ODD_SPEC] Error: {e}")
            return {"status": "error", "message": str(e)}

    async def load_odd_spec_tool(domain: str, tool_context) -> Dict[str, Any]:
        """Load ODD specification from artifact and return relevant domain.

        Args:
            domain: Which domain to load - "environment", "actors", "ego", or "all"
            tool_context: ADK tool context for artifact access

        Returns:
            Dict with the requested domain's axes and their specifications.
            If domain="all", returns the entire ODD specification.

        Example:
            # Get just environment axes for perception agent
            result = load_odd_spec_tool(domain="environment")
            # Returns: {"categorical": {...}, "numeric": {...}, "boolean": {...}}

            # Get ego axes for motion agent  
            result = load_odd_spec_tool(domain="ego")
            # Returns: {"categorical": {...}, "numeric": {...}, "boolean": {...}}
        """
        print(f"\n🟡 [LOAD_ODD_SPEC] Loading domain: {domain}")

        try:
            # Load artifact
            artifact = await tool_context.load_artifact(filename="odd_spec.json")
            if not artifact:
                return {"status": "error", "message": "odd_spec.json artifact not found"}

            if hasattr(artifact, 'inline_data') and artifact.inline_data:
                raw_data = artifact.inline_data.data
                if isinstance(raw_data, bytes):
                    odd_spec = json.loads(raw_data.decode('utf-8'))
                else:
                    odd_spec = json.loads(raw_data)
            else:
                return {"status": "error", "message": "Artifact has no inline_data"}

            spec = odd_spec.get("odd_specification", {})

            if domain == "all":
                print(
                    f"🟡 [LOAD_ODD_SPEC] Returning full spec with {len(spec)} domains")
                return {"status": "loaded", "odd_specification": spec}
            elif domain in spec:
                domain_spec = spec[domain]
                # Count axes
                cat_count = len(domain_spec.get("categorical", {}))
                num_count = len(domain_spec.get("numeric", {}))
                bool_count = len(domain_spec.get("boolean", {}))
                print(
                    f"🟡 [LOAD_ODD_SPEC] {domain}: {cat_count} cat, {num_count} num, {bool_count} bool")
                return {"status": "loaded", "domain": domain, "spec": domain_spec}
            else:
                return {"status": "error", "message": f"Unknown domain: {domain}"}

        except Exception as e:
            print(f"🟡 [LOAD_ODD_SPEC] Error: {e}")
            return {"status": "error", "message": str(e)}

    return [
        FunctionTool(func=save_odd_spec_tool),
        FunctionTool(func=load_odd_spec_tool)
    ]
