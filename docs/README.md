# ODD Analysis Interactive Reports & Dashboard

This directory contains the GitHub Pages site for the ODD Observer project, including interactive HTML reports and aggregate dashboards.

## Site Structure

```
docs/
├── index.html              # Landing page (portfolio showcase)
├── dashboard.html          # Aggregate analysis dashboard
├── reports/                # Individual scenario reports
│   ├── demo_report.html
│   └── [more reports...]
├── agent_knowledge/        # Agent knowledge reference docs (fundamentals, sensors, profiles)
├── agents/                 # Agent architecture documentation
│   ├── README.md           # Overview and workflow
│   ├── PERCEPTION.md       # Perception agents
│   ├── MOTION.md           # Motion agents
│   ├── COLLISION.md        # Collision agents
│   ├── ODD_SPEC.md         # ODD specification agent
│   ├── COD_CLASSIFIER.md   # COD classification agent
│   ├── COMPLIANCE.md       # Compliance checking agent
│   └── REPORT.md           # Report generation agent
├── guides/                 # User documentation
├── examples/               # Example data and demos
└── images/                 # Documentation images
```

## Live Site

Visit: **https://danmartinez78.github.io/go2-odd-observer/**

## Pages Overview

### 🤖 Agent Architecture (`agents/`)
Comprehensive documentation for the 10-agent pipeline:
- **Overview:** Workflow diagram and agent categories
- **Per-agent docs:** Purpose, inputs, outputs, prompting strategies
- **Tool dependencies:** What each agent uses
- **Model selection:** Cost optimization strategies
- **Example outputs:** Sample JSON responses
- **Common issues:** Known edge cases and solutions

See [Agent Architecture Documentation](agents/README.md)

### 🏠 Landing Page (`index.html`)
Portfolio-quality showcase with:
- Project overview and features
- Report gallery with status badges
- Quick navigation to dashboard and guides
- Links to GitHub repo and documentation

### 📈 Dashboard (`dashboard.html`)
Aggregate statistics across all analyzed scenarios:
- Compliance distribution (pie chart)
- Violation breakdown (bar chart)
- Environment distribution
- Scenario-by-scenario comparison table
- Key performance metrics

### 📊 Individual Reports (`reports/`)
Detailed analysis for specific scenarios:
- Interactive Plotly charts (acceleration timeline, risk matrix)
- Side-by-side camera + BEV image comparisons
- Critical violation spotlights
- Dark mode support
- Mobile-responsive design

## Generating Content

### Individual Reports

Generate detailed reports for specific scenarios:

```bash
python scripts/generate_html_report.py \
    --input path/to/full_result.json \
    --scenario-dir path/to/scenario/with/images \
    --output docs/reports/scenario_name.html
```

**Example:**
```bash
python scripts/generate_html_report.py \
    --input data/analysis_results/manual/20251123_182732/real_03_174232/full_result.json \
    --scenario-dir data/processed/test_data/real/real_03_174232 \
    --output docs/reports/real_03_174232.html
```

### Aggregate Dashboard

Generate dashboard from batch analysis results:

```bash
python scripts/generate_dashboard.py \
    --batch-dir data/analysis_results/automated/batch_20251123 \
    --output docs/dashboard.html
```

This will:
- Aggregate all `full_result.json` files in the batch directory
- Calculate compliance distribution and violation statistics
- Generate interactive charts (Plotly.js)
- Create scenario comparison table

## Viewing Reports

### Local Viewing

1. **Simple:** Open HTML file directly in browser
   ```bash
   # macOS
   open docs/demo_report.html
   
   # Linux
   xdg-open docs/demo_report.html
   
   # Windows
   start docs/demo_report.html
   ```

2. **HTTP Server:** For full functionality
   ```bash
   python -m http.server -d docs 8080
   # Then open: http://localhost:8080/demo_report.html
   ```

### GitHub Pages Deployment

1. **Enable GitHub Pages:**
   - Go to repo Settings → Pages
   - Source: Deploy from a branch
   - Branch: `dev` or `main`, Directory: `/docs`
   - Save

2. **Access Site:**
   - Landing: `https://danmartinez78.github.io/go2-odd-observer/`
   - Dashboard: `https://danmartinez78.github.io/go2-odd-observer/dashboard.html`
   - Reports: `https://danmartinez78.github.io/go2-odd-observer/reports/demo_report.html`

3. **Auto-Deployment:**
   - Push to selected branch automatically updates site
   - Changes typically live within 1-2 minutes

## Report Features

### Hero Section
- Overall ODD compliance status (IN_ODD / BOUNDARY / OUT_ODD)
- Key metrics dashboard
- Scenario metadata

### Critical Events Spotlight
- Windows with violations highlighted
- Side-by-side camera + BEV images
- Detailed violation breakdown
- Context from perception analysis

### Interactive Charts
1. **Acceleration Timeline**
   - Bar chart with color-coded thresholds
   - Hover for exact values
   - Threshold lines at 2.0 m/s² (IN_ODD) and 5.0 m/s² (OUT_ODD)

2. **Risk Matrix**
   - Scatter plot: Collision Risk vs Traversability
   - Each point = one window
   - Color-coded by risk level

### ODD Compliance Tables
- Categorical compliance (environment, terrain, lighting)
- Numeric compliance (acceleration, obstacle density, etc.)
- Current values vs ODD requirements

### Executive Summary
- High-level overview
- Key findings (bullet points)
- Actionable recommendations

## Customization

The report generator is designed to be extensible:

- **Styling:** Modify CSS in `generate_html_report.py`
- **Charts:** Adjust Plotly configurations in `generate_plotly_charts()`
- **Layout:** Edit HTML template structure
- **Images:** Add more BEV visualization types (height, density, roughness)

## Technical Details

- **Framework:** Bootstrap 5 for responsive design
- **Charts:** Plotly.js for interactive visualizations
- **Images:** Base64-embedded for portability
- **File Size:** ~3-4 MB per report (includes images)
- **Dependencies:** None (CDN-loaded libraries)

## Future Enhancements

### Planned Pages
- [ ] **Gallery:** Visual showcase of best/worst scenarios
- [ ] **Methodology:** Deep-dive into multi-agent analysis approach
- [ ] **About:** Project background and architecture
- [ ] **Results:** Cross-scenario performance analysis

### Planned Features
- [ ] Image comparison slider (drag to reveal)
- [ ] Animated replay through windows
- [ ] Smart filtering (violations only, high-risk only)
- [ ] Export to PDF
- [ ] Radar chart for ODD compliance
- [ ] Timeline navigation with thumbnails
- [ ] Real-time batch analysis progress tracker

## Example Screenshots

### Light Mode
![Hero Section](examples/screenshots/hero_light.png)
![Charts](examples/screenshots/charts_light.png)

### Dark Mode
![Hero Section](examples/screenshots/hero_dark.png)
![Charts](examples/screenshots/charts_dark.png)

---

**Generated by:** ODD Observer Analysis Pipeline  
**Last Updated:** November 23, 2025
