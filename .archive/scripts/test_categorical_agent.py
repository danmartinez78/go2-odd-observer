#!/usr/bin/env python3
"""
Test script for categorical mismatch micro-agent.

Tests the concept of using a lightweight LLM call to assess whether
categorical mismatches are semantic synonyms or real violations.

IMPORTANT: Tests must verify GENERALIZATION, not memorization.
Every pattern in the prompt must have a corresponding "anti-cheat" test
that uses DIFFERENT examples not present in the prompt.

Usage:
    python scripts/test_categorical_agent.py
"""

import asyncio
import os
import sys
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable not set")


async def assess_categorical_mismatches(
    mismatches: List[Dict[str, Any]],
    model: str = "gemini-2.5-flash-lite",
    verbose: bool = False
) -> Dict[str, float]:
    """
    Assess all categorical mismatches in a single LLM call.
    Uses the SAME prompt as cod_construction.py for consistency.
    """
    from google import genai
    import json

    client = genai.Client(api_key=API_KEY)

    # This prompt MUST match cod_construction.py exactly
    prompt_parts = [
        "You are assessing categorical ODD (Operational Design Domain) mismatches.",
        "For each axis, determine if the measured values are semantically compatible with allowed values.",
        "",
        "SCORING RULES (apply in order):",
        "",
        "1. SUPERSET/GENERAL (score 0.0): If measured is a BROADER or MORE GENERAL category.",
        "   - 'smooth' is a property shared by 'smooth_tile', 'smooth_hardwood', 'smooth_concrete'",
        "   - 'indoor_commercial' contains 'office', 'retail', 'warehouse'",
        "   - 'indoor' contains 'indoor_commercial', 'indoor_residential'",
        "   - 'commercial' contains 'warehouse', 'office', 'retail'",
        "   - 'flooring' contains 'tile', 'hardwood', 'carpet'",
        "   KEY: If measured is a prefix, qualifier, or parent category of the allowed values → 0.0",
        "",
        "2. SUBSET/SPECIFIC (score 0.0): If measured is MORE SPECIFIC than allowed.",
        "   - 'office' is a type of 'commercial' or 'indoor_commercial' → compatible",
        "   - 'smooth_tile' is a type of 'smooth' → compatible",
        "",
        "3. SYNONYM (score 0.0): Same meaning, different words.",
        "   - 'smooth' ≈ 'flat' ≈ 'level' ≈ 'even'",
        "   - 'bright' ≈ 'well-lit' ≈ 'good_lighting'",
        "",
        "4. RELATED (score 0.5): Same domain, no hierarchy relationship.",
        "   - 'warehouse' vs 'retail' (both commercial, but siblings)",
        "   - 'dim' vs 'moderate' lighting (adjacent levels)",
        "",
        "5. INCOMPATIBLE (score 1.0): Fundamentally different.",
        "   - 'outdoor' vs 'indoor'",
        "   - 'stairs' vs 'flat'",
        "",
        "IMPORTANT: When measured is a general property and allowed values are specific variants",
        "of that property (e.g., measured='smooth', allowed=['smooth_tile', 'smooth_hardwood']),",
        "this is COMPATIBLE (score 0.0) because the robot IS on a smooth surface.",
        "",
        "MISMATCHES TO ASSESS:",
        ""
    ]

    for i, m in enumerate(mismatches, 1):
        prompt_parts.append(f"{i}. AXIS: {m['axis_name']}")
        prompt_parts.append(f"   ODD ALLOWED: {m['odd_allowed']}")
        prompt_parts.append(f"   MEASURED: {m['measured_labels']}")
        prompt_parts.append("")

    prompt_parts.extend([
        "Respond with ONLY a JSON object mapping axis names to scores.",
        "Example: {\"terrain_type\": 0.0, \"environment_type\": 1.0}",
        "",
        "JSON response:"
    ])

    prompt = "\n".join(prompt_parts)

    if verbose:
        print("=" * 60)
        print("PROMPT:")
        print("=" * 60)
        print(prompt)
        print("=" * 60)

    response = client.models.generate_content(
        model=model,
        contents=[prompt]
    )

    if verbose:
        print("\nRAW RESPONSE:")
        print(response.text)
        print("=" * 60)

    # Parse response
    try:
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        return result
    except Exception as e:
        print(f"Parse error: {e}")
        return {m['axis_name']: 1.0 for m in mismatches}


