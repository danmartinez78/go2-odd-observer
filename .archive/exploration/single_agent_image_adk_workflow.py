#!/usr/bin/env python3
"""
Direct image → Gemini via ADK (no tools / artifacts).

Reads a local image, builds a multimodal user Content (text + image),
creates a session, and sends it to an Agent using InMemoryRunner.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner

from google.genai import types  # Content, Part

# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.5-pro"

if not GOOGLE_API_KEY:
    print("❌ GOOGLE_API_KEY not found! Check your .env.")
    raise SystemExit(1)

PROJECT_ROOT = Path(__file__).parent


async def main() -> None:
    print("=" * 80)
    print("DIRECT IMAGE → GEMINI (run_async + Content)")
    print("=" * 80)

    # -----------------------------------------------------------------
    # 1. Load image bytes from disk
    # -----------------------------------------------------------------
    image_rel_path = "data/test_images/4.jpg"
    image_path = PROJECT_ROOT / image_rel_path

    if not image_path.exists():
        print(f"❌ Image not found at {image_rel_path}")
        raise SystemExit(1)

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/jpeg",  # adjust if PNG
    )

    # -----------------------------------------------------------------
    # 2. Define a simple image-analysis agent (no tools)
    # -----------------------------------------------------------------
    analysis_agent = Agent(
        name="ImageAnalysisAgent",
        model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
        instruction=(
            "You are an image classification expert.\n"
            "You will receive an image and a short text instruction.\n"
            "Classify the image accordingly and provide a detailed description.\n"
            "Be accurate and concise in your analysis.\n"
        ),
    )

    runner = InMemoryRunner(agent=analysis_agent, app_name="DirectImageDemo")

    # -----------------------------------------------------------------
    # 3. Create a session explicitly (fixes 'Session not found')
    # -----------------------------------------------------------------
    user_id = "debug_user"
    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
    )

    # -----------------------------------------------------------------
    # 4. Build a multimodal user message (text + image)
    # -----------------------------------------------------------------
    user_message = types.Content(
        role="user",
        parts=[
            types.Part.from_text(
                text="Classify this image."
            ),
            image_part,
        ],
    )

    print(f"\n🚀 Processing: {image_rel_path}\n")

    # -----------------------------------------------------------------
    # 5. Run the agent and print the model's response
    # -----------------------------------------------------------------
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        if (
            event.author == analysis_agent.name
            and event.content
            and event.content.parts
            and event.content.parts[0].text is not None
        ):
            print(f"{event.author} >", event.content.parts[0].text.strip())

    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
