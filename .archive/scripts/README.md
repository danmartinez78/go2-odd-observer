# Archived Scripts

This directory contains scripts that have been superseded by newer implementations.

## Archived (2025-11-23)

### `odd_workflow.py`
- **Replaced by**: `scripts/run_odd_analysis.py`
- **Reason**: New script provides interactive scenario selection, better model configuration, and improved output organization
- **Status**: Superseded but functional

### `analyze_real_data.py`
- **Replaced by**: `scripts/run_odd_batch_analysis.py`
- **Reason**: New script provides better error handling, progress tracking, aggregate reporting, and organized output structure
- **Status**: Superseded but functional

### `generate_demo_results.py`
- **Replaced by**: `scripts/run_odd_analysis.py` (can use test data)
- **Reason**: New runner can analyze demo/test data interactively with same workflow
- **Status**: Superseded but functional

### `generate_demo_data.py`
- **Replaced by**: Manual test sets in `data/processed/test_data/`
- **Reason**: Real test sets from actual robot data provide better validation than synthetic data
- **Status**: Superseded, kept for reference

---

**Note**: These scripts are preserved for historical reference and potential future use. They may not be maintained going forward. Use the new production scripts in `scripts/` directory instead.
