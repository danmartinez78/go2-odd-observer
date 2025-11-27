"""
Perception agent wrapper for ADK evaluation.
Exports an 'agent' variable as required by ADK's AgentEvaluator.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from odd_agents.agents.perception import create_perception_agent

load_dotenv()

# Resolve scenario relative to repo root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
scenario_path = PROJECT_ROOT / "data" / "test" / "sim_test_w010_w011"

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable must be set in .env file")

# Use a reliable model for tool calling in tests
model = "gemini-2.5-pro"
genai_client = genai.Client(api_key=api_key)

# Export agent for ADK evaluation
agent = create_perception_agent(
    scenario_path=scenario_path,
    genai_client=genai_client,
    model=model,
    api_key=api_key,
)
