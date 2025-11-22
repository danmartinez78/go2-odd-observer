"""Export ReportAgent for ADK evaluation.

This agent has NO TOOLS - it's a single LLM inference agent that aggregates
all previous agent outputs into a comprehensive final report.

Key differences from loop agents:
- No tool calls (no list_windows, no analyze_* tools)
- Input: Mock context data for all {temp:*} outputs
- Output: Structured JSON with executive summary + full analysis
- Test approach: Complete mock context → validate JSON structure + aggregation quality
"""

import os
from dotenv import load_dotenv
from odd_agents.agents.report import create_report_agent

load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")
MODEL = "gemini-2.0-flash-exp"

# Export agent instance (ADK requires it to be named 'agent')
agent = create_report_agent(API_KEY, MODEL)
