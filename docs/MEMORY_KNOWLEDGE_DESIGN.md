# ODD Observer – Memory & Knowledge Design

## 1. Context & Goals

The current ODD / COD pipeline in `odd_agents` is:

- **Run-scoped**: each run analyzes a short 10–20 second snippet of a larger scenario.
- **Artifact-driven**: major structured outputs (ODD spec, window analyses, COD results, reports) are written as artifacts via strict tools.
- **Schema-aligned**: the ODD spec, upstream agents, COD calculators, and evaluators share a consistent schema enforced by artifact-writing tools.

We now want to introduce **persistent knowledge** that:

1. Provides a **shared reference brain** for key agents (ODD/COD/robotics fundamentals, internal policies).
2. Allows the pipeline to **accumulate cross-scenario knowledge** across many snippet runs (e.g., typical COD distance for a given ODD, recurring failure patterns).

Constraints:

- Must work cleanly with **ADK session memory** and existing **artifacts**.
- No fine-tuning.
- RAG is optional; design should be useful even without vector search.

Core rule:

> **Artifacts** handle *what happened in this run*.
> **Memory** handles *what we know across runs* (plus pointers).
> **Reference docs** handle *fundamentals and house rules*.

---

## 2. Design Overview

We separate three layers:

1. **Artifacts** – large, structured, per-run outputs  
   - ODD spec for this run  
   - Perception/motion/collision analyses  
   - COD + COD distance  
   - Evaluator verdicts & reports  

2. **Memory (ADK in-memory memory)** – small, cross-run knowledge  
   - Reference pointers to canonical docs/artifacts  
   - Per-ODD aggregates and profiles  
   - Compact summaries of notable past runs  

3. **Reference docs (optional RAG corpus)** – static fundamentals  
   - Robotics + ODD/COD definitions and examples  
   - Internal policies (how we interpret COD distance, axis criticality)  
   - Stored as one or more artifacts, optionally indexed for RAG later  

---

## 3. Memory Schema

ADK memory is a generic key/value store. We define our own schema so agents and tools stay aligned.

We’ll use three main families:

- `ref:*`    – reference pointers and indices  
- `global:*` – aggregated knowledge across runs  
- `case:*`   – compact summaries of individual runs  

### 3.1 Reference entries (`ref:*`)

Purpose: Give agents a stable way to find canonical reference material.

Example:

```jsonc
// key: ref:odd_cod_fundamentals
{
  "sections": {
    "odd_definitions": "artifact:ref_odd_cod_v1#odd_definitions",
    "cod_distance": "artifact:ref_odd_cod_v1#cod_distance",
    "categorical_axes": "artifact:ref_odd_cod_v1#categorical_axes",
    "safety_policy": "artifact:ref_odd_cod_v1#safety_policy"
  }
}
```

Usage:

- ODD Spec, Evaluator, and Report agents get this memory injected.
- Prompts can say:  
  "If you need foundational definitions, refer to `ref:odd_cod_fundamentals.sections.*`."

Implementation notes:

- The artifact `artifact:ref_odd_cod_v1` is a markdown/JSON doc under `docs/` (checked in).
- Memory just stores pointers and light metadata, not the full doc.

### 3.2 Per-ODD profiles (`global:odd_profile:*`)

Purpose: Accumulate knowledge across runs for each ODD "flavor" or ID.

Key shape:

```jsonc
// key: global:odd_profile:<odd_id>
{
  "odd_id": "urban_sidewalk_v1",
  "num_runs": 37,
  "cod_distance_stats": {
    "min": 0.03,
    "max": 0.41,
    "mean": 0.12,
    "p90": 0.25
  },
  "common_axes_violated": ["lighting", "rain_active"],
  "example_runs": {
    "low_risk": ["run:0012", "run:0034"],
    "high_risk": ["run:0103"]
  },
  "last_updated": "2025-11-27T12:34:56Z"
}
```

