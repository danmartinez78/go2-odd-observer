"""
Minimal toy agent for learning ADK evaluation.
Simple greeting agent with one tool.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini

# Load environment variables
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY must be set in .env file")


def greet_user(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}!"


# Export simple agent for ADK evaluation
agent = Agent(
    name="GreetingAgent",
    model=Gemini(model="gemini-2.0-flash-lite", api_key=api_key),
    tools=[greet_user],
    instruction="You are a friendly greeter. When asked to greet someone, use the greet_user tool with their name.",
)
