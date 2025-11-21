#!/usr/bin/env python3
"""
AGENT-AS-TOOL LOOP DEMO
4 images -> descriptions -> story

Architecture:
- Tool: describe_image_with_agent(image_path)
    * Reads ONE image from disk.
    * Calls Gemini vision directly (multimodal).
    * Returns a short description + LABEL line.

- ImageLoopAgent (orchestrator with loop pattern):
    * Sees 4 image paths (one per line) in the user message.
    * For each path (in order), calls describe_image_with_agent(image_path=...).
    * Aggregates results into a formatted block.
    * Stores that block in session.state["temp:all_image_descriptions"].

- StoryAgent (sequential follow-up):
    * Reads {temp:all_image_descriptions}.
    * Writes a short story (4–6 sentences) that uses all four images.
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from google import genai
from google.genai import types

from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-2.5-pro"

if not GOOGLE_API_KEY:
    print("❌ GOOGLE_API_KEY not found! Check your .env.")
    raise SystemExit(1)

# Go up from scripts/ to project root
PROJECT_ROOT = Path(__file__).parent.parent
genai_client = genai.Client(api_key=GOOGLE_API_KEY)


# ---------------------------------------------------------------------
# Tool: describe_image_with_agent(image_path)
# ---------------------------------------------------------------------
async def describe_image_with_agent(image_path: str, tool_context: ToolContext) -> str:
    """
    Reads an image from disk and runs a single multimodal Gemini call
    to describe it.

    Args:
        image_path: Path to the image, relative to PROJECT_ROOT.

    Returns:
        A short description + LABEL line, as a single text block.
        Example:
            "A golden retriever puppy sits in green grass.\nLABEL: golden retriever puppy"
    """
    full_path = PROJECT_ROOT / image_path
    if not full_path.exists():
        return f"ERROR: image not found at {image_path}"

    image_bytes = full_path.read_bytes()
    mime_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    # Use Part(text=...) for text; from_bytes for image
    response = genai_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part(
                text=(
                    "Describe this image in 1–2 short sentences. "
                    "Then on a new line write: LABEL: <simple_label> "
                    "where <simple_label> is 1–3 words summarizing the main subject."
                )
            ),
            image_part,
        ],
    )

    text = (response.text or "").strip()
    return text


describe_image_tool = FunctionTool(func=describe_image_with_agent)


# ---------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------

image_loop_agent = Agent(
    name="ImageLoopAgent",
    model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
    tools=[describe_image_tool],
    instruction=(
        "You are an orchestrator agent.\n"
        "The user message contains EXACTLY four image paths on disk, one per line.\n\n"
        "Your job is to process them IN ORDER using the tool "
        "`describe_image_with_agent`.\n\n"
        "Steps:\n"
        "1) Parse the user message to extract the four image paths, in order.\n"
        "2) For each path (first line is Image 1, second is Image 2, etc.):\n"
        "   - Call describe_image_with_agent(image_path=<that exact path string>).\n"
        "   - Capture the tool's text result (description + LABEL line).\n\n"
        "3) After you have processed ALL FOUR paths, construct a single response "
        "in this EXACT format:\n\n"
        "Image 1:\n"
        "<description from the tool for the first path>\n"
        "LABEL: <label for the first image>\n\n"
        "Image 2:\n"
        "<description for the second path>\n"
        "LABEL: <label>\n\n"
        "Image 3:\n"
        "<description for the third path>\n"
        "LABEL: <label>\n\n"
        "Image 4:\n"
        "<description for the fourth path>\n"
        "LABEL: <label>\n\n"
        "Do not add any extra commentary before or after this block.\n"
        "Do not make up details; rely on the tool outputs."
    ),
    output_key="temp:all_image_descriptions",
)

story_agent = Agent(
    name="StoryAgent",
    model=Gemini(model=GEMINI_MODEL, api_key=GOOGLE_API_KEY),
    instruction=(
        "You are a concise storyteller.\n"
        "You are given descriptions of four images from another agent:\n"
        "{temp:all_image_descriptions?}\n\n"
        "If there are no descriptions available, respond with:\n"
        "\"No descriptions available; cannot write a story.\"\n\n"
        "Otherwise, write a short story (4–6 short sentences) that weaves together\n"
        "the scenes implied by the four images.\n"
        "The story should:\n"
        "- Use information from ALL FOUR images.\n"
        "- Be concrete and minimal.\n"
        "Just output the story itself; do not explain your reasoning."
    ),
)

workflow = SequentialAgent(
    name="ImageLoopToStoryWorkflow",
    sub_agents=[image_loop_agent, story_agent],
)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
async def main() -> None:
    print("=" * 80)
    print("AGENT-AS-TOOL LOOP DEMO: 4 IMAGES → DESCRIPTIONS → STORY")
    print("=" * 80)

    images_dir_rel = "data/test/images"
    images_dir = PROJECT_ROOT / images_dir_rel

    if not images_dir.exists():
        print(f"❌ Directory not found: {images_dir_rel}")
        raise SystemExit(1)

    image_files = sorted(
        [p for p in images_dir.iterdir() if p.suffix.lower() in {
            ".jpg", ".jpeg", ".png"}]
    )[:4]

    if len(image_files) < 4:
        print(
            f"❌ Need at least 4 images in {images_dir_rel}, found {len(image_files)}")
        raise SystemExit(1)

    rel_paths = [str(p.relative_to(PROJECT_ROOT)) for p in image_files]
    paths_block = "\n".join(rel_paths)

    runner = InMemoryRunner(
        agent=workflow,
        app_name="AgentLoopImageStoryDemo",
    )

    user_id = "toy_user"
    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
    )

    user_message = types.Content(
        role="user",
        parts=[
            types.Part(
                text=(
                    "Here are exactly four image paths on disk, one per line:\n"
                    f"{paths_block}\n\n"
                    "Follow your agent instructions to process them."
                )
            )
        ],
    )

    print("\n🚀 Running agent-as-tool loop workflow on these images:\n")
    for rp in rel_paths:
        print("  -", rp)
    print("\n" + "-" * 80 + "\n")

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        if (
            event.author in (image_loop_agent.name, story_agent.name)
            and event.content
            and event.content.parts
            and event.content.parts[0].text is not None
        ):
            print(f"{event.author} >")
            print(event.content.parts[0].text.strip())
            print("\n" + "-" * 80 + "\n")

    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