This is small, cheap to inject, and represents:

- Typical COD distance behavior for this ODD.
- Which axes cause trouble most often.
- A few representative run IDs to pull detailed case summaries from if needed.

### 3.3 Per-run case summaries (`case:run:*`)

Purpose: Allow agents to reference specific previous runs without loading full artifacts.

Key shape:

```jsonc
// key: case:run:<run_id>
{
  "run_id": "run:0103",
  "odd_id": "urban_sidewalk_v1",
  "cod_distance": 0.35,
  "axes_dominant": ["rain_active"],
  "num_flagged_windows": 5,
  "exit_intervals": [
    { "start_time_s": 12.3, "end_time_s": 18.9 }
  ],
  "final_verdict": "fail",
  "notes": "Sustained rain_active violation; lighting borderline but acceptable."
}
```

Agents can then:

- Use these as **few-shot examples**:  
  - "This run looks like run:0103 (fail) or run:0012 (pass)."  
- Reference them in reports:  
  - "Compared to other runs in this ODD, this scenario is among the safest / riskiest 10%."

---

## 4. Data Flow by Run

Each snippet run goes through:

### 4.1 Normal pipeline (existing)

- ODD Spec agent produces ODD spec artifact.
- Perception/motion/collision agents produce artifacts + flagged windows.
- COD / COD distance tools produce COD artifacts.
- Evaluator and Report agents produce final verdict + report artifacts.

### 4.2 Consolidation step (new)

A post-run consolidator tool or agent:

- Reads:
  - ODD spec artifact (to get `odd_id` or derive a stable ODD key).
  - COD artifacts (distance, axes, exit intervals).
  - Evaluator verdict + any human label (if available later).
- Writes:
  - `case:run:<run_id>` – per-run summary.
  - `global:odd_profile:<odd_id>` – updated aggregate profile.

### 4.3 Next runs

When a new run starts:

- ODD Spec agent can read `ref:odd_cod_fundamentals` for definitions/patterns.
- Evaluator and Report agents can read:
  - `global:odd_profile:<odd_id>` if it exists.
  - Optionally 1–2 `case:run:*` summaries for that ODD as examples.

This gives the pipeline a **cross-scenario "experience"** without reloading full logs or artifacts.

---

## 5. Agent-Level Responsibilities

### 5.1 ODD Spec Agent

Reads:

- Reference memory `ref:odd_cod_fundamentals` for definitions/patterns.
- Optionally `global:odd_profile:<odd_id>` when refining a known ODD.

Writes:

- ODD spec artifact for the current run (existing behavior).

Prompt guidance:

- Keep instructions short; rely on the reference artifact for longer explanations.
- Be explicit that **numeric thresholds and axis types come from artifacts/spec**, not from memory.

### 5.2 Sensor/Processing Agents (Perception / Motion / Collision)

Behavior mostly unchanged:

- Read the ODD spec artifact to know which axes to populate per window.
- Produce structured artifacts for per-window data and flagged windows.

Optional enhancement:

- Include a small **axis statistics summary** in their artifacts that the consolidator can use to update `common_axes_violated` stats.

### 5.3 COD / COD Distance Tools

Remain pure tools:

- Do not read or write memory directly.
- Consume artifacts and produce COD artifacts (`cod_overall`, `cod_timeline`, `cod_distance`, etc.).

This keeps core numeric logic deterministic and testable.

### 5.4 Evaluator Agent

Reads:

- Current run artifacts:
  - ODD spec
  - COD results
  - Flagged windows
- Memory:
  - `global:odd_profile:<odd_id>` (if available)
  - Optionally a small selection of `case:run:*` summaries as examples

Responsibilities (beyond current):

- Use `global:odd_profile` to place this run in context:
  - "COD distance is higher/lower than typical for this ODD."
  - "This run shows the same recurring issue with axis X."
