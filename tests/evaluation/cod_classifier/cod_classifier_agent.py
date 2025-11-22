"""Export COD Classifier Agent for ADK evaluation.

This agent has NO TOOLS - it's a single LLM inference agent that synthesizes
perception, motion, and collision analyses into a categorical ODD (COD) classification.

Key differences from loop agents:
- No tool calls (no list_windows, no analyze_* tools)
- Input: Mock context data ({temp:perception_analysis}, {temp:motion_analysis}, {temp:collision_analysis})
- Output: JSON with categorical ODD classification
- Test approach: Mock varied context data → validate JSON structure + synthesis quality
"""

import os
from dotenv import load_dotenv
from odd_agents.agents.cod_classifier import create_cod_classifier_agent

load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")
MODEL = "gemini-2.0-flash-exp"

# Export agent instance (ADK requires it to be named 'agent')
agent = create_cod_classifier_agent(API_KEY, MODEL)
