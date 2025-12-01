#!/usr/bin/env python3
"""
Toy example to test ADK blackboard state access from tools.

Goal: Understand how tool_context.state works with output_key
"""
import asyncio
import os
import json
from pathlib import Path

from dotenv import load_dotenv
from google.genai import Client
from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.adk.runners import InMemoryRunner

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")


# =============================================================================
# AGENT 1: Producer - writes data to blackboard
# =============================================================================
def create_producer_agent(api_key: str) -> Agent:
    """Agent that produces data and stores it via output_key."""
    return Agent(
        name="ProducerAgent",
        model=Gemini(model="gemini-2.0-flash-exp", api_key=api_key),
        output_key="temp:producer_output",
        instruction="""You are a data producer. Output this exact JSON:
{
  "measurements": {
    "temperature": 25.5,
    "humidity": 60
  },
  "status": "ok"
}

Output JSON only, no markdown.""",
    )


# =============================================================================
# AGENT 2: Consumer - reads data from blackboard via tool
# =============================================================================
def create_consumer_tools():
    """Create tools that read from blackboard."""
    from google.adk.tools.tool_context import ToolContext

    async def read_producer_data_tool(tool_context: ToolContext) -> str:
        """Read data from producer agent via blackboard."""
        results = {}

        # Explore tool_context attributes
        results["tool_context_attrs"] = [
            a for a in dir(tool_context) if not a.startswith('_')]

        # Check state type and access
        results["state_type"] = str(type(tool_context.state))

        # Try state.get
        results["state.get('temp:producer_output')"] = tool_context.state.get(
            "temp:producer_output")

        # Try direct attribute access on state
        try:
            results["state.__dict__"] = str(tool_context.state.__dict__)[:500]
        except Exception as e:
            results["state.__dict__"] = str(e)

        # Check if there's session_state or session
        if hasattr(tool_context, 'session'):
            results["has_session"] = True
            try:
                results["session_state"] = str(
                    tool_context.session.state)[:500]
            except Exception as e:
                results["session_state"] = str(e)

        # Check invocation_context
        if hasattr(tool_context, 'invocation_context'):
            results["has_invocation_context"] = True
            ic = tool_context.invocation_context
            if hasattr(ic, 'session') and ic.session:
                try:
                    results["ic_session_state"] = str(ic.session.state)[:500]
                except:
                    pass

        # PRINT to console for debugging
        print("\n" + "=" * 40)
        print("TOOL SEES STATE:")
        print(json.dumps(results, indent=2, default=str))
        print("=" * 40 + "\n")

        return json.dumps(results, indent=2, default=str)

    return [FunctionTool(func=read_producer_data_tool)]


def create_consumer_agent(api_key: str) -> Agent:
    """Agent that reads data from blackboard via tool."""
    tools = create_consumer_tools()

    return Agent(
        name="ConsumerAgent",
        model=Gemini(model="gemini-2.5-pro", api_key=api_key),
        tools=tools,
        output_key="temp:consumer_output",
        instruction="""You MUST call the read_producer_data_tool first.

STEP 1: Call read_producer_data_tool() - THIS IS MANDATORY

STEP 2: After getting the tool result, output JSON with what you found.

Do NOT make up data. Only report what the tool returns.""",
    )


async def main():
    print("=" * 60)
    print("ADK BLACKBOARD STATE TEST")
    print("=" * 60)

    # Create sequential pipeline
    workflow = SequentialAgent(
        name="TestWorkflow",
        sub_agents=[
            create_producer_agent(API_KEY),
            create_consumer_agent(API_KEY),
        ],
    )

    runner = InMemoryRunner(agent=workflow, app_name="BlackboardTest")

    print("\nRunning pipeline...")
    events = await runner.run_debug("Test the blackboard state mechanism")

    for event in events:
        if event.author and event.content:
            print(f"\n[{event.author}]")
            for part in event.content.parts:
                if part.text:
                    print(part.text[:500])

    print("\n" + "=" * 60)
    print("EVENTS SUMMARY")
    print("=" * 60)
    for event in events:
        if event.author:
            print(
                f"  - {event.author}: {len(event.content.parts) if event.content else 0} parts")


if __name__ == "__main__":
    asyncio.run(main())
