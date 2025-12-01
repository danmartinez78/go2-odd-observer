#!/usr/bin/env python3
"""
Toy example to test ADK Artifacts pattern with gemini-2.5-flash-lite.
"""
import asyncio
import os
import json
import random

from dotenv import load_dotenv
import google.genai.types as types
from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL = "gemini-2.5-flash"


# =============================================================================
# PRODUCER AGENT
# =============================================================================
def create_producer_tools():
    from google.adk.tools.tool_context import ToolContext

    async def save_measurements_tool(
        temperature: float,
        humidity: float,
        tool_context: ToolContext
    ) -> str:
        """Save measurement data as a JSON artifact."""
        data = {
            "measurements": {
                "temperature": temperature,
                "humidity": humidity
            }
        }

        json_bytes = json.dumps(data).encode('utf-8')
        artifact = types.Part.from_bytes(
            data=json_bytes, mime_type="application/json")

        version = await tool_context.save_artifact(
            filename="sensor_measurements.json",
            artifact=artifact
        )
        print(f"\n[PRODUCER TOOL] Saved artifact v{version}: {data}")
        return json.dumps({"status": "saved", "version": version})

    return [FunctionTool(func=save_measurements_tool)]


def create_producer_agent(api_key: str) -> Agent:
    tools = create_producer_tools()

    # Random values - Consumer won't know these
    temp = round(random.uniform(15.0, 35.0), 1)
    humid = round(random.uniform(30.0, 80.0), 1)
    print(f"[SECRET VALUES] temp={temp}, humid={humid}")

    return Agent(
        name="ProducerAgent",
        model=Gemini(model=MODEL, api_key=api_key),
        tools=tools,
        instruction=f"""You are an autonomous sensor agent. Do NOT ask questions.

IMMEDIATELY call save_measurements_tool with these EXACT values:
- temperature: {temp}
- humidity: {humid}

After the tool call succeeds, output ONLY: {{"status": "saved"}}

Do not ask for clarification. Execute the tool call now.""",
    )


# =============================================================================
# CONSUMER AGENT
# =============================================================================
def create_consumer_tools():
    from google.adk.tools.tool_context import ToolContext

    async def load_measurements_tool(tool_context: ToolContext) -> str:
        """Load measurement data from artifact."""
        artifact = await tool_context.load_artifact(filename="sensor_measurements.json")

        if artifact and artifact.inline_data:
            data = json.loads(artifact.inline_data.data.decode('utf-8'))
            print(f"\n[CONSUMER TOOL] Loaded artifact: {data}")
            return json.dumps({"status": "loaded", "data": data})
        else:
            return json.dumps({"status": "not_found"})

    async def compute_analysis_tool(temperature: float, humidity: float) -> str:
        """Compute analysis from measurements."""
        comfort = round((temperature + (100 - humidity)) / 2, 1)
        print(f"\n[COMPUTE TOOL] comfort={comfort}")
        return json.dumps({"comfort_index": comfort})

    return [
        FunctionTool(func=load_measurements_tool),
        FunctionTool(func=compute_analysis_tool)
    ]


def create_consumer_agent(api_key: str) -> Agent:
    tools = create_consumer_tools()

    return Agent(
        name="ConsumerAgent",
        model=Gemini(model=MODEL, api_key=api_key),
        tools=tools,
        instruction="""You must load sensor data from artifact and analyze it.

STEP 1: Call load_measurements_tool() to get data.
STEP 2: Call compute_analysis_tool(temperature, humidity) with loaded values.
STEP 3: Output the analysis result as JSON.""",
    )


# =============================================================================
# MAIN
# =============================================================================
async def main():
    print("=" * 60)
    print(f"ADK ARTIFACTS TEST - {MODEL}")
    print("=" * 60)

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    workflow = SequentialAgent(
        name="ArtifactWorkflow",
        sub_agents=[
            create_producer_agent(API_KEY),
            create_consumer_agent(API_KEY),
        ],
    )

    runner = Runner(
        agent=workflow,
        app_name="ArtifactTest",
        session_service=session_service,
        artifact_service=artifact_service,
    )

    user_id = "test_user"
    session = await session_service.create_session(app_name="ArtifactTest", user_id=user_id)
    print(f"Session: {session.id}\n")

    tool_calls = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(
            role="user", parts=[types.Part(text="Process sensor data")])
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    tool_calls.append(
                        f"{event.author}: {part.function_call.name}")
                    print(
                        f"[CALL] {event.author} -> {part.function_call.name}")
                if hasattr(part, 'text') and part.text:
                    print(f"[{event.author}] {part.text}")

    print("\n" + "=" * 60)
    print(f"Tool calls: {tool_calls}")

    artifacts = await artifact_service.list_artifact_keys(
        app_name="ArtifactTest", user_id=user_id, session_id=session.id
    )
    print(f"Artifacts: {artifacts}")


if __name__ == "__main__":
    asyncio.run(main())
