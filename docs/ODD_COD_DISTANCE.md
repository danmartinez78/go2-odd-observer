# ODD–COD Distance Spec

Simple, code-friendly spec for comparing an **Operational Design Domain (ODD)** to a **Current Operating Domain (COD)**.

This version assumes every feature (axis) is exactly one of:

1. **Range** axis  → continuous value in `[min, max]` (e.g., speed, lighting)  
2. **Bool** axis   → single bit (`0`/`1`) (e.g., stairs present, safety flag)  
3. **Enum** axis   → value from a finite set of string labels (e.g., weather type)

We define how to:

- Represent ODD and COD (point and region) across these axis types
- Compute:
  - **Point violation distance** (`D_violation_point`): how far a single COD point is **outside** the ODD
  - **Point margin** (`M_point`): how close a point is to **leaving** the ODD (range axes only)
  - **Region distance** (`D_region`): how much a COD region (envelope / profile) lies **outside** the ODD

The toy example uses a quadruped robot in an office, but the math is general.

---

## 1. Axis Types and Feature Space

Each feature belongs to exactly one of three types:

### 1.1 Range Axis

- Example: `lighting`, `clutter`, `speed`  
- Value at a point: a float (typically normalized to `[0,1]`)
- ODD constraint: an interval `[min, max]`

### 1.2 Bool Axis

- Example: `stairs_present`, `emergency_mode`, `human_in_proximity`
- Value: `0` or `1`
- ODD constraint: a single allowed value (either `0` or `1`)

### 1.3 Enum Axis

- Example: `floor_type ∈ {"carpet", "tile", "concrete"}`  
  `weather ∈ {"clear", "rain", "snow", "fog"}`
- Value: one string from a fixed set
- ODD constraint: a **set of allowed labels** (e.g., `{"carpet", "tile"}`)

A single COD point is then:

```text
x = {
  "lighting": float,
  "clutter": float,
  "speed":   float,
  "stairs":  0 or 1,
  "floor_type": "carpet" | "tile" | "concrete",
  ...
}
```

---

## 2. Example ODD: Quadruped in an Office

We define a small ODD using all three axis types.

Axes:

- `L` — lighting (range axis, normalized `[0,1]`)
- `C` — clutter level (range axis `[0,1]`)
- `v` — speed (range axis `[0,1]`)
- `S` — stairs present (bool axis)
- `floor_type` — surface type (enum axis)

ODD specification:

- `L ∈ [0.4, 1.0]`   (no very-dark operation)
- `C ∈ [0.0, 0.6]`   (not extremely cluttered)
- `v ∈ [0.0, 0.6]`   (no sprinting)
- `S = 0`            (no reachable stairs)
- `floor_type ∈ {"carpet", "tile"}` (no polished concrete)

Code-friendly representation:

```python
ODD = {
    "L": {
        "type": "range",
        "min": 0.4,
        "max": 1.0,
    },
    "C": {
        "type": "range",
        "min": 0.0,
        "max": 0.6,
    },
    "v": {
        "type": "range",
        "min": 0.0,
        "max": 0.6,
    },
    "S": {
        "type": "bool",
        "allowed": 0,
    },
    "floor_type": {
        "type": "enum",
        "allowed": ["carpet", "tile"],
        # Optional: cost/similarity matrix could be added later
    },
}
```

---

## 3. COD Representations

We support two COD representations:

1. **Point COD** — a single current operating condition
2. **Region COD** — an envelope / profile over a time window

### 3.1 Point COD

Example current condition:

```python
COD_point = {
    "L": 0.5,
    "C": 0.8,
    "v": 0.5,
    "S": 1,
    "floor_type": "concrete",
}
```

### 3.2 Region COD

A region COD is a compact description of recent operation.

For each axis type:

- **Range axis**: use a min/max envelope
- **Bool axis**: use fraction of time in each value (0/1)
- **Enum axis**: use a probability / frequency distribution over labels

Example over the last hour:

