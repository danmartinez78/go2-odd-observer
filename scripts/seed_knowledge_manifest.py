#!/usr/bin/env python3
"""
Seed knowledge manifest and reference pointers into a session.

This is optional; the pipeline reads these keys if present:
- ref:knowledge_manifest: mapping of applicable reference artifacts
- ref:odd_cod_fundamentals: section anchors for fundamentals doc
- ref:sensor_interpretation: section anchors for sensor interpretation doc

Usage:
    python scripts/seed_knowledge_manifest.py --app OddWorkflowApp --user odd_analysis
"""

import argparse
import asyncio
import json
from odd_agents.knowledge import (
    build_reference_manifest,
    default_fundamentals_sections,
    default_sensor_sections,
    build_memory_seed_entries,
)
from google.adk.sessions import InMemorySessionService


async def main(app_name: str, user_id: str):
    session_service = InMemorySessionService()

    # Example artifact identifiers with explicit versions
    fundamentals_artifact = "artifact:odd_cod_fundamentals_v1"
    sensors_artifact = "artifact:sensor_interpretation_core_v1"
    robot_overlay = None  # e.g., "artifact:robot_go2_profile_v1"
    app_overlay = None    # e.g., "artifact:app_generic_profile_v1"

    manifest = build_reference_manifest(
        fundamentals_artifact=fundamentals_artifact,
        robot_artifact=robot_overlay,
        app_artifact=app_overlay,
        sensors_artifact=sensors_artifact,
    )

    fundamentals_sections = default_fundamentals_sections(
        fundamentals_artifact=fundamentals_artifact
    )
    sensor_sections = default_sensor_sections(
        sensors_artifact=sensors_artifact,
        sensors_overlay_artifact=None,
    )

    seeds = build_memory_seed_entries(
        manifest=manifest,
        fundamentals_sections=fundamentals_sections,
        sensor_sections=sensor_sections,
    )

    # Create a session with seeded state
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        state=seeds,
    )

    print(f"Created session {session.id} with seeded knowledge references:")
    print(json.dumps(seeds, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed knowledge manifest into a session")
    parser.add_argument("--app", default="OddWorkflowApp", help="App name")
    parser.add_argument("--user", default="odd_analysis", help="User id")
    args = parser.parse_args()
    asyncio.run(main(app_name=args.app, user_id=args.user))
