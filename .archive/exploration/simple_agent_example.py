#!/usr/bin/env python3
"""
Simple example agent using Google ADK to test data access and validation.
This demonstrates how to pass file data into ADK agents using FunctionTools.
"""

from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.adk.models.google_llm import Gemini
from google.adk.agents import Agent
from google.genai import types
import os
import sys
import json
import csv
import base64
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ==========================================w==================================
# TOOL IMPLEMENTATIONS
# ============================================================================

def read_csv_file(file_path: str) -> Dict[str, Any]:
    """Read and parse a CSV file, return summary."""
    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        rows = []
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        return {
            "success": True,
            "file": file_path,
            "row_count": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "sample_row": rows[0] if rows else None,
            "all_rows": rows
        }
    except Exception as e:
        return {"error": f"Error reading CSV: {str(e)}"}


def read_json_file(file_path: str) -> Dict[str, Any]:
    """Read and parse a JSON file, return summary."""
    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        with open(path, 'r') as f:
            data = json.load(f)

        return {
            "success": True,
            "file": file_path,
            "type": type(data).__name__,
            "keys": list(data.keys()) if isinstance(data, dict) else "N/A",
            "content": data  # Include full content for analysis
        }
    except Exception as e:
        return {"error": f"Error reading JSON: {str(e)}"}


def read_image_file(file_path: str) -> Dict[str, Any]:
    """Read image file and return as Gemini-compatible image data (raw bytes)."""
    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        with open(path, 'rb') as f:
            image_bytes = f.read()

        mime_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"

        return {
            "success": True,
            "file": file_path,
            "size_bytes": path.stat().st_size,
            "format": path.suffix.lower(),
            "mime_type": mime_type,
            "image_bytes": image_bytes,  # Raw bytes that Gemini can process
            "encoding": "raw_bytes",
            "description": f"Image file: {path.name} ({len(image_bytes)} bytes)"
        }
    except Exception as e:
        return {"error": f"Error reading image: {str(e)}"}


def read_image_file_base64(file_path: str) -> Dict[str, Any]:
    """Read image file and return as base64-encoded data."""
    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        with open(path, 'rb') as f:
            image_bytes = f.read()

        mime_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"

        # Encode to base64
        base64_data = base64.b64encode(image_bytes).decode('utf-8')

        return {
            "success": True,
            "file": file_path,
            "size_bytes": path.stat().st_size,
            "format": path.suffix.lower(),
            "mime_type": mime_type,
            "image_base64": base64_data,  # Base64-encoded data
            "encoding": "base64",
            "description": f"Image file: {path.name} ({len(image_bytes)} bytes)"
        }
    except Exception as e:
        return {"error": f"Error reading image: {str(e)}"}


def generate_validation_report(data_summary: str) -> Dict[str, Any]:
    """Generate a validation report for the data."""
    return {
        "validation_complete": True,
        "summary": data_summary,
        "status": "success",
        "timestamp": str(Path("/workspaces/go2-odd-observer/test_data").stat().st_mtime)
    }


# ============================================================================
# CREATE FUNCTION TOOLS FOR ADK
# ============================================================================

csv_tool = FunctionTool(func=read_csv_file)
json_tool = FunctionTool(func=read_json_file)
read_image_tool = FunctionTool(func=read_image_file)
read_image_tool_base64 = FunctionTool(func=read_image_file_base64)
report_tool = FunctionTool(func=generate_validation_report)


# ============================================================================
# CREATE ADK AGENT
# ============================================================================

def create_validation_agent():
    """Create an ADK agent for ODD/COD analysis."""

    # Initialize Gemini model
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY not found in environment!")
        print("   Please set: export GOOGLE_API_KEY='your-key-here'")
        sys.exit(1)

    model = Gemini(
        api_key=GOOGLE_API_KEY,
        model="gemini-2.0-flash-lite"
    )

    # Create agent with both raw bytes and base64 image tools
    agent = Agent(
        name="ImageComparisonAgent",
        description="Agent for comparing raw bytes vs base64 image encoding",
        model=model,
        tools=[read_image_tool, read_image_tool_base64],
        instruction="""You are a vision analysis expert testing image data formats.

YOUR TASK:
1. For EACH image file listed below, read it with BOTH tools:
   - /workspaces/go2-odd-observer/data/processed/runs/sim_run_test/cam_sim_run_test_w006.png
   - /workspaces/go2-odd-observer/data/processed/runs/sim_run_test/bev_occupancy_sim_run_test_w006.png

2. After getting responses, compare the metadata:
   - File size from read_image_file (raw bytes)
   - File size from read_image_file_base64 
   - MIME types (should be identical)
   - Encoding field shows "raw_bytes" vs "base64"

3. Create a DATA VALIDATION TABLE with:
   - Filename
   - File size (bytes)
   - MIME type
   - Raw bytes encoding status
   - Base64 encoding status
   - Data validation: PASS or FAIL (do sizes match?)

4. Analyze the images using the raw_bytes version for visual analysis:
   - Estimated dimensions
   - Primary colors
   - Brightness level
   - Content type
   - Key features observed

5. Create a final report with validation results and image analysis."""
    )

    return agent


def run_validation():
    """Run the image analysis agent."""
    print("=" * 80)
    print("ADK SIMPLE AGENT - IMAGE FORMAT COMPARISON TEST")
    print("=" * 80)

    try:
        import asyncio

        agent = create_validation_agent()
        runner = InMemoryRunner(app_name="ImageComparison", agent=agent)

        print("\n✓ Agent created successfully")
        print("  - Model: gemini-2.0-flash-lite")
        print("  - Tools: 2 (Raw bytes + Base64 encoding)")
        print("  - Task: Compare both image formats and analyze properties")
        print("  - Dataset: /workspaces/go2-odd-observer/data/processed/runs/sim_run_test/")
        print("\n✓ Running image comparison agent...\n")

        # Run the agent asynchronously
        result = asyncio.run(runner.run_debug(
            user_messages="Compare the raw bytes and base64 versions of the images. Verify they represent the same data. Analyze the images for size, colors, brightness, and key features."
        ))

        print("\n" + "=" * 80)
        print("AGENT EXECUTION COMPLETE")
        print("=" * 80)
        print(f"\nResult:\n{result}")

        return result

    except Exception as e:
        print(f"\n❌ Error running agent: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    run_validation()