```python
COD_region = {
    "L": {"min": 0.3, "max": 0.7},
    "C": {"min": 0.4, "max": 0.9},
    "v": {"min": 0.4, "max": 0.9},

    # Bool axis: frequency of each value
    "S": {"p_0": 0.6, "p_1": 0.4},

    # Enum axis: empirical distribution over labels
    "floor_type": {
        "carpet":   0.5,
        "tile":     0.3,
        "concrete": 0.2,
    },
}
```

---

## 4. Point Violation Distance (All Axis Types)

We want a scalar that measures **how far a single COD point is outside the ODD**.

- If the point fully satisfies the ODD (including on the boundary) → distance `0`
- If not → positive value; larger = more severe / multidimensional violation

We compute per-axis violation `v_i`, then aggregate.

### 4.1 Range Axis: Point Violation

For a range axis with ODD range `[a, b]` and COD value `x`:

```text
If a <= x <= b:
    v = 0
elif x > b:
    v = (x - b) / (b - a)
else:  # x < a
    v = (a - x) / (b - a)
```

So:

- `v = 0`: inside ODD on this axis
- `v > 0`: outside, normalized by the axis range length

### 4.2 Bool Axis: Point Violation

For a bool axis with allowed value `allowed` and COD value `x ∈ {0,1}`:

```text
If x == allowed:
    v = 0
else:
    v = 1
```

This treats any boolean violation as a **full violation along that axis**.

### 4.3 Enum Axis: Point Violation

For an enum axis with allowed set `A` and COD value `x`:

```text
If x in A:
    v = 0
else:
    v = 1
```

Optional future extension: replace `1` with a cost from a similarity matrix, but the simple 0/1 scheme is enough for a first implementation.

### 4.4 Aggregate Point Violation Distance

Given per-axis violations `v_i` and optional per-axis weights `w_i`:

```text
D_violation_point = sqrt( Σ_i (w_i * v_i^2) )
```

- If all `v_i = 0` → point is inside the ODD → `D_violation_point = 0`
- If any axis violates the ODD → `D_violation_point > 0`

Pseudocode implementation:

```python
def violation_distance_point(COD_point, ODD, weights=None):
    if weights is None:
        weights = {k: 1.0 for k in ODD.keys()}

    v_sq_sum = 0.0

    for feat, spec in ODD.items():
        w = weights[feat]
        x = COD_point[feat]
        t = spec["type"]

        if t == "range":
            a, b = spec["min"], spec["max"]
            if a <= x <= b:
                v = 0.0
            elif x > b:
                v = (x - b) / (b - a)
            else:  # x < a
                v = (a - x) / (b - a)

        elif t == "bool":
            allowed = spec["allowed"]
            v = 0.0 if x == allowed else 1.0

        elif t == "enum":
            allowed_set = set(spec["allowed"])
            v = 0.0 if x in allowed_set else 1.0

        else:
            raise ValueError(f"Unknown axis type {t}")

        v_sq_sum += w * (v ** 2)

    return v_sq_sum ** 0.5
```

---

## 5. Point Margin-to-Boundary (Range Axes Only)

Violation distance says **how far outside** the ODD you are.  
We also want to know, when inside, **how close to the edge** we are.

For that we use a **margin-to-boundary** metric, defined only on **range axes**.

### 5.1 Per-Axis Margin (Range)

For a range axis with ODD `[a, b]` and COD value `x`:

If inside `[a, b]`:

```text
lower_margin = (x - a) / (b - a)
upper_margin = (b - x) / (b - a)
m = min(lower_margin, upper_margin)
```

If outside ODD:

```text
m = 0
```

Interpretation:

- `m ≈ 0.5`: value near the middle of the ODD
- `m → 0`: value hugging a boundary or outside

### 5.2 Bool and Enum Axes

Bool and enum axes **do not have a geometric notion of boundary** in this simple schema.

- They contribute to **violation distance**
- They do **not** contribute to the margin-to-boundary metric

### 5.3 Aggregate Margin

Define global point margin as the minimum margin over all **range** axes:

```text
M_point = min_i(m_i over all range axes)
```

If there are no range axes, define `M_point = 0.0`.

