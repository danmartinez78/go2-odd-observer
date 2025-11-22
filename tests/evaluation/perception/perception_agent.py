"""
Perception agent wrapper for ADK evaluation.
This module exports an 'agent' variable as required by ADK's AgentEvaluator.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from odd_agents.agents.perception import create_perception_loop_agent

# Load environment variables from .env
load_dotenv()

# Setup
scenario_path = Path("data/processed/runs/sim_run_test")
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError(
        "GOOGLE_API_KEY environment variable must be set in .env file"
    )

model = "gemini-2.0-flash-lite"

# Create genai client
genai_client = genai.Client(api_key=api_key)

# Export agent for ADK evaluation
agent = create_perception_loop_agent(
    scenario_path=scenario_path,
    genai_client=genai_client,
    model=model,
    api_key=api_key
)
