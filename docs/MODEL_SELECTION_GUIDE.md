# Model Selection Guide for ODD Workflow Agents

## Test Results (Nov 21, 2025)

We tested all agents with `gemini-2.0-flash-lite` vs `gemini-2.5-pro` to optimize cost/performance.

### Agent Performance Summary

| Agent | Flash-Lite Performance | Recommended Model | Rationale |
|-------|----------------------|-------------------|-----------|
| **Perception Agent** | ⚠️ Degraded | `gemini-2.5-pro` | Vision-heavy analysis; flash-lite misclassified lighting (called bright scenes "dim"), produced less detailed environmental constraints |
| **Motion Agent** | ✅ Perfect | `gemini-2.0-flash-lite` | Simple numeric JSON extraction, no vision required |
| **Collision Agent** | ⚠️ Acceptable | `gemini-2.5-pro` | Complex multimodal fusion (motion+camera+LiDAR); flash-lite more conservative but less nuanced |
| **ODD Spec Agent** | ✅ Perfect | `gemini-2.0-flash-lite` | Pure JSON synthesis from structured data, no vision or complex reasoning |

### Cost/Performance Strategy

**Use `gemini-2.5-pro` for:**
- Perception Agent - requires accurate vision analysis
- Collision Agent - needs sophisticated multimodal fusion

**Use `gemini-2.0-flash-lite` for:**
- Motion Agent - simple data processing
- ODD Spec Agent - JSON aggregation only

**Estimated Cost Savings:** ~40-50% reduction by using flash-lite for motion + odd_spec agents

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
