"""
ODD Agents - Multi-Agent Operational Design Domain Analysis
============================================================

A modular library for analyzing robot sensor data and detecting operational
design domain (ODD) violations using multi-agent AI pipelines.

Architecture (Phase 1.4.4 - Nov 2025):
    Type-Driven COD Construction:
    - Sensor agents with Python tools for deterministic measurements
    - Evaluator agent for COD construction + compliance
    - Report agent with statistics tools (hybrid LLM + Python)
    - Post-pipeline report builder for comprehensive data capture
    
    Key Features:
    - ODD-Schema Driven: Agents adapt to any ODD structure dynamically
    - Hybrid Reporting: Python statistics + LLM synthesis
    - Token Efficient: Tools compute, LLM interprets
    - Cost Optimization: Flash-exp + thinking models as needed

Core Components:
    - tools: Sensor analysis tool functions (perception, motion, collision, cod_construction)
    - agents: AI agents for different analysis stages
    - utils: Shared utility functions
    - workflow: High-level workflow orchestration
    - report_builder: Post-pipeline report assembly

Quick Start:
    >>> from odd_agents import run_odd_workflow
    >>> from google.genai import Client
    >>> 
    >>> client = Client(api_key="your-api-key")
    >>> result = await run_odd_workflow(
    ...     scenario_path="data/test/sim/sim_test_w010_w011",
    ...     genai_client=client,
    ...     api_key="your-api-key"
    ... )
    >>> print(result["report"]["executive_summary"])
    >>> # Access full technical report
    >>> print(result["reports"]["full_technical"]["statistics"])
"""

__version__ = "1.4.4"  # Phase 1.4.4: Type-Driven COD + Hybrid Reporting
__author__ = "ODD Observer Team"

# Import main components for convenient access
from . import utils
from . import tools
from . import agents
from . import report_builder

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

from .report_builder import (
    generate_reports,
    extract_all_agent_outputs,
    build_executive_summary_report,
    build_full_technical_report,
)

__all__ = [
    # Modules
    "utils",
    "tools",
    "agents",
    "report_builder",

    # Utils exports
    "build_image_path",
    "ensure_image_bytes",
    "extract_json_block",

    # Workflow exports
    "create_odd_workflow",
    "run_odd_workflow",
    "extract_final_report",

    # Report builder exports
    "generate_reports",
    "extract_all_agent_outputs",
    "build_executive_summary_report",
    "build_full_technical_report",
]
