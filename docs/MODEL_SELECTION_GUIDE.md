# Model Selection Guide for ODD Workflow Agents

## Test Results (Nov 21, 2025)

We tested all agents with `gemini-2.0-flash-lite` vs `gemini-2.5-pro` to optimize cost/performance.

### Agent Performance Summary

| Agent | Flash-Lite Performance | Recommended Model | Rationale |
|-------|----------------------|-------------------|-----------|
| **Perception Agent** | ⚠️ Degraded | `gemini-2.5-pro` | Vision-heavy analysis; flash-lite misclassified lighting (called bright scenes "dim"), produced less detailed environmental constraints |
| **Motion Agent** | ⚠️ Data Loss | `gemini-2.5-pro` | Flash-lite failed to preserve per-window motion arrays during aggregation; 2.5-pro needed for reliable data structure preservation |
| **Collision Agent** | ⚠️ Acceptable | `gemini-2.5-pro` | Complex multimodal fusion (motion+camera+LiDAR); flash-lite more conservative but less nuanced |
| **ODD Spec Agent** | ✅ Perfect | `gemini-2.0-flash-lite` | Pure JSON synthesis from structured data, no vision or complex reasoning |

### Cost/Performance Strategy

**Use `gemini-2.5-pro` for:**
- Perception Agent - requires accurate vision analysis
- Motion Agent - needs reliable data structure preservation during aggregation
- Collision Agent - needs sophisticated multimodal fusion
- Report Agent - high-quality report generation

**Use `gemini-2.0-flash-lite` for:**
- ODD Spec Agent - JSON aggregation only
- COD Agent - simple comparison logic

**Estimated Cost Savings:** ~30% reduction by using flash-lite for odd_spec + cod agents (updated from original 40-50% estimate after motion agent reassignment)

### Implementation Notes

- Each agent has its own `GEMINI_MODEL_*` variable in the full workflow
- Start with 2.5-pro for all agents during initial testing
- Switch to hybrid approach once pipeline is validated
- COD and Report agents TBD (test after full workflow implementation)

### Future Optimization

Consider testing:
- `gemini-1.5-flash` for even cheaper motion/odd_spec processing
- Different models for loop vs summary agents in sequential workflows
- Caching strategies for repeated scenario analysis
