"""
ODD Agents - Multi-Agent Operational Design Domain Analysis
============================================================

A modular library for analyzing robot sensor data and detecting operational
design domain (ODD) violations using multi-agent AI pipelines.

Core Components:
    - tools: Sensor analysis tool functions (perception, motion, collision)
    - agents: AI agents for different analysis stages
    - config: Configuration, model assignments, paths
    - utils: Shared utility functions
    - workflow: High-level workflow orchestration

Quick Start:
    >>> from odd_agents import run_odd_workflow
    >>> result = await run_odd_workflow(scenario_name="sim_run_test")
    >>> print(result["report"]["executive_summary"])

For more control:
    >>> from odd_agents import odd_workflow, set_scenario
    >>> from google.adk.runners import InMemoryRunner
    >>> 
    >>> set_scenario("my_scenario")
    >>> runner = InMemoryRunner(agent=odd_workflow, app_name="MyApp")
    >>> # ... customize and run workflow
"""

__version__ = "0.1.0"
__author__ = "ODD Observer Team"

# Import main components for convenient access
from . import config
from . import utils
from . import tools
from . import agents

# Re-export commonly used items
from .config import (
    GOOGLE_API_KEY,
    GENAI_CLIENT,
    GEMINI_MODEL_PERCEPTION,
    GEMINI_MODEL_MOTION,
    GEMINI_MODEL_COLLISION,
    GEMINI_MODEL_ODD_SPEC,
    GEMINI_MODEL_COD,
    GEMINI_MODEL_REPORT,
    set_scenario,
    get_scenario_path,
)

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
    "config",
    "utils",
    "tools",
    "agents",

    # Config exports
    "GOOGLE_API_KEY",
    "GENAI_CLIENT",
    "GEMINI_MODEL_PERCEPTION",
    "GEMINI_MODEL_MOTION",
    "GEMINI_MODEL_COLLISION",
    "GEMINI_MODEL_ODD_SPEC",
    "GEMINI_MODEL_COD",
    "GEMINI_MODEL_REPORT",
    "set_scenario",
    "get_scenario_path",

    # Utils exports
    "build_image_path",
    "ensure_image_bytes",
    "extract_json_block",

    # Workflow exports
    "create_odd_workflow",
    "run_odd_workflow",
    "extract_final_report",
]
