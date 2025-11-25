#!/usr/bin/env python3
"""
Test script to investigate ADK event-based metadata extraction.

This script tests whether we can extract agent execution metadata
from the event stream returned by runner.run_debug().
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from google.genai import Client
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk import events

# Load environment
load_dotenv()
api_key = os.environ.get("GOOGLE_API_KEY")


async def test_event_metadata():
    """Test what metadata is available in events."""

    # Create a simple test agent
    test_agent = Agent(
        name="TestAgent",
        model="gemini-2.0-flash-exp",
        instruction="You are a test agent. When given a question, respond with 'Test response: [question]'",
    )

    # Run the agent
    runner = InMemoryRunner(agent=test_agent, app_name="MetadataTest")
    event_list = await runner.run_debug("What is 2+2?")

    print("\n" + "=" * 80)
    print("EVENT STREAM ANALYSIS")
    print("=" * 80)

    for i, event in enumerate(event_list):
        print(f"\n--- Event {i} ---")
        print(f"Author: {event.author}")
        print(f"ID: {event.id}")
        print(f"Timestamp: {event.timestamp}")
        print(f"Invocation ID: {event.invocation_id}")

        # Check for usage metadata
        if hasattr(event, 'usage_metadata') and event.usage_metadata:
            print(f"Usage Metadata: {event.usage_metadata}")
            print(
                f"  - Prompt Tokens: {event.usage_metadata.prompt_token_count}")
            print(
                f"  - Candidates Tokens: {event.usage_metadata.candidates_token_count}")
            print(
                f"  - Total Tokens: {event.usage_metadata.total_token_count}")

        # Check for model version
        if hasattr(event, 'model_version') and event.model_version:
            print(f"Model Version: {event.model_version}")

        # Check for custom metadata
        if hasattr(event, 'custom_metadata') and event.custom_metadata:
            print(f"Custom Metadata: {event.custom_metadata}")

        # Check content
        if event.content:
            print(f"Content parts: {len(event.content.parts)}")
            for j, part in enumerate(event.content.parts):
                if part.text:
                    preview = part.text[:100].replace('\n', ' ')
                    print(f"  Part {j}: {preview}...")

    # Test with SequentialAgent
    print("\n" + "=" * 80)
    print("SEQUENTIAL AGENT TEST")
    print("=" * 80)

    from google.adk.agents import SequentialAgent

    agent1 = Agent(
        name="Agent1",
        model="gemini-2.0-flash-exp",
        instruction="You are Agent 1. Respond with 'Agent 1 processed: [input]'",
        output_key="agent1_output"
    )

    agent2 = Agent(
        name="Agent2",
        model="gemini-2.0-flash-exp",
        instruction="You are Agent 2. Take {agent1_output} and respond with 'Agent 2 processed: [agent1 output]'",
    )

    workflow = SequentialAgent(
        name="TestWorkflow",
        sub_agents=[agent1, agent2]
    )

    runner2 = InMemoryRunner(agent=workflow, app_name="SequentialTest")
    event_list2 = await runner2.run_debug("Test input")

    print(f"\nTotal events: {len(event_list2)}")

    # Track which agent generated which event
    agent_events = {}
    for event in event_list2:
        author = event.author
        if author not in agent_events:
            agent_events[author] = []
        agent_events[author].append({
            'id': event.id,
            'timestamp': event.timestamp,
            'invocation_id': event.invocation_id,
            'has_usage': bool(event.usage_metadata) if hasattr(event, 'usage_metadata') else False,
            'model_version': event.model_version if hasattr(event, 'model_version') else None,
        })

    print("\nEvents grouped by author:")
    for author, author_events in agent_events.items():
        print(f"\n{author}: {len(author_events)} events")
        for evt_info in author_events:
            print(
                f"  - ID: {evt_info['id'][:8]}... Time: {evt_info['timestamp']:.2f} Usage: {evt_info['has_usage']} Model: {evt_info['model_version']}")


if __name__ == "__main__":
    asyncio.run(test_event_metadata())
