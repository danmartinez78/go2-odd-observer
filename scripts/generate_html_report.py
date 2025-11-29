#!/usr/bin/env python3
"""
Interactive HTML Report Generator for ODD Analysis (v2.0)

Generates a stunning, interactive HTML report from ODD analysis results.
Designed for GitHub Pages deployment and portfolio showcase.

Updated for Phase 1.4.5 pipeline schema with:
- Artifact-based agent outputs
- COD region with categorical/numeric split
- Compliance verdict with temporal stability
- Data source detection (sim vs real)

Usage:
    python scripts/generate_html_report.py --input /path/to/full_result.json \
                                           --scenario-dir /path/to/scenario \
                                           --output docs/reports/report.html

Features:
    - Interactive COD compliance visualization
    - Agent execution timeline with versions
    - Plotly.js charts (compliance, cost breakdown)
    - Side-by-side image comparisons
    - Dark mode, responsive design
    - GitHub Pages ready
"""

import argparse
import base64
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_analysis_result(json_path: Path) -> Dict[str, Any]:
    """Load the full analysis JSON result."""
    with open(json_path) as f:
        return json.load(f)


def encode_image_base64(image_path: Path) -> str:
    """Encode image as base64 for embedding in HTML."""
    with open(image_path, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')
    return f"data:image/png;base64,{encoded}"


def find_window_images(scenario_dir: Path, window_id: str, scenario_name: str) -> Dict[str, str]:
    """Find all images for a given window and return as base64."""
    images = {}

    # Camera image
    cam_pattern = f"cam_{scenario_name}_w{window_id}.png"
    cam_path = scenario_dir / cam_pattern
    if cam_path.exists():
        images['camera'] = encode_image_base64(cam_path)

    # BEV images
    for bev_type in ['occupancy', 'density', 'height', 'roughness']:
        bev_pattern = f"bev_{bev_type}_{scenario_name}_w{window_id}.png"
        bev_path = scenario_dir / bev_pattern
        if bev_path.exists():
            images[f'bev_{bev_type}'] = encode_image_base64(bev_path)

    return images


def get_report_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract report data, handling both old and new schema."""
    # New schema: report.result is a JSON string
    report = result.get('report', {})
    if 'result' in report:
        report_str = report['result']
        if isinstance(report_str, str):
            return json.loads(report_str)
        return report_str
    # Old schema: direct keys
    return report


def get_compliance_verdict(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract compliance verdict from new schema."""
    # Try new schema first
    fa = result.get('full_analysis', {})
    if 'compliance_verdict' in fa:
        return fa['compliance_verdict']

    # Try agent outputs
    agent_outputs = result.get('agent_outputs', {})
    eval_output = agent_outputs.get('EvaluatorAgent', {})
    if 'compliance_verdict' in eval_output:
        return eval_output['compliance_verdict']

    # Old schema fallback
    return fa.get('odd_compliance', {})


def get_cod_region(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract COD region from new schema."""
    fa = result.get('full_analysis', {})
    if 'cod_region' in fa:
        return fa['cod_region']

    agent_outputs = result.get('agent_outputs', {})
    eval_output = agent_outputs.get('EvaluatorAgent', {})
    return eval_output.get('cod_region', {})


def get_region_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract region metrics from new schema."""
    fa = result.get('full_analysis', {})
    if 'region_metrics' in fa:
        return fa['region_metrics']

    agent_outputs = result.get('agent_outputs', {})
    eval_output = agent_outputs.get('EvaluatorAgent', {})
    return eval_output.get('region_metrics', {})


def get_scenario_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract scenario metadata."""
    # Try reports.executive_summary
    reports = result.get('reports', {})
    exec_summary = reports.get('executive_summary', {})
    scenario = exec_summary.get('scenario', {})

    # Try pipeline_metadata
    pipeline_meta = result.get('pipeline_metadata', {})
    scenario_info = pipeline_meta.get('scenario_info', {})

    # Try report data
    report_data = get_report_data(result)
    scenario_meta = report_data.get('scenario_metadata', {})

    return {
        'scenario_name': scenario_info.get('scenario_name', scenario.get('name', 'Unknown')),
        'windows_analyzed': scenario_meta.get('windows_analyzed', scenario.get('windows_analyzed', 0)),
        'environment': scenario_meta.get('environment', 'Unknown'),
        'data_source': scenario_meta.get('data_source', 'unknown'),
        'data_quality': scenario_meta.get('data_quality', 'unknown'),
    }


def get_agent_outputs(result: Dict[str, Any]) -> Dict[str, Any]:
    """Get agent outputs from new schema."""
    return result.get('agent_outputs', {})


def get_key_findings(result: Dict[str, Any]) -> Dict[str, str]:
    """Extract key findings."""
    report_data = get_report_data(result)
    findings = report_data.get('key_findings', {})

    if isinstance(findings, dict):
        return findings
    elif isinstance(findings, list):
        return {'findings': findings}
    return {}


def get_issues_and_recommendations(result: Dict[str, Any]) -> tuple:
    """Extract issues and recommendations."""
    report_data = get_report_data(result)
    issues = report_data.get('issues', [])
    recommendations = report_data.get('recommendations', [])
    return issues, recommendations


def discover_windows(scenario_dir: Path, scenario_name: str) -> tuple[List[str], str]:
    """Discover available windows from image files.
    
    Returns:
        Tuple of (list of window IDs, detected scenario prefix for images)
    """
    windows = set()
    detected_prefix = scenario_name  # Default to provided name
    
    # First try exact match with provided scenario_name
    for img_file in scenario_dir.glob(f"cam_{scenario_name}_w*.png"):
        name = img_file.stem
        parts = name.split('_w')
        if len(parts) >= 2:
            window_id = parts[-1]
            windows.add(window_id)
    
    # If no windows found, try to auto-detect from any cam_*_w*.png files
    if not windows:
        for img_file in scenario_dir.glob("cam_*_w*.png"):
            name = img_file.stem  # e.g., "cam_real_173442_w010"
            # Extract window ID (last part after _w)
            parts = name.split('_w')
            if len(parts) >= 2:
                window_id = parts[-1]
                windows.add(window_id)
                # Extract the prefix (everything between "cam_" and "_w")
                prefix = name[4:name.rfind('_w')]  # Skip "cam_" and go up to "_w"
                detected_prefix = prefix
    
    return sorted(list(windows)), detected_prefix


def generate_svg_radar_chart(axes_names: list, axes_values: list, title: str = "ODD Distance by Axis") -> str:
    """Generate an inline SVG radar/spider chart for ODD compliance.

    Zero (compliant) is at a small inner ring, not the center.
    Distance from ODD increases outward - larger = more violation.
    """
    import math

    if not axes_names:
        return '<div class="text-muted text-center p-4">No data available</div>'

    width = 500
    height = 460
    cx, cy = width / 2, 220

    # Key dimensions - zero ring is NOT at center, BIGGER chart
    zero_r = 45       # Inner ring where zero/compliant sits
    max_r = 160       # Maximum radius for 100% violation

    n = len(axes_names)
    if n == 0:
        return '<div class="text-muted text-center p-4">No axes data</div>'

    angle_step = 2 * math.pi / n

    # Generate the STAR/WEB structure first - lines from center to each vertex
    web_svg = ""

    # Draw web rings at each level connecting vertices (the spider web look)
    for level in [0.0, 0.33, 0.66, 1.0]:
        r = zero_r + (max_r - zero_r) * level
        web_points = []
        for i in range(n):
            angle = -math.pi/2 + i * angle_step
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            web_points.append(f"{x},{y}")
        web_points_str = " ".join(web_points)

        if level == 0.0:
            # Zero ring - green, filled
            web_svg += f'<polygon points="{web_points_str}" fill="rgba(40, 167, 69, 0.15)" stroke="#28a745" stroke-width="2"/>'
        elif level == 1.0:
            # Outer ring - red
            web_svg += f'<polygon points="{web_points_str}" fill="none" stroke="#dc3545" stroke-width="1.5" opacity="0.6"/>'
        else:
            # Intermediate rings - dashed
            web_svg += f'<polygon points="{web_points_str}" fill="none" stroke="var(--border-color)" stroke-width="1" stroke-dasharray="4,4" opacity="0.4"/>'

    # Draw axis lines from center to each vertex (the star spokes)
    for i in range(n):
        angle = -math.pi/2 + i * angle_step
        x_end = cx + max_r * math.cos(angle)
        y_end = cy + max_r * math.sin(angle)
        web_svg += f'<line x1="{cx}" y1="{cy}" x2="{x_end}" y2="{y_end}" stroke="var(--border-color)" stroke-width="1" opacity="0.5"/>'

    # Generate labels - positioned outside the chart
    labels_svg = ""
    for i, name in enumerate(axes_names):
        angle = -math.pi/2 + i * angle_step

        # Position labels beyond max radius
        label_r = max_r + 20
        lx = cx + label_r * math.cos(angle)
        ly = cy + label_r * math.sin(angle)

        # Clean up axis name
        short_name = name.replace('_', ' ').replace(
            'mps2', '').replace('deg', '°')
        short_name = ' '.join(word.capitalize() for word in short_name.split())

        if len(short_name) > 16:
            short_name = short_name[:14] + '..'

        # Text anchor based on position
        angle_deg = math.degrees(angle) % 360
        if 60 < angle_deg < 120:  # Bottom
            anchor = "middle"
            ly += 12
        elif 120 <= angle_deg <= 240:  # Left side
            anchor = "end"
            lx -= 5
        elif 240 < angle_deg < 300:  # Top
            anchor = "middle"
            ly -= 5
        else:  # Right side
            anchor = "start"
            lx += 5

        labels_svg += f'<text x="{lx}" y="{ly}" text-anchor="{anchor}" font-size="10" fill="var(--text-secondary)">{short_name}</text>'

    # Build the data polygon - distance increases outward from zero ring
    points = []
    dots_svg = ""

    for i, value in enumerate(axes_values):
        angle = -math.pi/2 + i * angle_step

        # value is fraction outside (0 = compliant at zero_r, 1 = max violation at max_r)
        r = zero_r + (max_r - zero_r) * min(value, 1.0)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append(f"{x},{y}")

        # Dot color based on violation
        if value > 0:
            dot_color = "#dc3545"
            # Label for violations - position it smartly
            label_r_offset = 15
            lx = x + label_r_offset * math.cos(angle)
            ly = y + label_r_offset * math.sin(angle)
            dots_svg += f'<text x="{lx}" y="{ly + 3}" text-anchor="middle" font-size="10" font-weight="bold" fill="#dc3545">{value:.0%}</text>'
        else:
            dot_color = "#28a745"

        dots_svg += f'<circle cx="{x}" cy="{y}" r="5" fill="{dot_color}" stroke="white" stroke-width="2"/>'

    # Draw the data polygon
    polygon_points = " ".join(points)
    max_violation = max(axes_values) if axes_values else 0

    if max_violation == 0:
        fill_color = "rgba(40, 167, 69, 0.3)"
        stroke_color = "#28a745"
    elif max_violation < 0.5:
        fill_color = "rgba(255, 193, 7, 0.3)"
        stroke_color = "#ffc107"
    else:
        fill_color = "rgba(220, 53, 69, 0.3)"
        stroke_color = "#dc3545"

    data_svg = f'<polygon points="{polygon_points}" fill="{fill_color}" stroke="{stroke_color}" stroke-width="2.5"/>'

    # Title - more space from chart
    title_svg = f'<text x="{width/2}" y="28" text-anchor="middle" font-size="14" font-weight="bold" fill="var(--text-primary)">{title}</text>'

    # Legend at bottom
    legend_y = height - 20
    legend_svg = f'''
        <g transform="translate(70, {legend_y})">
            <circle cx="8" cy="0" r="5" fill="#28a745" stroke="white" stroke-width="1.5"/>
            <text x="20" y="4" font-size="10" fill="var(--text-secondary)">Compliant (0%)</text>
            <circle cx="160" cy="0" r="5" fill="#dc3545" stroke="white" stroke-width="1.5"/>
            <text x="172" y="4" font-size="10" fill="var(--text-secondary)">Violation (outward)</text>
        </g>
    '''

    return f'''<svg viewBox="0 0 {width} {height}" class="svg-chart" style="width:100%;max-width:{width}px;height:auto;">
        {title_svg}
        {web_svg}
        {data_svg}
        {dots_svg}
        {labels_svg}
        {legend_svg}
    </svg>'''


def generate_svg_pie_chart(labels: list, values: list, title: str = "Cost Breakdown") -> str:
    """Generate an inline SVG donut/pie chart - no external dependencies."""
    if not labels or not values or sum(values) == 0:
        return '<div class="text-muted text-center p-4">No cost data available</div>'

    import math

    width = 400
    height = 300
    cx, cy = width / 2, 140
    outer_r = 80
    inner_r = 45  # Donut hole

    colors = ['#667eea', '#764ba2', '#28a745', '#ffc107',
              '#dc3545', '#17a2b8', '#6c757d', '#fd7e14']
    total = sum(values)

    paths_svg = ""
    legend_svg = ""
    start_angle = -90  # Start from top

    for i, (label, value) in enumerate(zip(labels, values)):
        if value == 0:
            continue

        pct = value / total
        angle = pct * 360
        end_angle = start_angle + angle

        # Calculate arc
        large_arc = 1 if angle > 180 else 0

        # Convert to radians
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)

        # Outer arc points
        x1_o = cx + outer_r * math.cos(start_rad)
        y1_o = cy + outer_r * math.sin(start_rad)
        x2_o = cx + outer_r * math.cos(end_rad)
        y2_o = cy + outer_r * math.sin(end_rad)

        # Inner arc points
        x1_i = cx + inner_r * math.cos(end_rad)
        y1_i = cy + inner_r * math.sin(end_rad)
        x2_i = cx + inner_r * math.cos(start_rad)
        y2_i = cy + inner_r * math.sin(start_rad)

        color = colors[i % len(colors)]

        # Path for donut segment
        path = f'M {x1_o} {y1_o} A {outer_r} {outer_r} 0 {large_arc} 1 {x2_o} {y2_o} L {x1_i} {y1_i} A {inner_r} {inner_r} 0 {large_arc} 0 {x2_i} {y2_i} Z'
        paths_svg += f'<path d="{path}" fill="{color}" stroke="white" stroke-width="2"/>'

        # Legend item
        legend_y = 250 + (i // 3) * 18
        legend_x = 30 + (i % 3) * 130
        short_label = label.replace('Agent', '')[:10]
        legend_svg += f'<rect x="{legend_x}" y="{legend_y}" width="12" height="12" fill="{color}" rx="2"/>'
        legend_svg += f'<text x="{legend_x + 16}" y="{legend_y + 10}" font-size="10" fill="var(--text-secondary)">{short_label} ({pct:.0%})</text>'

        start_angle = end_angle

    # Center text
    center_text = f'<text x="{cx}" y="{cy - 5}" text-anchor="middle" font-size="12" fill="var(--text-secondary)">Total</text>'
    center_text += f'<text x="{cx}" y="{cy + 12}" text-anchor="middle" font-size="14" font-weight="bold" fill="var(--text-primary)">${total/1000:.3f}</text>'

    # Title
    title_svg = f'<text x="{width/2}" y="20" text-anchor="middle" font-size="14" font-weight="bold" fill="var(--text-primary)">{title}</text>'

    return f'''<svg viewBox="0 0 {width} {height}" class="svg-chart" style="width:100%;max-width:{width}px;height:auto;">
        {title_svg}
        {paths_svg}
        {center_text}
        {legend_svg}
    </svg>'''


def generate_charts_data(result: Dict[str, Any]) -> dict:
    """Generate SVG chart HTML strings."""
    charts = {}

    # COD Region Compliance Bar Chart
    region_metrics = get_region_metrics(result)
    fractions = region_metrics.get('fraction_outside_per_axis', {})

    if fractions:
        axes_names = list(fractions.keys())
        axes_values = [fractions.get(ax, 0) for ax in axes_names]
        charts['compliance_svg'] = generate_svg_radar_chart(
            axes_names, axes_values, "ODD Compliance by Axis")
    else:
        charts['compliance_svg'] = '<div class="text-muted text-center p-4">No compliance data available</div>'

    # Agent Cost Breakdown Pie Chart
    analysis_meta = result.get('analysis_metadata', {})
    cost_per_agent = analysis_meta.get('cost_per_agent', {})

    if cost_per_agent:
        agent_names = list(cost_per_agent.keys())
        # Convert to millicents for display
        agent_costs = [cost_per_agent[a] * 1000 for a in agent_names]
        charts['cost_svg'] = generate_svg_pie_chart(
            agent_names, agent_costs, "Cost Breakdown by Agent")
    else:
        charts['cost_svg'] = '<div class="text-muted text-center p-4">No cost data available</div>'

    return charts


def generate_html_report(result: Dict[str, Any], scenario_dir: Path, output_path: Path):
    """Generate the complete interactive HTML report."""

    # Extract data using new schema helpers
    report_data = get_report_data(result)
    compliance = get_compliance_verdict(result)
    cod_region = get_cod_region(result)
    region_metrics = get_region_metrics(result)
    scenario_meta = get_scenario_metadata(result)
    agent_outputs = get_agent_outputs(result)
    key_findings = get_key_findings(result)
    issues, recommendations = get_issues_and_recommendations(result)

    scenario_name = scenario_meta.get('scenario_name', scenario_dir.name)
    image_scenario_name = scenario_dir.name  # Default, may be overridden

    # Determine compliance status
    verdict = compliance.get('verdict', compliance.get('status', 'UNKNOWN'))
    confidence = compliance.get('confidence', 0)
    if isinstance(confidence, str):
        confidence = {'HIGH': 0.9, 'MEDIUM': 0.6,
                      'LOW': 0.3}.get(confidence, 0.5)

    # Status styling - support both 'BOUNDARY' and 'ODD_BOUNDARY' forms
    status_config = {
        'IN_ODD': {'color': '#28a745', 'icon': '✅', 'label': 'IN ODD'},
        'BOUNDARY': {'color': '#ffc107', 'icon': '⚠️', 'label': 'ODD BOUNDARY'},
        'ODD_BOUNDARY': {'color': '#ffc107', 'icon': '⚠️', 'label': 'ODD BOUNDARY'},
        'OUT_ODD': {'color': '#dc3545', 'icon': '❌', 'label': 'OUT OF ODD'},
    }
    # Default to UNKNOWN styling instead of OUT_ODD to avoid false negatives
    default_status = {'color': '#6c757d', 'icon': '❓', 'label': 'UNKNOWN'}
    status = status_config.get(verdict, default_status)

    # Discover windows and load images (auto-detects image prefix)
    windows, image_scenario_name = discover_windows(scenario_dir, image_scenario_name)

    # Sample windows evenly across the scenario (max 6 for display)
    MAX_DISPLAY_WINDOWS = 6
    if len(windows) > MAX_DISPLAY_WINDOWS:
        # Evenly sample across the scenario
        step = len(windows) / MAX_DISPLAY_WINDOWS
        sampled_indices = [int(i * step) for i in range(MAX_DISPLAY_WINDOWS)]
        sampled_windows = [windows[i] for i in sampled_indices]
    else:
        sampled_windows = windows

    windows_with_images = []
    for window_id in sampled_windows:
        images = find_window_images(
            scenario_dir, window_id, image_scenario_name)
        if images:
            windows_with_images.append({'id': window_id, 'images': images})

    # Generate SVG charts (no external dependencies)
    charts = generate_charts_data(result)

    # Generate timestamp
    timestamp = datetime.now().strftime("%B %d, %Y at %H:%M:%S")

    # Extract analysis metadata
    analysis_meta = result.get('analysis_metadata', {})
    pipeline_meta = result.get('pipeline_metadata', {})

    # Build agent version table
    agent_executions = pipeline_meta.get('agent_executions', {})
    agent_version_rows = ""
    for agent_name, agent_data in sorted(agent_executions.items()):
        version = agent_data.get('version', 'N/A')
        model = agent_data.get(
            'actual_model', agent_data.get('declared_model', 'N/A'))
        prompt_hash = agent_data.get('prompt_hash', 'N/A')[:8]
        tokens = agent_data.get('token_usage', {}).get('total_tokens', 0)

        agent_version_rows += f"""
                                            <tr>
                                                <td><code>{agent_name}</code></td>
                                                <td>{version}</td>
                                                <td><small>{model}</small></td>
                                                <td><code>{prompt_hash}</code></td>
                                                <td>{tokens:,}</td>
                                            </tr>"""

    if not agent_version_rows:
        agent_version_rows = """
                                            <tr>
                                                <td colspan="5" class="text-center text-muted">
                                                    <em>No agent version metadata available</em>
                                                </td>
                                            </tr>"""

    # Build COD region table
    cod_table_rows = ""
    if cod_region:
        for axis, value in sorted(cod_region.items()):
            fraction_outside = region_metrics.get(
                'fraction_outside_per_axis', {}).get(axis, 0)
            status_class = 'text-danger' if fraction_outside > 0 else 'text-success'
            status_icon = '❌' if fraction_outside > 0 else '✅'

            # Format value based on type
            if isinstance(value, dict):
                val_display = value.get('measured', str(value))
            elif isinstance(value, float):
                val_display = f"{value:.2f}"
            else:
                val_display = str(value)

            cod_table_rows += f"""
                        <tr>
                            <td>{axis}</td>
                            <td>{val_display}</td>
                            <td class="{status_class}">{status_icon} {fraction_outside:.0%}</td>
                        </tr>"""

    # Extract executive summary and key findings
    exec_summary = report_data.get('executive_summary', '')
    if not exec_summary:
        reports = result.get('reports', {})
        exec_summary = reports.get('executive_summary', {}).get(
            'scenario_overview', 'No summary available.')

    # Build key findings HTML
    findings_html = ""
    if isinstance(key_findings, dict):
        for category, finding in key_findings.items():
            findings_html += f"""
                <div class="col-md-6 mb-3">
                    <div class="metric-card h-100">
                        <h6 class="text-primary text-uppercase">{category}</h6>
                        <p class="mb-0">{finding}</p>
                    </div>
                </div>"""
    elif isinstance(key_findings, list):
        for i, finding in enumerate(key_findings):
            findings_html += f"""
                <div class="col-md-6 mb-3">
                    <div class="metric-card h-100">
                        <p class="mb-0">{finding}</p>
                    </div>
                </div>"""

    # Build issues HTML
    issues_html = ""
    for issue in issues:
        issues_html += f"<li class='mb-2'>{issue}</li>"

    # Build recommendations HTML
    recommendations_html = ""
    for rec in recommendations:
        recommendations_html += f"<li class='mb-2'>{rec}</li>"

    # Build scenario overview (representative windows)
    scenario_overview_html = ""
    display_windows = windows_with_images[:4]  # Show first 4 windows
    for window in display_windows:
        camera_img = window['images'].get('camera', '')
        bev_img = window['images'].get('bev_occupancy', '')
        scenario_overview_html += f"""
        <div class="col-md-6 col-lg-3 mb-4">
            <div class="metric-card h-100">
                <h6 class="text-primary mb-2">Window {window['id']}</h6>
                <div class="mb-2">
                    <img src="{camera_img}" alt="Window {window['id']} camera" 
                         style="width: 100%; border-radius: 8px; margin-bottom: 4px;">
                </div>
                <div class="mb-2">
                    <img src="{bev_img}" alt="Window {window['id']} BEV" 
                         style="width: 100%; border-radius: 8px;">
                </div>
            </div>
        </div>
        """

    # Critical axes
    critical_axes = compliance.get('critical_axes', [])
    critical_axes_html = ""
    for axis in critical_axes:
        critical_axes_html += f"<span class='badge bg-danger me-1'>{axis}</span>"
    if not critical_axes_html:
        critical_axes_html = "<span class='text-muted'>None</span>"

    # Data source info - check multiple locations in schema
    # New schema: agent_outputs.PerceptionAgent.data_source
    # Old schema: scenario_metadata.data_source
    agent_outputs = result.get('agent_outputs', {})
    perception_output = agent_outputs.get('PerceptionAgent', {})
    perception_data_source = perception_output.get('data_source', {})

    if isinstance(perception_data_source, dict) and perception_data_source.get('type'):
        # New schema format
        data_source = perception_data_source.get('type', 'unknown')
        data_source_confidence = perception_data_source.get('confidence', 0)
    else:
        # Fall back to old schema
        data_source = scenario_meta.get('data_source', 'unknown')
        data_source_classification = scenario_meta.get(
            'data_source_classification', {})
        data_source_confidence = data_source_classification.get(
            'confidence', 0)

    # Build data source display string (only if known)
    if data_source in ('simulated', 'sim'):
        data_source_display = f"Simulation ({data_source_confidence:.0%} confidence)" if data_source_confidence > 0 else "Simulation"
    elif data_source == 'real':
        data_source_display = f"Real Robot ({data_source_confidence:.0%} confidence)" if data_source_confidence > 0 else "Real Robot"
    else:
        data_source_display = None  # Will omit from display

    # Windows violated - handle both list and int
    windows_violated = region_metrics.get('windows_violated', [])
    if isinstance(windows_violated, list):
        windows_violated_count = len(windows_violated)
        windows_violated_display = ', '.join(
            windows_violated) if windows_violated else 'None'
    else:
        windows_violated_count = windows_violated
        windows_violated_display = str(windows_violated)

    # JSON filename for download
    json_filename = f"{scenario_name}_full_result.json"

    # Build the HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ODD Analysis Report: {scenario_name}</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <style>
        :root {{
            --status-color: {status['color']};
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --text-primary: #212529;
            --text-secondary: #6c757d;
            --border-color: #dee2e6;
        }}
        
        [data-theme="dark"] {{
            --bg-primary: #1a1d23;
            --bg-secondary: #25292f;
            --text-primary: #e9ecef;
            --text-secondary: #adb5bd;
            --border-color: #495057;
        }}
        
        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            transition: background-color 0.3s, color 0.3s;
        }}
        
        .hero-section {{
            background: linear-gradient(135deg, var(--status-color) 0%, color-mix(in srgb, var(--status-color) 70%, black) 100%);
            color: white;
            padding: 4rem 0;
            margin-bottom: 3rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .status-badge {{
            font-size: 2.5rem;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .metric-card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--status-color);
        }}
        
        .metric-label {{
            font-size: 0.875rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .chart-container {{
            background-color: var(--bg-secondary);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            min-height: 350px;
        }}
        
        .chart-container > div {{
            height: 320px;
            width: 100%;
        }}
        
        .compliance-table {{
            background-color: var(--bg-secondary);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .compliance-table table {{
            margin-bottom: 0;
        }}
        
        .dark-mode-toggle {{
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            z-index: 1000;
        }}
        
        .agent-badge {{
            font-size: 0.7rem;
            padding: 0.25rem 0.5rem;
        }}
        
        @media (max-width: 768px) {{
            .hero-section {{
                padding: 2rem 0;
            }}
            
            .status-badge {{
                font-size: 1.5rem;
            }}
        }}
    </style>
</head>
<body>

<!-- Dark Mode Toggle -->
<div class="dark-mode-toggle">
    <button class="btn btn-outline-secondary rounded-circle" onclick="toggleDarkMode()" title="Toggle dark mode">
        <span id="theme-icon">🌙</span>
    </button>
</div>

<!-- Hero Section -->
<div class="hero-section">
    <div class="container">
        <div class="mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
            <a href="../index.html" class="btn btn-outline-light">← Back to Home</a>
            <a href="{json_filename}" class="btn btn-outline-light btn-sm" download>📥 Download JSON</a>
        </div>
        <div class="row align-items-center">
            <div class="col-md-8">
                <h1 class="display-4">🤖 ODD Analysis Report</h1>
                <h2 class="h3">Scenario: {scenario_name}</h2>
                <p class="lead mb-0">Generated {timestamp}</p>
                <p class="mb-0">
                    <small>Pipeline v{analysis_meta.get('pipeline_version', 'N/A')} | 
                    {analysis_meta.get('total_tokens_used', 0):,} tokens | 
                    ${analysis_meta.get('estimated_cost_usd', 0):.4f} USD</small>
                </p>
            </div>
            <div class="col-md-4 text-end">
                <div class="status-badge">
                    {status['icon']} {status['label']}
                </div>
                <div class="mt-2">
                    <small>Confidence: {confidence:.0%}</small>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Key Metrics -->
<div class="container mb-5">
    <div class="row">
        <div class="col-md-3 col-sm-6">
            <div class="metric-card text-center">
                <div class="metric-value">{len(windows) if windows else scenario_meta.get('windows_analyzed', 0)}</div>
                <div class="metric-label">Windows Analyzed</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="metric-card text-center">
                <div class="metric-value">{windows_violated_count}</div>
                <div class="metric-label">Windows Violated</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="metric-card text-center">
                <div class="metric-value">{compliance.get('temporal_stability', 'N/A')}</div>
                <div class="metric-label">Temporal Stability</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="metric-card text-center">
                <div class="metric-value">{len(agent_executions)}</div>
                <div class="metric-label">Agents Executed</div>
            </div>
        </div>
    </div>
</div>

<!-- Executive Summary -->
<div class="container mb-5">
    <h2 class="mb-4">📋 Executive Summary</h2>
    <div class="metric-card">
        <p class="lead mb-3">{exec_summary}</p>
        <div class="mt-3">
            <strong>Critical Axes:</strong> {critical_axes_html}
        </div>
        <div class="mt-2">
            <strong>Rationale:</strong> {compliance.get('rationale', 'No rationale available.')}
        </div>
    </div>
</div>

<!-- Scenario Overview -->
<div class="container mb-5">
    <h2 class="mb-4">🎬 Scenario Overview</h2>
    <p class="text-muted mb-3">Representative windows from the analysis</p>
    <div class="row">
        {scenario_overview_html if scenario_overview_html else '<div class="col-12"><p class="text-muted">No window images available</p></div>'}
    </div>
</div>

<!-- Key Findings -->
<div class="container mb-5">
    <h2 class="mb-4">🔍 Key Findings</h2>
    <div class="row">
        {findings_html if findings_html else '<div class="col-12"><p class="text-muted">No findings available</p></div>'}
    </div>
</div>

<!-- COD Region Compliance -->
<div class="container mb-5">
    <h2 class="mb-4">📏 COD Region Analysis</h2>
    <div class="row">
        <div class="col-lg-6">
            <div class="chart-container">
                {charts['compliance_svg']}
            </div>
        </div>
        <div class="col-lg-6">
            <div class="compliance-table">
                <table class="table table-striped mb-0">
                    <thead class="table-dark">
                        <tr>
                            <th>ODD Axis</th>
                            <th>Measured Value</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {cod_table_rows if cod_table_rows else '<tr><td colspan="3" class="text-center text-muted">No COD data available</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Issues & Recommendations -->
<div class="container mb-5">
    <div class="row">
        <div class="col-md-6">
            <h2 class="mb-4">⚠️ Issues Identified</h2>
            <div class="metric-card">
                <ol class="mb-0">
                    {issues_html if issues_html else '<li class="text-muted">No issues identified</li>'}
                </ol>
            </div>
        </div>
        <div class="col-md-6">
            <h2 class="mb-4">💡 Recommendations</h2>
            <div class="metric-card">
                <ol class="mb-0">
                    {recommendations_html if recommendations_html else '<li class="text-muted">No recommendations</li>'}
                </ol>
            </div>
        </div>
    </div>
</div>

<!-- Analysis Costs -->
<div class="container mb-5">
    <h2 class="mb-4">💰 Analysis Costs</h2>
    <div class="row">
        <div class="col-lg-6">
            <div class="chart-container">
                {charts['cost_svg']}
            </div>
        </div>
        <div class="col-lg-6">
            <div class="metric-card">
                <h5>Cost Breakdown</h5>
                <table class="table table-sm">
                    <tr>
                        <td>Total Tokens</td>
                        <td class="text-end"><strong>{analysis_meta.get('total_tokens_used', 0):,}</strong></td>
                    </tr>
                    <tr>
                        <td>Input Tokens</td>
                        <td class="text-end">{analysis_meta.get('cost_breakdown', {}).get('total_input_tokens', 0):,}</td>
                    </tr>
                    <tr>
                        <td>Output Tokens</td>
                        <td class="text-end">{analysis_meta.get('cost_breakdown', {}).get('total_output_tokens', 0):,}</td>
                    </tr>
                    <tr class="table-primary">
                        <td><strong>Estimated Cost</strong></td>
                        <td class="text-end"><strong>${analysis_meta.get('estimated_cost_usd', 0):.4f} USD</strong></td>
                    </tr>
                    <tr>
                        <td>Duration</td>
                        <td class="text-end">{analysis_meta.get('analysis_duration_seconds', 0):.1f}s</td>
                    </tr>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Agent Executions -->
<div class="container mb-5">
    <h2 class="mb-4">🤖 Agent Executions</h2>
    <div class="compliance-table">
        <table class="table table-striped mb-0">
            <thead class="table-dark">
                <tr>
                    <th>Agent</th>
                    <th>Version</th>
                    <th>Model</th>
                    <th>Prompt Hash</th>
                    <th>Tokens</th>
                </tr>
            </thead>
            <tbody>
                {agent_version_rows}
            </tbody>
        </table>
    </div>
</div>

<!-- Footer -->
<footer class="container-fluid bg-light text-muted py-4 mt-5">
    <div class="container">
        <div class="row">
            <div class="col-md-4">
                <p class="mb-0">Generated by ODD Observer Analysis Pipeline</p>
                <p class="mb-0"><small>{timestamp}</small></p>
            </div>
            <div class="col-md-4 text-center">
                <p class="mb-0">Pipeline v{pipeline_meta.get('pipeline_version', 'N/A')}</p>
                <p class="mb-0"><small>{analysis_meta.get('analysis_timestamp', 'N/A')[:19] if analysis_meta.get('analysis_timestamp') else 'N/A'}</small></p>
            </div>
            <div class="col-md-4 text-end">
                {f'<p class="mb-0">Data Source: {data_source_display}</p>' if data_source_display else ''}
                <p class="mb-0"><small>Scenario: {scenario_name}</small></p>
            </div>
        </div>
    </div>
</footer>

<!-- Bootstrap JS -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<!-- Custom Scripts -->
<script>
    // Dark mode toggle
    function toggleDarkMode() {{
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', newTheme);
        document.getElementById('theme-icon').textContent = newTheme === 'dark' ? '☀️' : '🌙';
        localStorage.setItem('theme', newTheme);
        
    }}
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    document.getElementById('theme-icon').textContent = savedTheme === 'dark' ? '☀️' : '🌙';
</script>

</body>
</html>
"""

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # Copy JSON file to same directory for download link
    json_output = output_path.parent / json_filename
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"✅ Report generated: {output_path}")
    print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"📥 JSON exported: {json_output}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate interactive HTML report from ODD analysis (v2.0 - Phase 1.4.5 schema)")
    parser.add_argument('--input', type=Path, required=True,
                        help='Path to full_result.json')
    parser.add_argument('--scenario-dir', type=Path, required=True,
                        help='Path to scenario directory with images')
    parser.add_argument('--output', type=Path, default=Path('docs/reports/report.html'),
                        help='Output HTML file path')

    args = parser.parse_args()

    if not args.input.exists():
        print(f"❌ Input file not found: {args.input}")
        sys.exit(1)

    if not args.scenario_dir.exists():
        print(f"❌ Scenario directory not found: {args.scenario_dir}")
        sys.exit(1)

    print(f"📊 Loading analysis result from: {args.input}")
    result = load_analysis_result(args.input)

    print(f"🖼️  Loading images from: {args.scenario_dir}")

    print(f"🎨 Generating HTML report (v2.0 - Phase 1.4.5 schema)...")
    generate_html_report(result, args.scenario_dir, args.output)

    print()
    print("🎉 Report generation complete!")
    print(f"   Open in browser: file://{args.output.absolute()}")
    print(
        f"   Or serve locally: python -m http.server -d {args.output.parent}")


if __name__ == '__main__':
    main()