- `D_violation_point > 0` → outside ODD, margin is effectively 0
- `D_violation_point == 0` and `M_point == 0` → exactly on a boundary (or outside on some axis)
- `D_violation_point == 0` and `M_point > 0` → strictly inside ODD; `M_point` measures how “deep” inside you are

Pseudocode:

```python
def margin_to_boundary_point(COD_point, ODD):
    margins = []

    for feat, spec in ODD.items():
        if spec["type"] != "range":
            continue  # only range axes have geometric margin

        a, b = spec["min"], spec["max"]
        x = COD_point[feat]

        if x < a or x > b:
            m = 0.0
        else:
            lower_margin = (x - a) / (b - a)
            upper_margin = (b - x) / (b - a)
            m = min(lower_margin, upper_margin)

        margins.append(m)

    if not margins:
        return 0.0

    return min(margins)
```

### 5.4 Operational Use

Example policy:

- If `D_violation_point > 0`:
  - Outside ODD → trigger fallback / safe behavior
- Else if `M_point < ε`:
  - Inside but near boundary → reduce speed, raise warnings, increase caution
- Else:
  - Comfortable operation inside ODD

`ε` is a tuned threshold (e.g., `0.1`).

---

## 6. Region Distance (All Axis Types)

Now we compare a **region COD** (envelope / profile over time) to the ODD.

For each axis, we compute a **fraction-outside** `f_i ∈ [0,1]` that measures how much of that region violates the ODD along that axis, then aggregate.

### 6.1 Range Axis: Region Fraction-Outside

COD region for a range axis: `[u_min, u_max]`  
ODD range: `[a, b]`

Compute overlap:

```text
overlap_min = max(a, u_min)
overlap_max = min(b, u_max)
overlap_len = max(0, overlap_max - overlap_min)

cod_len = max(0, u_max - u_min)
```

If `cod_len == 0`, treat as `f_i = 0` (degenerate case) or special-case as needed.

Fraction of the region outside the ODD:

```text
f_i = 1 - (overlap_len / cod_len)
```

- `f_i = 0` → region fully inside ODD
- `f_i = 1` → no overlap with ODD; completely outside

### 6.2 Bool Axis: Region Fraction-Outside

COD region for bool axis `B` with allowed value `allowed` is represented as:

```python
COD_region["B"] = {"p_0": p0, "p_1": p1}  # p0 + p1 = 1
```

Fraction outside:

```text
f_B = 1 - p_allowed
```

Example:

- ODD: `S = 0` allowed
- COD region: `{"p_0": 0.6, "p_1": 0.4}` → `f_S = 0.4`

### 6.3 Enum Axis: Region Fraction-Outside

COD region for enum axis is a distribution over labels:

```python
COD_region["floor_type"] = {
    "carpet":   0.5,
    "tile":     0.3,
    "concrete": 0.2,
}

ODD["floor_type"]["allowed"] = ["carpet", "tile"]
```

Fraction outside:

```text
f_enum = sum_{c not in allowed} p(c)
```

In the example above:

- `f_floor_type = 0.2` (20% of operation on disallowed floor type)

### 6.4 Aggregate Region Distance

Given per-axis fractions `f_i` and optional per-axis weights `w_i`:

```text
D_region = sqrt( Σ_i (w_i * f_i^2) )
```

- `D_region ≈ 0` → region of operation is almost entirely inside ODD
- Larger `D_region` → more time / volume spent outside ODD and/or more axes violated

Pseudocode:

