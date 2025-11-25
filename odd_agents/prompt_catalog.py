"""
Prompt Catalog - Maps prompt hashes to human-readable metadata.

This catalog enables:
1. Looking up which prompt version was used for an analysis
2. Comparing prompts across versions
3. Debugging prompt drift issues
4. Reproducing exact agent configurations

Auto-generated from current agent prompts. 
Updated whenever prompts change.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Handle imports for both module and standalone execution
try:
    from .metadata import hash_text
    from .agent_prompts import get_all_prompts
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from metadata import hash_text
    from agent_prompts import get_all_prompts


def build_prompt_catalog() -> Dict[str, Any]:
    """Build catalog of all current agent prompts with metadata.

    Returns:
        Dict mapping prompt_hash -> {agent, version, preview, full_text}
    """
    try:
        from .agents import AGENT_VERSIONS
    except ImportError:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from agents import AGENT_VERSIONS

    prompts = get_all_prompts()
    catalog = {}

    for agent_name, prompt_text in prompts.items():
        prompt_hash = hash_text(prompt_text)

        catalog[prompt_hash] = {
            'agent_name': agent_name,
            'version': AGENT_VERSIONS.get(agent_name, 'unknown'),
            'prompt_hash': prompt_hash,
            'prompt_length_chars': len(prompt_text),
            'prompt_preview': prompt_text[:200].replace('\n', ' ') + '...',
            'full_prompt': prompt_text,
            'catalog_generated': datetime.utcnow().isoformat(),
        }

    return catalog


def save_prompt_catalog(output_path: Path = None):
    """Save prompt catalog to JSON file.

    Args:
        output_path: Where to save catalog. Defaults to odd_agents/prompt_catalog.json
    """
    if output_path is None:
        output_path = Path(__file__).parent / 'prompt_catalog.json'

    catalog = build_prompt_catalog()

    with open(output_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    print(f"✅ Prompt catalog saved to: {output_path}")
    print(f"📊 Cataloged {len(catalog)} unique prompts")


def load_prompt_catalog(catalog_path: Path = None) -> Dict[str, Any]:
    """Load prompt catalog from JSON file.

    Args:
        catalog_path: Path to catalog file. Defaults to odd_agents/prompt_catalog.json

    Returns:
        Catalog dict
    """
    if catalog_path is None:
        catalog_path = Path(__file__).parent / 'prompt_catalog.json'

    if not catalog_path.exists():
        print(
            f"⚠️  Catalog not found at {catalog_path}, building fresh catalog...")
        return build_prompt_catalog()

    with open(catalog_path) as f:
        return json.load(f)


def lookup_prompt(prompt_hash: str, catalog_path: Path = None) -> Dict[str, Any]:
    """Look up prompt metadata by hash.

    Args:
        prompt_hash: SHA-256 hash of prompt (16-char hex)
        catalog_path: Optional path to catalog file

    Returns:
        Prompt metadata dict or None if not found
    """
    catalog = load_prompt_catalog(catalog_path)
    return catalog.get(prompt_hash)


def reconstruct_workflow_config(pipeline_metadata: Dict[str, Any],
                                catalog_path: Path = None) -> Dict[str, Any]:
    """Reconstruct full workflow configuration from pipeline metadata.

    Args:
        pipeline_metadata: metadata from analysis result
        catalog_path: Optional path to prompt catalog

    Returns:
        Complete workflow configuration with human-readable prompts
    """
    catalog = load_prompt_catalog(catalog_path)

    config = {
        'pipeline_version': pipeline_metadata['pipeline_version'],
        'pipeline_timestamp': pipeline_metadata['pipeline_start_time'],
        'pipeline_duration_seconds': pipeline_metadata['pipeline_duration_seconds'],
        'odd_specification': {
            'hash': pipeline_metadata['odd_specification']['hash'],
            'version': pipeline_metadata['odd_specification']['version'],
        },
        'scenario': {
            'name': pipeline_metadata['scenario_info']['scenario_name'],
            'path': pipeline_metadata['scenario_info']['scenario_path'],
        },
        'agents': []
    }

    # Reconstruct each agent's configuration
    for agent_name, agent_exec in pipeline_metadata['agent_executions'].items():
        prompt_hash = agent_exec['prompt_hash']
        prompt_info = catalog.get(prompt_hash, {})

        agent_config = {
            'agent_name': agent_name,
            'version': agent_exec['version'],
            'model': {
                'declared': agent_exec['declared_model'],
                'actual': agent_exec['actual_model'],
                'matches': agent_exec['declared_model'] == agent_exec['actual_model']
            },
            'prompt': {
                'hash': prompt_hash,
                'preview': prompt_info.get('prompt_preview', 'Prompt not found in catalog'),
                'full_prompt_available': bool(prompt_info.get('full_prompt'))
            },
            'execution': {
                'timestamp': agent_exec['timestamp'],
                'invocation_id': agent_exec['invocation_id'],
            }
        }

        # Add token usage if available
        if 'token_usage' in agent_exec:
            agent_config['token_usage'] = agent_exec['token_usage']

        config['agents'].append(agent_config)

    return config


if __name__ == '__main__':
    # Generate and save catalog when run as script
    save_prompt_catalog()

    # Display summary
    catalog = load_prompt_catalog()
    print("\n📋 Prompt Catalog Summary:")
    print("=" * 80)
    for prompt_hash, info in catalog.items():
        print(f"\n{info['agent_name']} v{info['version']}")
        print(f"  Hash: {prompt_hash}")
        print(f"  Length: {info['prompt_length_chars']} chars")
        print(f"  Preview: {info['prompt_preview'][:80]}...")
