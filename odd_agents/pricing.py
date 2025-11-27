"""
Gemini API pricing calculator.

Prices are per 1,000,000 tokens (paid tier).
Source: https://ai.google.dev/gemini-api/docs/pricing (2025-11-26)

Note: Preview/experimental models use base model pricing as approximation.
"""

from typing import Dict, Any, Optional, Tuple

# Pricing per 1M tokens (input, output) in USD
# Format: "model_pattern": (input_price, output_price)
MODEL_PRICING = {
    # Gemini 2.5 Pro
    "gemini-2.5-pro": (1.25, 10.00),  # ≤200k context

    # Gemini 2.5 Flash variants
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-preview": (0.30, 2.50),
    "models/gemini-2.5-flash-preview": (0.30, 2.50),

    # Gemini 2.5 Flash-Lite
    "gemini-2.5-flash-lite": (0.10, 0.40),

    # Gemini 2.0 Flash variants
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.0-flash-exp": (0.10, 0.40),
    # thinking tokens included in output
    "gemini-2.0-flash-thinking-exp": (0.10, 0.40),
    "gemini-2.0-flash-thinking-exp-01-21": (0.10, 0.40),

    # Gemini 2.0 Flash-Lite
    "gemini-2.0-flash-lite": (0.075, 0.30),

    # Legacy/fallback
    "default": (0.10, 0.40),
}


def get_model_pricing(model_name: str) -> Tuple[float, float]:
    """
    Get (input_price, output_price) per 1M tokens for a model.

    Args:
        model_name: Model identifier (e.g., "gemini-2.5-flash-preview-05-20")

    Returns:
        Tuple of (input_price_per_1M, output_price_per_1M)
    """
    # Normalize model name
    model_lower = model_name.lower()

    # Direct match
    if model_lower in MODEL_PRICING:
        return MODEL_PRICING[model_lower]

    # Pattern matching for versioned models
    for pattern, prices in MODEL_PRICING.items():
        if pattern in model_lower:
            return prices

    # Fallback
    return MODEL_PRICING["default"]


def calculate_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate cost in USD for a single model call.

    Args:
        model_name: Model identifier
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens

    Returns:
        Cost in USD
    """
    input_price, output_price = get_model_pricing(model_name)

    # Convert from per-1M to per-token
    input_cost = (input_tokens / 1_000_000) * input_price
    output_cost = (output_tokens / 1_000_000) * output_price

    return input_cost + output_cost


def calculate_pipeline_cost(
    agent_executions: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate total cost for a pipeline execution.

    Args:
        agent_executions: Dict of agent_name -> execution data with:
            - model or declared_model: model name
            - token_usage: {prompt_tokens, completion_tokens, total_tokens}

    Returns:
        {
            "per_agent": {agent_name: cost_usd},
            "total_usd": total_cost,
            "breakdown": {
                "total_input_tokens": ...,
                "total_output_tokens": ...,
                "input_cost_usd": ...,
                "output_cost_usd": ...
            }
        }
    """
    per_agent = {}
    total_input_tokens = 0
    total_output_tokens = 0
    total_input_cost = 0.0
    total_output_cost = 0.0

    for agent_name, exec_data in agent_executions.items():
        # Try multiple keys for model name
        model = (
            exec_data.get("model") or
            exec_data.get("declared_model") or
            exec_data.get("actual_model") or
            "default"
        )

        # Get token counts from token_usage
        usage = exec_data.get("token_usage", {})
        input_tokens = usage.get("prompt_tokens", 0) or 0
        output_tokens = usage.get("completion_tokens", 0) or 0

        # If only total is available, estimate split
        if input_tokens == 0 and output_tokens == 0:
            total = usage.get("total_tokens", 0) or 0
            input_tokens = int(total * 0.8)
            output_tokens = total - input_tokens

        cost = calculate_cost(model, input_tokens, output_tokens)
        per_agent[agent_name] = round(cost, 6)

        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        input_price, output_price = get_model_pricing(model)
        total_input_cost += (input_tokens / 1_000_000) * input_price
        total_output_cost += (output_tokens / 1_000_000) * output_price

    return {
        "per_agent": per_agent,
        "total_usd": round(total_input_cost + total_output_cost, 6),
        "breakdown": {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "input_cost_usd": round(total_input_cost, 6),
            "output_cost_usd": round(total_output_cost, 6),
        }
    }


def format_cost_summary(cost_data: Dict[str, Any]) -> str:
    """Format cost data as human-readable string."""
    lines = [
        f"Total Cost: ${cost_data['total_usd']:.4f} USD",
        f"  Input:  {cost_data['breakdown']['total_input_tokens']:,} tokens (${cost_data['breakdown']['input_cost_usd']:.4f})",
        f"  Output: {cost_data['breakdown']['total_output_tokens']:,} tokens (${cost_data['breakdown']['output_cost_usd']:.4f})",
        "",
        "Per Agent:"
    ]

    for agent, cost in cost_data["per_agent"].items():
        lines.append(f"  {agent}: ${cost:.4f}")

    return "\n".join(lines)