```python
def region_distance(COD_region, ODD, weights=None):
    if weights is None:
        weights = {k: 1.0 for k in ODD.keys()}

    f_sq_sum = 0.0

    for feat, spec in ODD.items():
        w = weights[feat]
        t = spec["type"]

        if t == "range":
            a, b = spec["min"], spec["max"]
            u_min, u_max = COD_region[feat]["min"], COD_region[feat]["max"]

            cod_len = max(0.0, u_max - u_min)
            if cod_len == 0.0:
                f_i = 0.0  # or special-case
            else:
                overlap_min = max(a, u_min)
                overlap_max = min(b, u_max)
                overlap_len = max(0.0, overlap_max - overlap_min)
                f_i = 1.0 - (overlap_len / cod_len)

        elif t == "bool":
            allowed = spec["allowed"]
            dist = COD_region[feat]  # {"p_0": ..., "p_1": ...}
            p_allowed = dist[f"p_{allowed}"]
            f_i = 1.0 - p_allowed

        elif t == "enum":
            allowed_set = set(spec["allowed"])
            dist = COD_region[feat]  # {label: probability}
            f_i = sum(p for cat, p in dist.items() if cat not in allowed_set)

        else:
            raise ValueError(f"Unknown axis type {t}")

        f_sq_sum += w * (f_i ** 2)

    return f_sq_sum ** 0.5
```

---

## 7. Sanity-Check Examples

Using the ODD in Section 2.

### 7.1 Point Strictly Inside

```python
COD_in = {
    "L": 0.6,
    "C": 0.3,
    "v": 0.4,
    "S": 0,
    "floor_type": "carpet",
}
```

Expected:

- `violation_distance_point(COD_in, ODD) -> 0.0`
- `margin_to_boundary_point(COD_in, ODD) > 0` (non-zero margin)

### 7.2 Point on Boundary (Range Axes)

```python
COD_bound = {
    "L": 0.4,   # at lower bound
    "C": 0.6,   # at upper bound
    "v": 0.6,   # at upper bound
    "S": 0,
    "floor_type": "tile",  # allowed
}
```

Expected:

- `violation_distance_point(COD_bound, ODD) -> 0.0` (still valid)
- `margin_to_boundary_point(COD_bound, ODD) -> 0.0` (hugging boundaries)

### 7.3 Point Clearly Outside

```python
COD_out = {
    "L": 0.5,
    "C": 0.8,           # above max
    "v": 0.5,
    "S": 1,             # stairs present, forbidden
    "floor_type": "concrete",  # forbidden
}
```

Expected qualitatively:

- `violation_distance_point(COD_out, ODD) > 0` (violations on clutter, stairs, floor type)
- `margin_to_boundary_point(COD_out, ODD) = 0` (outside on at least one range axis)

### 7.4 Region Clearly Deviating

```python
COD_region_example = {
    "L": {"min": 0.3, "max": 0.7},  # includes values below 0.4
    "C": {"min": 0.4, "max": 0.9},  # includes values above 0.6
    "v": {"min": 0.4, "max": 0.9},  # includes values above 0.6

    "S": {"p_0": 0.6, "p_1": 0.4},  # 40% of time with stairs present

    "floor_type": {
        "carpet":   0.5,
        "tile":     0.3,
        "concrete": 0.2,
    },
}
```

Expected qualitatively:

- Range `L`: some fraction of the interval below ODD minimum → `f_L > 0`
- Range `C`, `v`: significant fraction above ODD maximum → `f_C, f_v > 0`
- Bool `S`: `f_S = 0.4`
- Enum `floor_type`: `f_floor_type = 0.2`
- `region_distance(COD_region_example, ODD) > 0` and quite noticeable

---

## 8. How to Use This in a System

At runtime:

1. **Per-timestep (point COD):**
   - Compute `D_violation_point` and `M_point`.
   - Use thresholds to decide:
     - Normal behavior (inside with good margin)
     - Cautious behavior (inside but near boundary)
     - Fallback / safe stop (outside ODD)

2. **Over windows (region COD):**
   - Maintain envelopes / distributions per axis.
   - Compute `D_region` as a health / stats measure:
     - How much of recent operation was outside ODD
     - Which axes dominated the violations

3. **For safety / engineering reports:**
   - These metrics give a simple, explainable, numeric view of:
     - How close operations typically run to boundaries (via `M_point` stats)
     - How often and how badly the ODD is exceeded (via `D_violation_point` and `D_region`)

This spec is minimal but complete for an initial implementation over range, bool, and enum axes. More sophisticated distance metrics (e.g., distribution distances like KL/Wasserstein for regions, cost matrices for enums) can be added later without changing the core interface.

