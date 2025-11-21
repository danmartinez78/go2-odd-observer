"""
Configuration module for ODD Agents.
Contains model assignments, paths, and API setup.
Extracted from odd_workflow_full.py (reference implementation).
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# =============================================================================
# Project Paths
# =============================================================================

# Determine project root (works from anywhere in the package)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "runs"

# Global scenario path (can be overridden)
SCENARIO_PATH = DATA_DIR / "sim_run_new"  # Default: Full dataset (13 windows)


# =============================================================================
# API Configuration
# =============================================================================

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise SystemExit(
        "❌ GOOGLE_API_KEY not found. Set it in your environment or .env file.")

# Initialize Gemini client (singleton)
GENAI_CLIENT = genai.Client(api_key=GOOGLE_API_KEY)


# =============================================================================
# Model Assignments (Optimized for Cost/Performance)
# =============================================================================

# Vision-heavy agents use 2.5-pro for accuracy
GEMINI_MODEL_PERCEPTION = "gemini-2.5-pro"

# Data aggregation agents use 2.5-pro to preserve structure
GEMINI_MODEL_MOTION = "gemini-2.5-pro"

# Complex multimodal fusion
GEMINI_MODEL_COLLISION = "gemini-2.5-pro"

# JSON synthesis only
GEMINI_MODEL_ODD_SPEC = "gemini-2.0-flash-lite"

# Comparison logic
GEMINI_MODEL_COD = "gemini-2.0-flash-lite"

# High-quality report generation
GEMINI_MODEL_REPORT = "gemini-2.5-pro"


# =============================================================================
# Helper Functions
# =============================================================================

def set_scenario(scenario_name: str) -> Path:
    """
    Set the active scenario path.

    Args:
        scenario_name: Name of scenario directory (e.g., "sim_run_test")

    Returns:
        Path to the scenario directory
    """
    global SCENARIO_PATH
    SCENARIO_PATH = DATA_DIR / scenario_name
    return SCENARIO_PATH


def get_scenario_path() -> Path:
    """Get the current scenario path."""
    return SCENARIO_PATH
