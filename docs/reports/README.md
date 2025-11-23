# Individual Analysis Reports

This directory contains detailed, scenario-specific ODD analysis reports.

## Reports

Each report provides comprehensive analysis for a single scenario with:
- Interactive acceleration timeline and risk matrix charts
- Side-by-side camera and BEV occupancy grid images  
- Critical violation spotlights with detailed explanations
- Complete ODD compliance breakdown
- Executive summary and recommendations

### Available Reports

- **[Demo Report](demo_report.html)** - `real_03_174232` living room scenario *(coming soon)*

### Generating New Reports

Use the report generator script from the project root:

```bash
python scripts/generate_html_report.py \
    --input data/analysis_results/path/to/full_result.json \
    --scenario-dir data/processed/test_data/real/scenario_name \
    --output docs/reports/scenario_name.html
```

The generator will:
1. Parse the analysis JSON result
2. Embed camera and BEV images (base64 encoding)
3. Generate interactive Plotly charts
4. Create a self-contained HTML file (~3-4 MB)

### Report Features

- **Portable:** Single HTML file with embedded images
- **Interactive:** Plotly.js charts with hover tooltips and zoom
- **Responsive:** Mobile-friendly Bootstrap 5 layout
- **Dark Mode:** Toggle between light/dark themes
- **Fast:** Optimized rendering, works offline

---

**Back to:** [Main Site](../index.html) | [Dashboard](../dashboard.html) | [Documentation](../README.md)
