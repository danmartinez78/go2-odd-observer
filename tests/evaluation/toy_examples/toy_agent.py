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


def get_weather(city: str) -> str:
    """Get weather information for a city."""
    # Mock weather data
    return f"The weather in {city} is sunny and 72°F."


def calculate_age(birth_year: int) -> int:
    """Calculate age from birth year."""
    current_year = 2025
    return current_year - birth_year


def list_cities() -> list[str]:
    """List available cities for weather."""
    return ["San Francisco", "New York", "London", "Tokyo"]


# Export simple agent for ADK evaluation
agent = Agent(
    name="ToyAgent",
    model=Gemini(model="gemini-2.0-flash-lite", api_key=api_key),
    tools=[greet_user, get_weather, calculate_age, list_cities],
    instruction="""You are a helpful assistant with several capabilities:
    - Greet users by name
    - Provide weather information for cities
    - Calculate ages from birth years
    - List available cities
    
    Use the appropriate tools to answer user questions accurately.""",
)
