"""
ODD Agents - Multi-Agent Operational Design Domain Analysis
============================================================

A modular library for analyzing robot sensor data and detecting operational
design domain (ODD) violations using multi-agent AI pipelines.

Core Components:
    - tools: Sensor analysis tool functions (perception, motion, collision)
    - agents: AI agents for different analysis stages
    - utils: Shared utility functions
    - workflow: High-level workflow orchestration

Quick Start:
    >>> from odd_agents import run_odd_workflow
    >>> from google.genai import Client
    >>> 
    >>> client = Client(api_key="your-api-key")
    >>> result = await run_odd_workflow(
    ...     scenario_path="data/processed/runs/sim_run_test",
    ...     genai_client=client,
    ...     api_key="your-api-key"
    ... )
    >>> print(result["report"]["executive_summary"])
"""

__version__ = "0.1.0"
__author__ = "ODD Observer Team"

# Import main components for convenient access
from . import utils
from . import tools
from . import agents

# Re-export commonly used items
from .utils import (
    build_image_path,
    ensure_image_bytes,
    extract_json_block,
)

from .workflow import (
    create_odd_workflow,
    run_odd_workflow,
    extract_final_report,
)

__all__ = [
    # Modules
    "utils",
    "tools",
    "agents",

    # Utils exports
    "build_image_path",
    "ensure_image_bytes",
    "extract_json_block",

    # Workflow exports
    "create_odd_workflow",
    "run_odd_workflow",
    "extract_final_report",
]