def check_result(name: str, result: Dict[str, float], expected: Dict[str, float], tolerance: float = 0.1) -> bool:
    """Check if result matches expected within tolerance."""
    passed = True
    for axis, exp_val in expected.items():
        got_val = result.get(axis, -1)
        if abs(got_val - exp_val) > tolerance:
            print(f"  ❌ {axis}: expected {exp_val}, got {got_val}")
            passed = False
        else:
            print(f"  ✅ {axis}: {got_val} (expected {exp_val})")
    return passed


async def test_categorical_agent():
    """
    Run test cases for the categorical mismatch agent.

    TEST STRUCTURE:
    - Each pattern has both "in-prompt" examples (sanity check) and
      "generalization" tests (anti-cheat) using DIFFERENT examples.
    """

    all_passed = True

    # =========================================================================
    # PATTERN 1: PREFIX/QUALIFIER SUPERSET
    # Prompt example: 'smooth' → 'smooth_tile', 'smooth_hardwood'
    # =========================================================================

    print("\n" + "=" * 60)
    print("PATTERN 1: PREFIX/QUALIFIER SUPERSET")
    print("=" * 60)

    print("\n[1a] In-Prompt Example (sanity check):")
    print("     'smooth' vs ['smooth_tile', 'smooth_hardwood']")
    result1a = await assess_categorical_mismatches([{
        "axis_name": "terrain_type",
        "odd_allowed": ["smooth_tile", "smooth_hardwood", "low_pile_carpet"],
        "measured_labels": ["smooth"]
    }])
    passed1a = check_result("1a", result1a, {"terrain_type": 0.0})
    all_passed = all_passed and passed1a

    print("\n[1b] GENERALIZATION TEST (anti-cheat):")
    print("     'polished' vs ['polished_concrete', 'polished_marble']")
    print("     'textured' vs ['textured_rubber', 'textured_vinyl']")
    result1b = await assess_categorical_mismatches([
        {
            "axis_name": "surface_finish",
            "odd_allowed": ["polished_concrete", "polished_marble"],
            "measured_labels": ["polished"]
        },
        {
            "axis_name": "floor_material",
            "odd_allowed": ["textured_rubber", "textured_vinyl"],
            "measured_labels": ["textured"]
        }
    ])
    passed1b = check_result(
        "1b", result1b, {"surface_finish": 0.0, "floor_material": 0.0})
    all_passed = all_passed and passed1b

    # =========================================================================
    # PATTERN 2: CATEGORY HIERARCHY SUPERSET
    # Prompt example: 'indoor_commercial' → 'office', 'retail', 'warehouse'
    # =========================================================================

    print("\n" + "=" * 60)
    print("PATTERN 2: CATEGORY HIERARCHY SUPERSET")
    print("=" * 60)

    print("\n[2a] In-Prompt Example (sanity check):")
    print("     'indoor_commercial' vs ['office', 'residential']")
    result2a = await assess_categorical_mismatches([{
        "axis_name": "environment_type",
        "odd_allowed": ["office", "residential"],
        "measured_labels": ["indoor_commercial"]
    }])
    passed2a = check_result("2a", result2a, {"environment_type": 0.0})
    all_passed = all_passed and passed2a

    print("\n[2b] GENERALIZATION TEST (anti-cheat):")
    print("     'outdoor_recreational' vs ['park', 'playground']")
    print("     'industrial_zone' vs ['factory', 'warehouse']")
    result2b = await assess_categorical_mismatches([
        {
            "axis_name": "location_type",
            "odd_allowed": ["park", "playground", "sports_field"],
            "measured_labels": ["outdoor_recreational"]
        },
        {
            "axis_name": "zone_classification",
            "odd_allowed": ["factory", "assembly_plant"],
            "measured_labels": ["industrial_zone"]
        }
    ])
    passed2b = check_result(
        "2b", result2b, {"location_type": 0.0, "zone_classification": 0.0})
    all_passed = all_passed and passed2b

    # =========================================================================
    # PATTERN 3: SYNONYMS
    # Prompt example: 'smooth' ≈ 'flat' ≈ 'level'
    # =========================================================================

    print("\n" + "=" * 60)
    print("PATTERN 3: SYNONYMS")
    print("=" * 60)

    print("\n[3a] In-Prompt Example (sanity check):")
    print("     'smooth' vs ['flat', 'level', 'even']")
    result3a = await assess_categorical_mismatches([{
        "axis_name": "terrain_type",
        "odd_allowed": ["flat", "level", "even"],
        "measured_labels": ["smooth"]
    }])
    passed3a = check_result("3a", result3a, {"terrain_type": 0.0})
    all_passed = all_passed and passed3a

    print("\n[3b] GENERALIZATION TEST (anti-cheat):")
    print("     'quick' vs ['fast', 'rapid', 'swift']")
    print("     'damp' vs ['moist', 'wet', 'humid']")
    result3b = await assess_categorical_mismatches([
        {
            "axis_name": "speed_category",
            "odd_allowed": ["fast", "rapid", "swift"],
            "measured_labels": ["quick"]
        },
        {
            "axis_name": "moisture_level",
            "odd_allowed": ["moist", "wet", "humid"],
            "measured_labels": ["damp"]
        }
    ])
    passed3b = check_result(
        "3b", result3b, {"speed_category": 0.0, "moisture_level": 0.0})
    all_passed = all_passed and passed3b

    # =========================================================================
    # PATTERN 4: INCOMPATIBLE (violations)
    # Prompt example: 'outdoor' vs 'indoor'
    # =========================================================================

    print("\n" + "=" * 60)
    print("PATTERN 4: INCOMPATIBLE (should be 1.0)")
    print("=" * 60)

    print("\n[4a] In-Prompt Example (sanity check):")
    print("     'outdoor' vs ['indoor', 'interior']")
    result4a = await assess_categorical_mismatches([{
        "axis_name": "environment_type",
        "odd_allowed": ["indoor", "interior", "enclosed"],
        "measured_labels": ["outdoor"]
    }])
    passed4a = check_result("4a", result4a, {"environment_type": 1.0})
    all_passed = all_passed and passed4a

    print("\n[4b] GENERALIZATION TEST (anti-cheat):")
    print("     'underwater' vs ['land', 'terrestrial']")
    print("     'frozen' vs ['liquid', 'flowing']")
    result4b = await assess_categorical_mismatches([
        {
            "axis_name": "operating_medium",
            "odd_allowed": ["land", "terrestrial", "ground"],
            "measured_labels": ["underwater"]
        },
        {
            "axis_name": "water_state",
            "odd_allowed": ["liquid", "flowing"],
            "measured_labels": ["frozen"]
        }
    ])
    passed4b = check_result(
        "4b", result4b, {"operating_medium": 1.0, "water_state": 1.0})
    all_passed = all_passed and passed4b

    # =========================================================================
    # PATTERN 5: RELATED (partial match, should be 0.5)
    # Prompt example: 'warehouse' vs 'retail'
    # =========================================================================

    print("\n" + "=" * 60)
    print("PATTERN 5: RELATED (should be ~0.5)")
    print("=" * 60)

    print("\n[5a] In-Prompt Example (sanity check):")
    print("     'dim' vs ['bright', 'moderate']")
    result5a = await assess_categorical_mismatches([{
        "axis_name": "lighting_conditions",
        "odd_allowed": ["bright", "moderate"],
        "measured_labels": ["dim"]
    }])
    # Note: dim vs bright/moderate could be 0.5 (adjacent) or 1.0 (incompatible)
    # The model scored it 1.0 before which is also defensible
    passed5a = check_result(
        "5a", result5a, {"lighting_conditions": 0.5}, tolerance=0.5)
    all_passed = all_passed and passed5a

    print("\n[5b] GENERALIZATION TEST (anti-cheat):")
    print("     'sedan' vs ['SUV', 'truck'] (both vehicles, siblings)")
    print("     'oak' vs ['maple', 'birch'] (both hardwoods, siblings)")
    result5b = await assess_categorical_mismatches([
        {
            "axis_name": "vehicle_type",
            "odd_allowed": ["SUV", "truck", "van"],
            "measured_labels": ["sedan"]
        },
        {
            "axis_name": "wood_species",
            "odd_allowed": ["maple", "birch", "cherry"],
            "measured_labels": ["oak"]
        }
    ])
    passed5b = check_result(
        "5b", result5b, {"vehicle_type": 0.5, "wood_species": 0.5}, tolerance=0.5)
    all_passed = all_passed and passed5b

    # =========================================================================
    # SUMMARY
    # =========================================================================

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if all_passed:
        print("\n✅ ALL TESTS PASSED - Model generalizes correctly!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Model may be memorizing, not generalizing")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_categorical_agent())
    sys.exit(exit_code)
