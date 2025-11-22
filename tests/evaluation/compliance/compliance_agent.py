"""Export OddComplianceAgent for ADK evaluation.

This agent has NO TOOLS - it's a single LLM inference agent that compares
ODD specification against categorical ODD to assess compliance.

Key differences from loop agents:
- No tool calls (no list_windows, no analyze_* tools)
- Input: Mock context data (temp:odd_spec, temp:cod_classification)
- Output: JSON with compliance assessment and gap analysis
- Test approach: Mock context → validate compliance logic + JSON structure
"""

import os
from dotenv import load_dotenv
from odd_agents.agents.compliance import create_odd_compliance_agent

load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")
MODEL = "gemini-2.0-flash-exp"

# Export agent instance (ADK requires it to be named 'agent')
agent = create_odd_compliance_agent(API_KEY, MODEL)
