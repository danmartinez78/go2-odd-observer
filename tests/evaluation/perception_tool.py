"""
Perception tool (inference) wrapper for ADK evaluation.
This tests the actual multimodal perception analysis, not the orchestration loop.

This is where the REAL AI work happens:
- Multimodal vision analysis (camera + LiDAR BEV)
- Scene understanding (lighting, terrain, obstacles)
- Constraint detection (humans, traversability)
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from odd_agents.tools.perception import create_perception_tools

# Load environment variables
load_dotenv()

# Setup
scenario_path = Path("data/processed/runs/sim_run_test")
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError(
        "GOOGLE_API_KEY environment variable must be set in .env file")

model = "gemini-2.0-flash-lite"
genai_client = genai.Client(api_key=api_key)

# Create the perception tools
_, analyze_window_tool = create_perception_tools(
    scenario_path=scenario_path,
    genai_client=genai_client,
    model=model
)

# Wrap the tool in a simple agent for ADK evaluation
# This agent just calls the analyze_window_perception_tool directly


def create_agent():
    """Lazy agent creation to avoid initialization at import time."""
    return Agent(
        name="PerceptionToolAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[analyze_window_tool],
        instruction="""You are testing the perception analysis tool.

When asked to analyze a window, call analyze_window_perception_tool with the window_id.
Return the tool response as JSON without modification or commentary."""
    )


# ADK expects 'agent' variable
agent = create_agent()
