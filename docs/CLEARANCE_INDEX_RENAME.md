# Rename: traversability_score → clearance_index

## Rationale

"Clearance index" is more semantically clear than "traversability":
- **traversability** is vague - could mean terrain roughness, slope, friction, etc.
- **clearance_index** clearly communicates: "is there physical space/clearance for the robot to navigate?"

This aligns with what we're actually measuring:
- BEV occupancy gap analysis
- Can the robot fit through?
- Is the forward path clear?

## Scale (unchanged)
- 1.0 = maximum clearance (wide open)
- 0.0 = no clearance (blocked)
- ODD minimum: 0.3 (unchanged)

---

## Full Scope of Changes

### 1. Natural Language ODD Input
**File:** User-provided NL description
**Change:** Documentation/examples should use "clearance" terminology
**Status:** [ ] TODO

---

### 2. ODD Spec Agent
**File:** `odd_agents/tools/odd_spec.py`
**Changes:**
- [ ] Update axis name in ODD_AXES: `traversability_score` → `clearance_index`
- [ ] Update description to reference clearance/space
- [ ] Update any prompt text mentioning traversability

**File:** `odd_agents/agents/odd_spec.py`
**Changes:**
- [ ] Update prompt if it mentions traversability

---

### 3. Perception Tool (VLA)
**File:** `odd_agents/tools/perception.py`
**Changes:**
- [ ] Rename section header: "TRAVERSABILITY ASSESSMENT" → "CLEARANCE INDEX ASSESSMENT"
- [ ] Update all references to `traversability_score` → `clearance_index`
- [ ] Update scale descriptions to use "clearance" terminology
- [ ] Update output JSON field name in prompt

---

### 4. Perception Agent
**File:** `odd_agents/agents/perception.py`
**Changes:**
- [ ] Update prompt references to traversability → clearance_index
- [ ] Update output schema references: `min_traversability` → `min_clearance`
- [ ] Update any temporal analysis descriptions

---

### 5. COD Construction
**File:** `odd_agents/tools/cod_construction.py`
**Changes:**
- [ ] Check if axis name is hardcoded anywhere
- [ ] Should be dynamic from ODD spec, but verify

---

### 6. Evaluator Agent
**File:** `odd_agents/agents/evaluator.py`
**Changes:**
- [ ] Update prompt references to traversability
- [ ] Update per_axis_summary examples if present

---

### 7. Report Agent
**File:** `odd_agents/agents/report.py`
**Changes:**
- [ ] Update prompt references to traversability
- [ ] Update any display text generation

---

### 8. HTML Report Generator
**File:** `scripts/generate_html_report.py`
**Changes:**
- [ ] Update metric display labels
- [ ] Update any hardcoded "traversability" strings
- [ ] Update chart labels if applicable

---

### 9. Documentation
**Files:**
- [ ] `docs/agent_knowledge/*.md` - Update any knowledge docs
- [ ] `docs/agents/*.md` - Update agent documentation
- [ ] `docs/ARCHITECTURE_REDESIGN.md` - If referenced
- [ ] `README.md` - If referenced
- [ ] `.github/copilot-instructions.md` - If referenced

---

### 10. Tests
**Files:**
- [ ] `tests/test_perception_agent.py` - Update fixture expectations
- [ ] `tests/test_odd_spec_agent.py` - Update fixture expectations
- [ ] `tests/fixtures/*.json` - Update test fixtures
- [ ] Any other test files with hardcoded traversability

---

### 11. Example Data
**Files:**
- [ ] `data/examples/*.json` - Update example outputs
- [ ] Any demo/example files

---

## Occurrence Counts (as of 2024-12-01)

### Python Files (23 occurrences)
| File | Count | Priority |
|------|-------|----------|
| `odd_agents/agents/odd_spec.py` | 5 | HIGH |
| `odd_agents/agents/perception.py` | 4 | HIGH |
| `odd_agents/tools/perception.py` | 4 | HIGH |
| `odd_agents/evaluation/rubrics.py` | 5 | MEDIUM |
| `odd_agents/agents/compliance.py` | 1 | HIGH |
| `odd_agents/agents/report.py` | 1 | HIGH |
| `odd_agents/tools/odd_spec.py` | 1 | HIGH |
| `odd_agents/workflow.py` | 1 | LOW |
| `scripts/generate_html_report_old.py` | 6 | LOW (old file) |
| `tests/test_odd_spec_agent.py` | 1 | MEDIUM |

### Markdown Files (documentation - 70+ occurrences)
| File | Count | Priority |
|------|-------|----------|
| `docs/BULLETPROOF_PROMPTS_PLAN.md` | 16 | LOW |
| `docs/agents/COD_CLASSIFIER.md` | 11 | MEDIUM |
| `docs/agents/COMPLIANCE.md` | 9 | MEDIUM |
| `docs/LESSONS_LEARNED.md` | 8 | LOW |
| `docs/agents/ODD_SPEC.md` | 6 | MEDIUM |
| `docs/agents/PERCEPTION.md` | 4 | MEDIUM |
| Other docs... | ~20 | LOW |

### Search Commands
```bash
# Find all occurrences
grep -ri "traversability" odd_agents/ scripts/ tests/ --include="*.py"

# Count per file
grep -rc "traversability" odd_agents/ scripts/ | grep -v ":0"
```

---

## Implementation Order

1. **ODD Spec Tool** - Define the new axis name at the source
2. **Perception Tool** - VLA outputs the new field name
3. **Perception Agent** - Summary uses new field name
4. **COD Construction** - Verify dynamic handling
5. **Evaluator** - Update prompt references
6. **Report Agent** - Update prompt references
7. **HTML Generator** - Update display labels
8. **Tests** - Update expectations
9. **Documentation** - Update references

---

## Backwards Compatibility Notes

- Archived results will still have `traversability_score`
- New results will have `clearance_index`
- HTML report generator may need to handle both for historical comparison
- Consider: Should we add a mapping/alias in COD construction?

---

## Version Bumps Required

| Component | Current Version | New Version |
|-----------|-----------------|-------------|
| odd_spec tool | ? | +minor |
| perception tool | 11.1.0 | 12.0.0 (breaking change) |
| perception agent | 12.0.0 | 13.0.0 |
| evaluator agent | 7.1.0 | 8.0.0 |
| report agent | ? | +minor |

---

## Checklist Summary

- [ ] 1. ODD Spec Tool (`odd_agents/tools/odd_spec.py`)
- [ ] 2. ODD Spec Agent (`odd_agents/agents/odd_spec.py`)
- [ ] 3. Perception Tool (`odd_agents/tools/perception.py`)
- [ ] 4. Perception Agent (`odd_agents/agents/perception.py`)
- [ ] 5. COD Construction (`odd_agents/tools/cod_construction.py`)
- [ ] 6. Evaluator Agent (`odd_agents/agents/evaluator.py`)
- [ ] 7. Report Agent (`odd_agents/agents/report.py`)
- [ ] 8. HTML Report Generator (`scripts/generate_html_report.py`)
- [ ] 9. Documentation files
- [ ] 10. Test files and fixtures
- [ ] 11. Example data files
- [ ] 12. Verify end-to-end with test run