- Optionally refer to previous cases:
  - "This scenario resembles run:0103, which was also marked as fail due to persistent rain violations."

Writes:

- Evaluator verdict artifact (existing behavior).

### 5.5 Report Agent

Reads:

- ODD spec, perception/motion/collision summaries, COD, exit analysis.
- `global:odd_profile:<odd_id>` from memory for context.

Responsibilities:

- Enhance report narrative:
  - "Across 37 runs in this ODD, typical COD distances are X–Y; this run sits at the Nth percentile."
  - "The lighting axis is a recurrent issue in this ODD; this run continued that trend / improved on it."

Writes:

- Report artifact only.

---

## 6. Consolidator Logic (New Component)

Implement either as:

- A **tool** called after the pipeline finishes, or
- A dedicated small agent that calls a tool to update memory.

### Inputs

- `run_id` (stable identifier)
- ODD spec artifact (for `odd_id`)
- COD artifacts:
  - `cod_distance`
  - `cod_overall`
  - `cod_timeline` or exit intervals
- Evaluator verdict artifact:
  - `final_verdict` (pass/warn/fail, etc.)
  - Optional comments/notes

### Outputs

1. **Per-run case summary**:

   ```jsonc
   case:run:<run_id> = {
     "run_id": "<run_id>",
     "odd_id": "<odd_id>",
     "cod_distance": <float>,
     "axes_dominant": [...],
     "num_flagged_windows": <int>,
     "exit_intervals": [...],
     "final_verdict": "pass|warn|fail",
     "notes": "optional short summary"
   }
   ```

2. **Global ODD profile**:

   - If `global:odd_profile:<odd_id>` exists:
     - Update `num_runs`, `cod_distance_stats` (rolling stats), `common_axes_violated`.
     - Optionally manage `example_runs.low_risk` / `high_risk` with a simple heuristic.
   - Else:
     - Create a new profile with this run as seed.

---

## 7. RAG Integration (Optional, Future)

If we add RAG later:

- The **corpus** is primarily:
  - Canonical reference artifacts (e.g. `artifact:ref_odd_cod_v1`).
  - Possibly a curated subset of `case:run:*` summaries and selected reports, not raw logs.

- Memory still:
  - Stores pointers (like `ref:odd_cod_fundamentals`).
  - Stores aggregated stats and small case summaries.

Agents that might call RAG:

- ODD Spec agent, when drafting new ODDs from high-level descriptions.
- Evaluator and Report agents, when they need extra conceptual context or want to see similar-case narratives.

Core numeric and schema logic **remains in artifacts + tools**, not in RAG.

---

## 8. Implementation Checklist

Minimal steps to get this started:

1. **Define the memory schema doc** (this file) and commit under `docs/guides/`.
2. **Implement the memory key conventions**:
   - `ref:odd_cod_fundamentals`
   - `global:odd_profile:<odd_id>`
   - `case:run:<run_id>`

3. **Create the reference artifact**:
   - `docs/guides/ODD_COD_FUNDAMENTALS.md` (or similar).
   - Add an initialization script / setup agent to populate `ref:odd_cod_fundamentals` in memory with pointers to sections.

4. **Build the Consolidator tool/agent**:
   - Reads current run artifacts.
   - Writes/updates `case:run:*` and `global:odd_profile:*` in memory.

5. **Wire Evaluator and Report agents to read memory**:
   - Inject `global:odd_profile:<odd_id>` and `ref:odd_cod_fundamentals` into their prompts.
   - Add small logic in prompts to use that context for “relative to typical” reasoning.

6. **Add tests / notebooks**:
   - One or two example runs that:
     - Generate ODD spec, COD, and evaluator artifacts.
     - Invoke the consolidator.
     - Show that memory entries are updated and used on subsequent runs.

From there, you can iterate on:

- Better aggregation in `global:odd_profile`.
- Richer `case:run:*` summaries.
- Optional RAG indexing over reference artifacts and selected reports.

