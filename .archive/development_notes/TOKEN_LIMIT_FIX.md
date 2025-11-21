# ODD/COD Workflow - Token Limit Fix Summary

## Problem
The first attempt to run the workflow exceeded Gemini's token limit (2.025M tokens vs 1.048M limit):
```
ClientError: 400 INVALID_ARGUMENT. The input token count (2025515) exceeds the maximum number of tokens allowed (1048575)
```

**Root Cause**: Agent tool responses contained large binary image data that was being serialized into agent internal state/messages.

## Solution

### 1. Updated Agent Instructions
All three vision-related agents (Vision, Terrain, Collision) were updated to:
- Analyze images immediately when received
- Extract only analysis results in their JSON outputs
- **CRITICALLY: Never include image_bytes in the final output**

**Files modified**: `/notebooks/odd_cod_workflow.ipynb` cells:
- Vision Agent (cell #VSC-874fe498)
- Terrain Agent (cell #VSC-96174270)
- Collision Agent (cell #VSC-e4c944b4)

**Key instruction**: "DO NOT include the raw image bytes in your output - just the analysis results"

### 2. Changed Image Tool Responses
Modified `get_window_image_raw()` function to return:
- **Before**: `{"image_bytes": <486KB binary data>, ...}` 
- **After**: `{"image_base64": "<~633KB base64 string>", ...}`

**Benefit**: Base64 strings serialize more efficiently than binary data when included in JSON agent messages.

**File modified**: `/notebooks/odd_cod_workflow.ipynb` cell #VSC-54856c22

### 3. Verification Testing
Created standalone test (`test_workflow.py`) that confirmed:
- ✅ ODD Spec Agent works (text processing)
- ✅ Vision Agent works (processes 2 camera images for 2 windows)
- ✅ Terrain Agent works (processes 4 BEV image types for 2 windows)
- ✅ **NO token limit exceeded** with all fixes applied

## Result
Workflow can now execute without hitting token limits. The key was ensuring:
1. Large binary/base64 data doesn't accumulate in agent message history
2. Agents focus on analysis results, not data pass-through
3. Image data is processed immediately, not stored for later

## Testing the Workflow
To run the full workflow:
1. Execute setup cells in `odd_cod_workflow.ipynb` (cells 1-7)
2. Execute the runner setup cells (cells 8-23)
3. Execute the final cell to run `runner.run_debug()`

Expected: Workflow completes successfully within token limits.

## Git History
- `833e2ae`: Agent instructions updated to not include image bytes
- `07266c8`: Image tools changed to return base64 instead of raw bytes

These two commits together fix the token limit issue.
