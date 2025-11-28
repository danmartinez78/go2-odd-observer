# Tool Knowledge Access – Design Candidates

## Context
Tools lost performance after we trimmed their prompts assuming shared knowledge. Tools currently only see what’s baked into their prompt or passed as args. We need to restore grounding without bloating or duplicating the KB everywhere.

## Goals
- Give tools reliable access to relevant knowledge (fundamentals + overlays/profiles) with minimal token bloat.
- Keep call costs predictable; avoid brittle duplication.
- Preserve artifact/state safety and existing workflows.

## Candidates

### Option 1: Factory-loaded baseline + call-time injection (recommended)
- **What**: Load a small, static KB slice in the tool factory (fundamentals + tool-specific overlays). Add an optional `knowledge_context` arg to each tool call so the parent/loop agent can pass dynamic snippets.
- **How**:
  - In `create_*_tools(...)`, load the manifest and precompute a per-tool snippet (e.g., terminology, ego dims, modality cues). Bake this into the tool instruction.
  - Add `knowledge_context: str | dict | None` to tool signatures. In prompts: “Use knowledge_context if provided; otherwise rely on built-in fundamentals.”
  - Update loop agents to pass selective KB snippets per call (from `ref:knowledge_manifest`), sized for the tool (e.g., perception gets terrain/lighting/ego; motion gets dynamics/ego; collision gets safety proximities).
- **Pros**: Low refactor, deterministic baseline, supports dynamic overlays, limited token growth.
- **Cons**: Requires changes to tool signatures and callers; need a helper to assemble per-tool KB bundle.
- **Actionable**:
  - Add helper: `build_tool_kb(tool_type, manifest) -> str/dict` that extracts minimal relevant snippets.
  - Add `knowledge_context` param to tools and wire callers to pass it.
  - Add a 3–5 bullet fundamentals preamble to each tool prompt.

### Option 2: Sub-agents via AgentTool (ADK native)
- **What**: Replace FunctionTools with child ADK Agents wrapped via `AgentTool`. The parent orchestrator agent calls sub-agents like tools, but sub-agents have full agent capabilities.
- **How**:
  ```python
  from google.adk.tools import agent_tool
  
  # Sub-agent with full session state access (sees knowledge layer!)
  perception_analyst = LlmAgent(
      name="PerceptionAnalyst",
      model=Gemini(...),
      instruction="""You are a perception analyst.
      KNOWLEDGE: {ref:sensor_interpretation}  # <-- Has access!
      Analyze the sensor data for window {temp:current_window}...""",
      tools=[read_image_tool],  # Can have its own tools
  )
  
  # Wrap as tool for parent
  perception_tool = agent_tool.AgentTool(agent=perception_analyst)
  
  # Parent orchestrator uses it like any tool
  perception_orchestrator = LlmAgent(
      name="PerceptionOrchestrator",
      tools=[list_windows_tool, perception_tool, save_output_tool],
      instruction="""Process each window using PerceptionAnalyst.
      Before calling, set temp:current_window and temp:guidance...""",
  )
  ```
- **Key Benefits**:
  - **Full session state access**: Sub-agents can read `{ref:knowledge_manifest}`, `{ref:sensor_interpretation}` directly
  - **Parent can inject guidance**: Write to `temp:current_guidance` before calling; sub-agent reads it
  - **Temporal reasoning**: Parent can say "Previous window showed X, investigate Y in this window"
  - **Proper ADK tracing**: Sub-agent calls are observable in traces
  - **State propagation**: `AgentTool` handles response forwarding and state changes
- **Challenges**:
  - **Multimodal input**: Need to pass image paths via state, sub-agent loads images with own tool
  - **Latency**: Additional agent overhead vs raw API call
  - **Testing**: Need to validate artifact/temp namespace isolation
- **Actionable**:
  - Build toy example: parent agent + sub-agent with knowledge access
  - Test multimodal pattern: parent writes `temp:image_path`, sub-agent loads and analyzes
  - Measure latency/cost vs. FunctionTool; decide if acceptable
  - If viable, migrate perception tool first as prototype

### Option 3: Hardcode KB into tool prompts
- **What**: Copy key KB sections into each tool prompt (terminology, ego, modality).
- **Pros**: No caller changes; always present.
- **Cons**: Token bloat; duplication/staleness risk; no dynamic overlays; brittle.
- **Actionable**: Only use as fallback or minimal baseline; prefer Option 1’s small preamble.

### Option 4: Static appendix + optional caller injection
- **What**: Attach a small static KB appendix to each tool prompt (fundamentals + modality tips) and allow caller to append dynamic snippets (similar to Option 1, but less factory logic).
- **Pros**: Simple to implement; caller can add overlays.
- **Cons**: Still some duplication; no central helper to curate snippets.

## Recommended path
Start with **Option 1** for quick wins, but **prototype Option 2 (AgentTool)** to evaluate:

### Phase A: Quick wins (Option 1)
1) Add `knowledge_context` arg to tools and loop callers.
2) Add a minimal fundamentals preamble per tool prompt.
3) Add a helper to assemble per-tool KB snippets from the manifest and pass them per call.

### Phase B: AgentTool prototype (Option 2)
4) Build a toy example: parent + sub-agent with knowledge access
5) Test multimodal pattern (image paths via state)
6) Compare latency/cost vs FunctionTool
7) If viable, migrate perception as first production sub-agent

Option 2 is architecturally cleaner but needs validation. Option 1 is safer short-term.

## Notes
- Keep KB slices tight to avoid token blowup; per-tool relevance is key.
- If no `knowledge_context` is passed, tools should still function with the built-in fundamentals (don’t fail).
- For artifact/state safety, sub-agents need careful temp key handling; FunctionTools with injected KB avoid that complexity.
