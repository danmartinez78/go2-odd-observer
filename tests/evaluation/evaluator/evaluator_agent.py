"""
Evaluator agent wrapper for ADK evaluation.
Exports an 'agent' variable as required by ADK's AgentEvaluator.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from odd_agents.agents.evaluator import create_evaluator_agent

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
fixture_path = PROJECT_ROOT / "tests" / "evaluation" / "fixtures" / "eval_report"

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable must be set in .env file")

# Use stable model for tool calling
model = "gemini-2.5-pro"
genai_client = genai.Client(api_key=api_key)

agent = create_evaluator_agent(
    scenario_path=fixture_path,
    genai_client=genai_client,
    model=model,
    api_key=api_key,
)
