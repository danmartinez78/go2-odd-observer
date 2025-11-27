"""Export OddSpecAgent for ADK evaluation.

This agent has NO TOOLS - it's a single LLM inference agent that converts
natural language ODD descriptions into structured JSON specifications.

Key differences from loop agents:
- No tool calls (no list_windows, no analyze_* tools)
- Input: Natural language text (user request string)
- Output: Structured JSON with ODD specification
- Test approach: Multiple NL descriptions → validate JSON structure + content
"""

import os
from dotenv import load_dotenv
from odd_agents.agents.odd_spec import create_odd_spec_agent

load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")
MODEL = "gemini-2.5-pro"

# Export agent instance (ADK requires it to be named 'agent')
agent = create_odd_spec_agent(API_KEY, MODEL)
