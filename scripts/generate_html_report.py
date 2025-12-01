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
    """Extract compliance verdict from various schema formats."""
    compliance_data = {}

    # Start with report.compliance (from ReportAgent) as base
    report = result.get('report', {})
    if 'compliance' in report:
        compliance_data = dict(report['compliance'])
        # Normalize 'status' to 'verdict' for consistency
        if 'status' in compliance_data and 'verdict' not in compliance_data:
            compliance_data['verdict'] = compliance_data['status']

    # Try to get rationale from evaluator's compliance_verdict (more detailed)
    # Check artifacts first
    artifacts = result.get('artifacts', {})
    cod_artifact = artifacts.get('cod_construction.json', {})
    if 'compliance_verdict' in cod_artifact:
        eval_verdict = cod_artifact['compliance_verdict']
        if 'rationale' in eval_verdict and not compliance_data.get('rationale'):
            compliance_data['rationale'] = eval_verdict['rationale']
        if 'confidence' in eval_verdict and not compliance_data.get('confidence'):
            compliance_data['confidence'] = eval_verdict['confidence']
        if 'critical_axes' in eval_verdict and not compliance_data.get('critical_axes'):
            compliance_data['critical_axes'] = eval_verdict['critical_axes']

    # Check full_analysis for compliance_verdict
    fa = result.get('full_analysis', {})
    if 'compliance_verdict' in fa:
        eval_verdict = fa['compliance_verdict']
        if 'rationale' in eval_verdict and not compliance_data.get('rationale'):
            compliance_data['rationale'] = eval_verdict['rationale']
        if 'confidence' in eval_verdict and not compliance_data.get('confidence'):
            compliance_data['confidence'] = eval_verdict['confidence']

    # Check session_state for evaluator_output (may have markdown-wrapped JSON)
    session_state = result.get('session_state', {})
    eval_state = session_state.get(
        'evaluator_output', session_state.get('temp:evaluator_output', {}))
    if isinstance(eval_state, str):
        # Strip markdown code blocks if present
        eval_str = eval_state.strip()
        if eval_str.startswith('```'):
            # Remove ```json and trailing ```
            lines = eval_str.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            eval_str = '\n'.join(lines)
        try:
            eval_state = json.loads(eval_str)
        except:
            eval_state = {}
    if isinstance(eval_state, dict) and 'compliance_verdict' in eval_state:
        eval_verdict = eval_state['compliance_verdict']
        if 'rationale' in eval_verdict and not compliance_data.get('rationale'):
            compliance_data['rationale'] = eval_verdict['rationale']
        if 'confidence' in eval_verdict and not compliance_data.get('confidence'):
            compliance_data['confidence'] = eval_verdict['confidence']

    if compliance_data:
        return compliance_data

    # Fallback to Phase 1.4.5 schema: compliance.verdict (nested verdict object)
    compliance = result.get('compliance', {})
    if 'verdict' in compliance:
        verdict_obj = compliance['verdict']
        if isinstance(verdict_obj, dict) and 'verdict' in verdict_obj:
            return verdict_obj
        return {'verdict': verdict_obj}

    # Try agent outputs
    agent_outputs = result.get('agent_outputs', {})
    eval_output = agent_outputs.get('EvaluatorAgent', {})
    if 'compliance_verdict' in eval_output:
        return eval_output['compliance_verdict']

    # Old schema fallback
    return fa.get('odd_compliance', {})
    return fa.get('odd_compliance', {})


def get_cod_region(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract COD region from various schema formats."""
    # Try Phase 1.6 schema: artifacts.cod_construction.json
    artifacts = result.get('artifacts', {})
    cod_artifact = artifacts.get('cod_construction.json', {})
    if 'cod_region' in cod_artifact:
        return cod_artifact['cod_region']

    # Try Phase 1.4.5 schema: compliance.cod_region
    compliance = result.get('compliance', {})
    if 'cod_region' in compliance:
        return compliance['cod_region']

    # Try full_analysis schema
    fa = result.get('full_analysis', {})
    if 'cod_region' in fa:
        return fa['cod_region']

    agent_outputs = result.get('agent_outputs', {})
    eval_output = agent_outputs.get('EvaluatorAgent', {})
    return eval_output.get('cod_region', {})


def get_region_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract region metrics from various schema formats."""
    # Try Phase 1.6 schema: artifacts.cod_construction.json
    artifacts = result.get('artifacts', {})
    cod_artifact = artifacts.get('cod_construction.json', {})
    if 'region_metrics' in cod_artifact:
        return cod_artifact['region_metrics']

    # Try Phase 1.4.5 schema: compliance.region_metrics
    compliance = result.get('compliance', {})
    if 'region_metrics' in compliance:
        return compliance['region_metrics']

    # Try full_analysis schema
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


def get_motion_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract motion analysis data from artifacts."""
    artifacts = result.get('artifacts', {})
    motion_artifact = artifacts.get('motion_output.json', {})

    # Also try to get summary from session_state
    session_state = result.get('session_state', {})
    motion_summary_str = session_state.get('motion_summary', '')
    motion_summary = {}
    if isinstance(motion_summary_str, str) and motion_summary_str.strip():
        try:
            motion_summary = json.loads(motion_summary_str)
        except:
            pass

    return {
        'per_window': motion_artifact.get('per_window', []),
        'windows_analyzed': motion_artifact.get('windows_analyzed', 0),
        'summary': motion_summary.get('summary', {}),
        'temporal_analysis': motion_summary.get('temporal_analysis', {}),
        'data_availability_summary': motion_summary.get('data_availability_summary', {}),
        'issues': motion_summary.get('issues', []),
    }


def get_collision_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract collision analysis data from artifacts."""
    artifacts = result.get('artifacts', {})
    collision_artifact = artifacts.get('collision_output.json', {})

    # Also try to get summary from session_state
    session_state = result.get('session_state', {})
    collision_summary_str = session_state.get('collision_summary', '')
    collision_summary = {}
    if isinstance(collision_summary_str, str) and collision_summary_str.strip():
        try:
            collision_summary = json.loads(collision_summary_str)
        except:
            pass

    return {
        'per_window': collision_artifact.get('per_window', []),
        'windows_analyzed': collision_artifact.get('windows_analyzed', 0),
        'collision_stats': collision_artifact.get('collision_stats', {}),
        'summary': collision_summary.get('summary', {}),
        'temporal_analysis': collision_summary.get('temporal_analysis', {}),
        'data_availability_summary': collision_summary.get('data_availability_summary', {}),
        'issues': collision_summary.get('issues', []),
        'advisory_note': collision_summary.get('advisory_note', ''),
    }


def get_perception_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract perception analysis data from artifacts."""
    artifacts = result.get('artifacts', {})
    perception_artifact = artifacts.get('perception_output.json', {})

    # Also try to get summary from session_state
    session_state = result.get('session_state', {})
    perception_summary_str = session_state.get('perception_summary', '')
    perception_summary = {}
    if isinstance(perception_summary_str, str) and perception_summary_str.strip():
        try:
            perception_summary = json.loads(perception_summary_str)
        except:
            pass

    return {
        'per_window': perception_artifact.get('per_window', []),
        'windows_analyzed': perception_artifact.get('windows_analyzed', 0),
        'tool_version': perception_artifact.get('tool_version', 'unknown'),
        'summary': perception_summary.get('summary', {}),
        'temporal_analysis': perception_summary.get('temporal_analysis', {}),
        'actor_detection': perception_summary.get('actor_detection', {}),
        'odd_critical': perception_summary.get('odd_critical', {}),
    }


def get_key_findings(result: Dict[str, Any]) -> Dict[str, str]:
    """Extract key findings from various schema formats."""
    # Try Phase 1.4.5 schema: summary_insights.key_observations
    summary_insights = result.get('summary_insights', {})
    if 'key_observations' in summary_insights:
        obs = summary_insights['key_observations']
        if isinstance(obs, list):
            return {'observations': obs}
        return obs

    # Try executive_summary.key_observations
    exec_summary = result.get('executive_summary', {})
    if 'key_observations' in exec_summary:
        obs = exec_summary['key_observations']
        if isinstance(obs, list):
            return {'observations': obs}
        return obs

    report_data = get_report_data(result)
    findings = report_data.get('key_findings', {})

    if isinstance(findings, dict):
        return findings
    elif isinstance(findings, list):
        return {'findings': findings}
    return {}


def get_issues_and_recommendations(result: Dict[str, Any]) -> tuple:
    """Extract issues and recommendations from various schema formats."""
    # Try Phase 1.4.5 schema
    compliance = result.get('compliance', {})
    exec_summary = result.get('executive_summary', {})

    # Issues from key_concerns or data_quality warnings
    issues = compliance.get('key_concerns', [])
    if not issues:
        data_quality = exec_summary.get('data_quality', {})
        issues = data_quality.get('warnings', []) + \
            data_quality.get('anomalies', [])

    # Recommendations from executive_summary
    recommendations = exec_summary.get('recommendations', [])

    # Fallback to old schema
    if not issues and not recommendations:
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
                # Skip "cam_" and go up to "_w"
                prefix = name[4:name.rfind('_w')]
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


def generate_svg_bar_chart(labels: list, values: list, max_val: float = None,
                           title: str = "Bar Chart", color: str = "#667eea",
                           unit: str = "") -> str:
    """Generate an inline SVG horizontal bar chart."""
    if not labels or not values:
        return '<div class="text-muted text-center p-4">No data available</div>'

    import math

    width = 450
    bar_height = 25
    bar_gap = 8
    label_width = 120
    value_width = 60
    chart_start = label_width + 10
    chart_width = width - chart_start - value_width - 10

    n = len(labels)
    height = n * (bar_height + bar_gap) + 60  # Extra for title

    if max_val is None:
        max_val = max(values) if values else 1
    if max_val == 0:
        max_val = 1

    # Title
    svg = f'<text x="{width/2}" y="20" text-anchor="middle" font-size="14" font-weight="bold" fill="var(--text-primary)">{title}</text>'

    y_offset = 45
    for i, (label, value) in enumerate(zip(labels, values)):
        y = y_offset + i * (bar_height + bar_gap)
        bar_width = (value / max_val) * chart_width

        # Label
        short_label = label[:15] + '..' if len(label) > 15 else label
        svg += f'<text x="{label_width}" y="{y + bar_height/2 + 4}" text-anchor="end" font-size="11" fill="var(--text-secondary)">{short_label}</text>'

        # Bar background
        svg += f'<rect x="{chart_start}" y="{y}" width="{chart_width}" height="{bar_height}" fill="var(--border-color)" opacity="0.3" rx="3"/>'

        # Bar fill
        if bar_width > 0:
            svg += f'<rect x="{chart_start}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="3"/>'

        # Value label
        val_display = f"{value:.2f}{unit}" if isinstance(
            value, float) else f"{value}{unit}"
        svg += f'<text x="{chart_start + chart_width + 5}" y="{y + bar_height/2 + 4}" font-size="11" fill="var(--text-primary)">{val_display}</text>'

    return f'''<svg viewBox="0 0 {width} {height}" class="svg-chart" style="width:100%;max-width:{width}px;height:auto;">
        {svg}
    </svg>'''


def generate_svg_line_chart(
    labels: List[str],
    values: List[float],
    max_val: float = None,
    title: str = "",
    color: str = "#667eea",
    unit: str = "",
    show_area: bool = True
) -> str:
    """Generate an SVG line chart for time-series data."""
    if not values or all(v == 0 for v in values):
        return f'<div class="text-muted text-center p-4">No {title.lower()} data</div>'

    n_points = len(values)

    # Chart dimensions
    width = 450
    height = 180
    margin_left = 50
    margin_right = 20
    margin_top = 35
    margin_bottom = 40

    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom

    # Calculate scales
    if max_val is None:
        max_val = max(values) * 1.2 if max(values) > 0 else 1
    min_val = 0

    # Generate points
    points = []
    for i, val in enumerate(values):
        x = margin_left + (i / max(n_points - 1, 1)) * chart_width
        y = margin_top + chart_height - (val / max_val) * chart_height
        points.append((x, y))

    # Build path
    path_d = f"M {points[0][0]:.1f} {points[0][1]:.1f}"
    for x, y in points[1:]:
        path_d += f" L {x:.1f} {y:.1f}"

    # Area fill path (closed polygon)
    area_d = path_d + \
        f" L {points[-1][0]:.1f} {margin_top + chart_height} L {points[0][0]:.1f} {margin_top + chart_height} Z"

    svg = f'''<svg viewBox="0 0 {width} {height}" class="svg-chart" style="width:100%;height:auto;">
        <text x="{width/2}" y="20" text-anchor="middle" font-size="14" font-weight="bold" fill="var(--text-primary)">{title}</text>
        
        <!-- Grid lines -->
        <line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + chart_height}" stroke="var(--border-color)" stroke-width="1"/>
        <line x1="{margin_left}" y1="{margin_top + chart_height}" x2="{margin_left + chart_width}" y2="{margin_top + chart_height}" stroke="var(--border-color)" stroke-width="1"/>
        '''

    # Add horizontal grid lines and y-axis labels
    for i in range(5):
        y = margin_top + (i / 4) * chart_height
        val = max_val * (1 - i / 4)
        svg += f'''
        <line x1="{margin_left}" y1="{y:.1f}" x2="{margin_left + chart_width}" y2="{y:.1f}" stroke="var(--border-color)" stroke-width="0.5" opacity="0.5"/>
        <text x="{margin_left - 5}" y="{y + 4:.1f}" text-anchor="end" font-size="10" fill="var(--text-secondary)">{val:.2f}</text>'''

    # Area fill (gradient effect)
    if show_area:
        svg += f'''
        <defs>
            <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:{color};stop-opacity:0.3"/>
                <stop offset="100%" style="stop-color:{color};stop-opacity:0.05"/>
            </linearGradient>
        </defs>
        <path d="{area_d}" fill="url(#areaGradient)"/>'''

    # Line
    svg += f'''
        <path d="{path_d}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'''

    # Data points
    for i, (x, y) in enumerate(points):
        val = values[i]
        svg += f'''
        <circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}" stroke="white" stroke-width="1.5"/>'''

    # X-axis labels (show subset if too many)
    if n_points <= 8:
        label_indices = range(n_points)
    else:
        # Show first, last, and evenly spaced
        step = max(1, n_points // 6)
        label_indices = list(range(0, n_points, step))
        if n_points - 1 not in label_indices:
            label_indices.append(n_points - 1)

    for i in label_indices:
        x = margin_left + (i / max(n_points - 1, 1)) * chart_width
        svg += f'''
        <text x="{x:.1f}" y="{height - 10}" text-anchor="middle" font-size="10" fill="var(--text-secondary)">{labels[i]}</text>'''

    # Unit label
    svg += f'''
        <text x="{margin_left - 5}" y="{margin_top - 8}" text-anchor="end" font-size="9" fill="var(--text-secondary)">{unit}</text>
    </svg>'''

    return svg


def generate_motion_charts(motion_data: Dict[str, Any]) -> Dict[str, str]:
    """Generate SVG charts for motion analysis section."""
    charts = {}

    per_window = motion_data.get('per_window', [])

    if not per_window:
        charts['trajectory_svg'] = '<div class="text-muted text-center p-4">No motion data available</div>'
        charts['speed_svg'] = '<div class="text-muted text-center p-4">No motion data available</div>'
        return charts

    # Trajectory metrics chart (displacement vs path length)
    window_ids = [w.get('window_id', str(i)) for i, w in enumerate(per_window)]
    displacements = []
    path_lengths = []
    efficiencies = []

    for w in per_window:
        traj = w.get('trajectory_metrics', {})
        displacements.append(traj.get('displacement_m', 0))
        path_lengths.append(traj.get('path_length_m', 0))
        efficiencies.append(traj.get('efficiency', 0))

    # Speed metrics chart
    peak_speeds = []
    avg_speeds = []

    for w in per_window:
        speed = w.get('speed_metrics', {})
        peak_speeds.append(speed.get('peak_mps', 0))
        avg_speeds.append(speed.get('avg_mps', 0))

    # Generate speed line chart
    if any(peak_speeds):
        max_speed = max(peak_speeds) if peak_speeds else 1
        # Use compact labels - just window index number
        compact_labels = [str(int(wid)) if wid.isdigit(
        ) else wid.lstrip('0') or '0' for wid in window_ids]
        charts['speed_svg'] = generate_svg_line_chart(
            compact_labels,
            peak_speeds,
            max_val=max(max_speed * 1.2, 0.1),
            title="Peak Speed per Window",
            color="#28a745",
            unit="m/s"
        )
    else:
        charts['speed_svg'] = '<div class="text-muted text-center p-4">No speed data available</div>'

    return charts


def generate_collision_charts(collision_data: Dict[str, Any]) -> Dict[str, str]:
    """Generate SVG charts for collision analysis section."""
    charts = {}

    per_window = collision_data.get('per_window', [])

    if not per_window:
        charts['proximity_svg'] = '<div class="text-muted text-center p-4">No collision data available</div>'
        return charts

    # Proximity over windows
    window_ids = [w.get('window_id', str(i)) for i, w in enumerate(per_window)]
    proximities = [w.get('proximity_estimate_m', 0) for w in per_window]

    if any(proximities):
        max_prox = max(proximities) if proximities else 3
        # Use compact labels - just window index number
        compact_labels = [str(int(wid)) if wid.isdigit(
        ) else wid.lstrip('0') or '0' for wid in window_ids]
        charts['proximity_svg'] = generate_svg_line_chart(
            compact_labels,
            proximities,
            max_val=max(max_prox * 1.2, 3),
            title="Proximity to Obstacles per Window",
            color="#17a2b8",
            unit="m"
        )
    else:
        charts['proximity_svg'] = '<div class="text-muted text-center p-4">No proximity data available</div>'

    return charts


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

    # Motion analysis charts
    motion_data = get_motion_data(result)
    motion_charts = generate_motion_charts(motion_data)
    charts.update(motion_charts)

    # Collision analysis charts
    collision_data = get_collision_data(result)
    collision_charts = generate_collision_charts(collision_data)
    charts.update(collision_charts)

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
    windows, image_scenario_name = discover_windows(
        scenario_dir, image_scenario_name)

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

    # Extract motion and collision data for new sections
    motion_data = get_motion_data(result)
    collision_data = get_collision_data(result)

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

            # Format value based on type - handle Phase 1.4.5 COD format
            if isinstance(value, dict):
                val_type = value.get('type', '')
                if val_type == 'range':
                    # Range type: show min-max or single value
                    min_val = value.get('min', 0)
                    max_val = value.get('max', 0)
                    if min_val == max_val:
                        val_display = f"{min_val:.2f}" if isinstance(
                            min_val, float) else str(min_val)
                    else:
                        val_display = f"{min_val:.2f} - {max_val:.2f}"
                elif val_type == 'enum':
                    # Enum type: show the detected values
                    enum_vals = {k: v for k, v in value.items() if k != 'type'}
                    if len(enum_vals) == 1:
                        val_display = list(enum_vals.keys())[
                            0].replace('_', ' ').title()
                    else:
                        # Multiple values: show as comma-separated
                        val_display = ', '.join(
                            k.replace('_', ' ').title() for k in enum_vals.keys())
                elif 'measured' in value:
                    val_display = value.get('measured', str(value))
                else:
                    val_display = str(value)
            elif isinstance(value, float):
                val_display = f"{value:.2f}"
            else:
                val_display = str(value)

            cod_table_rows += f"""
                        <tr>
                            <td>{axis.replace('_', ' ').title()}</td>
                            <td>{val_display}</td>
                            <td class="{status_class}">{status_icon} {fraction_outside:.0%}</td>
                        </tr>"""

    # Extract executive summary - try multiple schema locations
    exec_summary = ""

    # Try report.executive_summary (v14 schema - direct string)
    report_exec = report_data.get('executive_summary', '')
    if isinstance(report_exec, str) and report_exec:
        exec_summary = report_exec
    elif isinstance(report_exec, dict):
        exec_summary = report_exec.get('scenario_overview', '')

    # Fallback: compliance.summary (technical rationale)
    if not exec_summary:
        exec_summary = compliance.get(
            'summary', compliance.get('rationale', ''))

    # Final fallback
    if not exec_summary:
        exec_summary = "No summary available."

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

    # Build motion analysis HTML
    motion_summary = motion_data.get('summary', {})
    motion_temporal = motion_data.get('temporal_analysis', {})
    motion_per_window = motion_data.get('per_window', [])
    motion_data_avail = motion_data.get('data_availability_summary', {})

    # Motion state badges per window - with collapsible for many windows
    MAX_VISIBLE_BADGES = 6
    motion_states_visible = []
    motion_states_hidden = []

    for i, w in enumerate(motion_per_window):
        state = w.get('motion_state', 'unknown')
        state_colors = {
            'stationary': 'bg-secondary',
            'moving': 'bg-success',
            'complex': 'bg-warning',
            'rotating': 'bg-info',
            'unknown': 'bg-light text-dark'
        }
        badge_class = state_colors.get(state, 'bg-light text-dark')
        badge_html = f'<span class="badge {badge_class} me-1 mb-1">W{w.get("window_id", "?")}: {state}</span>'

        if i < MAX_VISIBLE_BADGES:
            motion_states_visible.append(badge_html)
        else:
            motion_states_hidden.append(badge_html)

    # Build motion states HTML with optional collapse
    if motion_states_hidden:
        motion_states_html = ''.join(motion_states_visible)
        motion_states_html += f'''
            <a class="btn btn-sm btn-outline-secondary py-0 px-2" data-bs-toggle="collapse" href="#motionStatesCollapse" role="button" aria-expanded="false">
                +{len(motion_states_hidden)} more
            </a>
            <div class="collapse mt-1" id="motionStatesCollapse">
                {''.join(motion_states_hidden)}
            </div>'''
    else:
        motion_states_html = ''.join(
            motion_states_visible) if motion_states_visible else ''

    # Data availability badges
    motion_avail_html = ""
    if motion_data_avail:
        if motion_data_avail.get('imu_available'):
            motion_avail_html += '<span class="badge bg-success me-1">IMU ✓</span>'
        else:
            motion_avail_html += '<span class="badge bg-warning me-1">IMU (derived)</span>'
        if motion_data_avail.get('position_available'):
            motion_avail_html += '<span class="badge bg-success me-1">Position ✓</span>'

    # Motion metrics summary
    max_speed = motion_summary.get('max_speed_mps', 0)
    total_displacement = motion_summary.get('total_displacement_m', 0)
    avg_efficiency = motion_summary.get('avg_trajectory_efficiency', 0)
    max_pitch = motion_summary.get('max_pitch_deg', 0)
    max_roll = motion_summary.get('max_roll_deg', 0)

    # Build trajectory details card HTML (collapsible per-window breakdown)
    trajectory_pattern = motion_temporal.get('trajectory_pattern', 'unknown')
    MAX_VISIBLE_TRAJECTORY = 5

    trajectory_rows_visible = []
    trajectory_rows_hidden = []

    # Header row for trajectory details
    trajectory_header = '''
        <div class="d-flex justify-content-between align-items-center py-2 border-bottom bg-light rounded-top px-2 mb-1">
            <span class="fw-bold text-muted small" style="min-width: 60px;">Window</span>
            <span class="fw-bold text-muted small text-center flex-grow-1">Displacement → Path Length</span>
            <span class="fw-bold text-muted small" style="min-width: 70px; text-align: right;">Efficiency</span>
        </div>'''

    for i, w in enumerate(motion_per_window):
        traj = w.get('trajectory_metrics', {})
        displacement = traj.get('displacement_m', 0)
        path_length = traj.get('path_length_m', 0)
        efficiency = traj.get('efficiency', 0)
        window_id = w.get('window_id', '?')

        # Color code efficiency
        if efficiency >= 0.9:
            eff_class = 'text-success'
        elif efficiency >= 0.7:
            eff_class = 'text-warning'
        else:
            eff_class = 'text-danger'

        row_html = f'''
            <div class="d-flex justify-content-between align-items-center py-1 border-bottom px-2">
                <span class="text-muted" style="min-width: 60px;">W{window_id}</span>
                <span class="text-center flex-grow-1">{displacement:.3f}m → {path_length:.3f}m</span>
                <span class="{eff_class} fw-bold" style="min-width: 70px; text-align: right;">{efficiency:.0%}</span>
            </div>'''

        if i < MAX_VISIBLE_TRAJECTORY:
            trajectory_rows_visible.append(row_html)
        else:
            trajectory_rows_hidden.append(row_html)

    # Build trajectory details HTML (with header)
    if trajectory_rows_visible:
        trajectory_details_html = trajectory_header + \
            ''.join(trajectory_rows_visible)
        if trajectory_rows_hidden:
            trajectory_details_html += f'''
                <div class="collapse" id="trajectoryCollapse">
                    {''.join(trajectory_rows_hidden)}
                </div>
                <div class="text-center mt-2">
                    <a class="btn btn-sm btn-outline-primary" data-bs-toggle="collapse" href="#trajectoryCollapse" role="button" aria-expanded="false">
                        <span class="when-collapsed">Show {len(trajectory_rows_hidden)} more windows</span>
                        <span class="when-expanded">Show less</span>
                    </a>
                </div>'''
    else:
        trajectory_details_html = '<p class="text-muted">No trajectory data</p>'

    # Build collision analysis HTML
    collision_summary = collision_data.get('summary', {})
    collision_temporal = collision_data.get('temporal_analysis', {})
    collision_per_window = collision_data.get('per_window', [])
    collision_data_avail = collision_data.get('data_availability_summary', {})

    # Compute collision stats from per-window data if summary is empty (new schema)
    collision_stats = collision_data.get('collision_stats', {})
    if not collision_summary and collision_per_window:
        # Compute from per-window data
        sudden_stops = sum(1 for w in collision_per_window
                           if w.get('collision_signatures', {}).get('sudden_stop', False))
        collisions = sum(1 for w in collision_per_window if w.get(
            'collision_detected', False))
        proximities = [w.get('proximity_estimate_m', 999)
                       for w in collision_per_window]
        speed_drops = [w.get('collision_signatures', {}).get(
            'speed_drop_mps', 0) for w in collision_per_window]
        collision_summary = {
            'sudden_stop_count': sudden_stops,
            'total_collisions_detected': collision_stats.get('collisions_detected', collisions),
            'min_proximity_m': min(proximities) if proximities else 0,
            'max_speed_drop_mps': max(speed_drops) if speed_drops else 0,
        }
        # Extract data availability from first window
        if collision_per_window:
            first_avail = collision_per_window[0].get('data_availability', {})
            collision_data_avail = {
                'imu_available': first_avail.get('acceleration') == 'imu',
                'position_available': first_avail.get('position') == 'available',
                'bev_available': first_avail.get('bev_proximity') == 'computed',
            }

    # Risk band badges per window - with collapsible for many windows
    risk_bands_visible = []
    risk_bands_hidden = []

    for i, w in enumerate(collision_per_window):
        risk = w.get('collision_risk_band', 'UNKNOWN')
        risk_colors = {
            'LOW': 'bg-success',
            'MEDIUM': 'bg-warning',
            'HIGH': 'bg-danger',
            'UNKNOWN': 'bg-secondary'
        }
        badge_class = risk_colors.get(risk, 'bg-secondary')
        badge_html = f'<span class="badge {badge_class} me-1 mb-1">W{w.get("window_id", "?")}: {risk}</span>'

        if i < MAX_VISIBLE_BADGES:
            risk_bands_visible.append(badge_html)
        else:
            risk_bands_hidden.append(badge_html)

    # Build risk bands HTML with optional collapse
    if risk_bands_hidden:
        risk_bands_html = ''.join(risk_bands_visible)
        risk_bands_html += f'''
            <a class="btn btn-sm btn-outline-secondary py-0 px-2" data-bs-toggle="collapse" href="#riskBandsCollapse" role="button" aria-expanded="false">
                +{len(risk_bands_hidden)} more
            </a>
            <div class="collapse mt-1" id="riskBandsCollapse">
                {''.join(risk_bands_hidden)}
            </div>'''
    else:
        risk_bands_html = ''.join(
            risk_bands_visible) if risk_bands_visible else ''

    # Collision signatures summary
    sudden_stop_count = collision_summary.get('sudden_stop_count', 0)
    total_collisions = collision_summary.get('total_collisions_detected', 0)
    min_proximity = collision_summary.get('min_proximity_m', 0)
    avg_proximity = collision_summary.get('avg_proximity_m', 0)
    max_speed_drop = collision_summary.get('max_speed_drop_mps', 0)

    # Data availability badges for collision
    collision_avail_html = ""
    if collision_data_avail:
        if collision_data_avail.get('imu_available'):
            collision_avail_html += '<span class="badge bg-success me-1">IMU ✓</span>'
        if collision_data_avail.get('position_available'):
            collision_avail_html += '<span class="badge bg-success me-1">Position ✓</span>'
        if collision_data_avail.get('bev_available'):
            collision_avail_html += '<span class="badge bg-success me-1">BEV ✓</span>'

    # Build scenario overview (representative windows)
    total_windows = len(windows)

    # Sample windows evenly for display (use windows_with_images which is already sampled)
    # But re-sample from the full list to get true even spacing
    MAX_DISPLAY_CARDS = 4
    if total_windows <= MAX_DISPLAY_CARDS:
        display_window_ids = windows
    else:
        # True even spacing: first, last, and evenly distributed middle
        step = (total_windows - 1) / (MAX_DISPLAY_CARDS - 1)
        display_window_ids = [windows[int(round(i * step))]
                              for i in range(MAX_DISPLAY_CARDS)]

    # Get images for display windows
    display_windows = [
        w for w in windows_with_images if w['id'] in display_window_ids]
    # If some weren't in windows_with_images, try to load them
    if len(display_windows) < len(display_window_ids):
        for wid in display_window_ids:
            if wid not in [w['id'] for w in display_windows]:
                images = find_window_images(
                    scenario_dir, wid, image_scenario_name)
                if images:
                    display_windows.append({'id': wid, 'images': images})
        # Sort by window id to maintain order
        display_windows.sort(key=lambda w: windows.index(
            w['id']) if w['id'] in windows else 999)

    # Extract environment info from per-window data or artifacts
    per_window_data = result.get('per_window_data', [])

    # Try artifacts for per-window data (current schema: perception_output.json)
    if not per_window_data:
        artifacts = result.get('artifacts', {})
        perception_artifact = artifacts.get('perception_output.json', {})
        if perception_artifact.get('per_window'):
            per_window_data = perception_artifact['per_window']

    # Extract categorical values across ALL windows to detect transitions
    def get_categorical_display(per_window_data, field_name, fallback="Unknown"):
        """Get display string for categorical field, showing transitions if values vary."""
        if not per_window_data:
            return fallback

        values = []
        for window in per_window_data:
            measurements = window.get(
                'odd_measurements', window.get('measurements', window.get('observations', {})))
            val = measurements.get(field_name)
            if val:
                values.append(val)

        if not values:
            return fallback

        # Preserve order, remove duplicates
        unique_values = list(dict.fromkeys(values))

        if len(unique_values) == 1:
            return unique_values[0]
        elif len(unique_values) == 2:
            return f"{unique_values[0]} → {unique_values[1]}"
        else:
            return ", ".join(unique_values[:3]) + ("..." if len(unique_values) > 3 else "")

    # Get terrain_type (surface) and environment from per-window data
    surface_type = get_categorical_display(
        per_window_data, 'terrain_type', 'Unknown')

    # For environment, try report.scenario_metadata first (agent-synthesized),
    # then fall back to per-window detection
    report_data = result.get('report', {})
    scenario_meta_env = report_data.get(
        'scenario_metadata', {}).get('environment')
    if scenario_meta_env and scenario_meta_env != 'Unknown':
        environment_type = scenario_meta_env
    else:
        # No environment_type in per-window data currently, use scenario_metadata
        environment_type = scenario_meta.get('environment', 'Unknown')

    # Data source info - check multiple locations in schema
    # Current schema: artifacts.perception_output.json.per_window[0].data_source
    # Fallback: agent_outputs.PerceptionAgent.data_source
    artifacts = result.get('artifacts', {})
    perception_artifact = artifacts.get('perception_output.json', {})
    # Try per_window data_source first
    perception_data_source = {}
    per_window_list = perception_artifact.get('per_window', [])
    if per_window_list and len(per_window_list) > 0:
        perception_data_source = per_window_list[0].get('data_source', {})
    if not perception_data_source:
        perception_data_source = perception_artifact.get('data_source', {})

    if not perception_data_source:
        agent_outputs_ds = result.get('agent_outputs', {})
        perception_output_ds = agent_outputs_ds.get('PerceptionAgent', {})
        perception_data_source = perception_output_ds.get('data_source', {})

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

    # Build data source display string
    if data_source in ('simulated', 'sim'):
        data_source_display = f"Simulation ({data_source_confidence:.0%} confidence)" if data_source_confidence > 0 else "Simulation"
    elif data_source == 'real':
        data_source_display = f"Real Robot ({data_source_confidence:.0%} confidence)" if data_source_confidence > 0 else "Real Robot"
    else:
        data_source_display = data_source.title() if data_source else "Unknown"

    # Build visual timeline showing all windows
    timeline_dots_html = ""
    for i, wid in enumerate(windows):
        is_displayed = wid in [w['id'] for w in display_windows]
        dot_class = "timeline-dot-active" if is_displayed else "timeline-dot"
        tooltip = f"Window {wid}" + (" (shown below)" if is_displayed else "")
        timeline_dots_html += f'<div class="{dot_class}" title="{tooltip}"></div>'

    # Scenario context card
    scenario_context_html = f"""
    <div class="row mb-4">
        <div class="col-12">
            <div class="metric-card">
                <div class="row align-items-center">
                    <div class="col-md-3 text-center border-end">
                        <div class="metric-value">{total_windows}</div>
                        <div class="metric-label">Total Windows</div>
                    </div>
                    <div class="col-md-3 text-center border-end">
                        <div class="metric-label">Detected Environment</div>
                        <div class="h5 mb-1 fw-normal">{environment_type.replace('_', ' ').title()}</div>
                    </div>
                    <div class="col-md-3 text-center border-end">
                        <div class="metric-label">Detected Surface</div>
                        <div class="h5 mb-1 fw-normal">{surface_type.replace('_', ' ').title()}</div>
                    </div>
                    <div class="col-md-3 text-center">
                        <div class="metric-label">Detected Data Source</div>
                        <div class="h5 mb-1 fw-normal">{data_source_display}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

    # Timeline visualization
    timeline_html = ""
    if total_windows > 1:
        timeline_html = f"""
    <div class="row mb-4">
        <div class="col-12">
            <div class="metric-card">
                <h6 class="text-primary mb-3">📊 Window Timeline</h6>
                <p class="text-muted small mb-2">Showing {len(display_windows)} of {total_windows} windows (highlighted = displayed below)</p>
                <div class="timeline-container">
                    <div class="timeline-track">
                        {timeline_dots_html}
                    </div>
                    <div class="timeline-labels d-flex justify-content-between mt-2">
                        <small class="text-muted">Start (W{windows[0] if windows else '?'})</small>
                        <small class="text-muted">End (W{windows[-1] if windows else '?'})</small>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

    # Build window cards
    scenario_overview_html = scenario_context_html + timeline_html

    for window in display_windows:
        camera_img = window['images'].get('camera', '')
        bev_img = window['images'].get('bev_occupancy', '')
        window_idx = windows.index(
            window['id']) + 1 if window['id'] in windows else '?'
        scenario_overview_html += f"""
        <div class="col-md-6 col-lg-3 mb-4">
            <div class="metric-card h-100">
                <h6 class="text-primary mb-2">Window {window['id']} <small class="text-muted">({window_idx}/{total_windows})</small></h6>
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
        
        /* Timeline visualization styles */
        .timeline-container {{
            padding: 0.5rem 0;
        }}
        
        .timeline-track {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(90deg, var(--border-color) 0%, var(--border-color) 100%);
            background-size: 100% 3px;
            background-position: center;
            background-repeat: no-repeat;
            padding: 0.5rem 0;
            gap: 2px;
        }}
        
        .timeline-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: var(--border-color);
            border: 2px solid var(--bg-secondary);
            transition: transform 0.2s;
            cursor: pointer;
            flex-shrink: 0;
        }}
        
        .timeline-dot:hover {{
            transform: scale(1.3);
        }}
        
        .timeline-dot-active {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background-color: var(--status-color);
            border: 2px solid var(--bg-secondary);
            box-shadow: 0 0 6px var(--status-color);
            cursor: pointer;
            flex-shrink: 0;
        }}
        
        .timeline-dot-active:hover {{
            transform: scale(1.2);
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
        
        .chart-container-compact {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.5rem;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .chart-container-compact svg {{
            width: 100%;
            height: auto;
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
        
        /* Collapsible section styles */
        .when-collapsed {{
            display: inline;
        }}
        .when-expanded {{
            display: none;
        }}
        [aria-expanded="true"] .when-collapsed {{
            display: none;
        }}
        [aria-expanded="true"] .when-expanded {{
            display: inline;
        }}
        
        .window-badge {{
            font-size: 0.75rem;
            padding: 0.35em 0.65em;
        }}
        
        .trajectory-row {{
            transition: background-color 0.2s;
        }}
        .trajectory-row:hover {{
            background-color: var(--bg-secondary);
        }}
        
        .risk-band-badge {{
            font-size: 0.75rem;
            padding: 0.35em 0.65em;
            min-width: 60px;
            text-align: center;
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
                <div class="metric-value">{region_metrics.get('region_distance', 0.0):.2f}</div>
                <div class="metric-label">Region Distance</div>
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

<!-- Motion Analysis Section -->
<div class="container mb-5">
    <h2 class="mb-4">🏃 Motion Analysis</h2>
    <div class="row">
        <div class="col-lg-6">
            <div class="metric-card">
                <h5 class="mb-3">Motion Summary</h5>
                <div class="row">
                    <div class="col-6 mb-3">
                        <div class="text-center">
                            <div class="h4 text-primary mb-0">{max_speed:.3f}</div>
                            <small class="text-muted">Peak Speed (m/s)</small>
                        </div>
                    </div>
                    <div class="col-6 mb-3">
                        <div class="text-center">
                            <div class="h4 text-info mb-0">{total_displacement:.3f}</div>
                            <small class="text-muted">Total Displacement (m)</small>
                        </div>
                    </div>
                    <div class="col-6 mb-3">
                        <div class="text-center">
                            <div class="h4 text-success mb-0">{avg_efficiency:.0%}</div>
                            <small class="text-muted">Avg Trajectory Efficiency</small>
                        </div>
                    </div>
                    <div class="col-6 mb-3">
                        <div class="text-center">
                            <div class="h4 text-warning mb-0">{max_pitch:.1f}°/{max_roll:.1f}°</div>
                            <small class="text-muted">Max Pitch/Roll</small>
                        </div>
                    </div>
                </div>
                <hr>
                <div class="mb-2">
                    <strong>Motion States:</strong><br>
                    {motion_states_html if motion_states_html else '<span class="text-muted">No motion state data</span>'}
                </div>
                <div>
                    <strong>Data Sources:</strong> {motion_avail_html if motion_avail_html else '<span class="text-muted">Unknown</span>'}
                </div>
            </div>
        </div>
        <div class="col-lg-6">
            <div class="chart-container-compact">
                {charts.get('speed_svg', '<div class="text-muted text-center p-4">No speed data</div>')}
            </div>
        </div>
    </div>
    <!-- Trajectory Details Row -->
    <div class="row mt-3">
        <div class="col-12">
            <div class="metric-card">
                <h5 class="mb-3">📍 Trajectory Details</h5>
                {trajectory_details_html if trajectory_details_html else '<p class="text-muted">No trajectory data available</p>'}
            </div>
        </div>
    </div>
</div>

<!-- Collision Analysis Section -->
<div class="container mb-5">
    <h2 class="mb-4">💥 Collision Analysis <small class="text-muted fs-6">(Advisory)</small></h2>
    <div class="row">
        <div class="col-lg-6">
            <div class="metric-card">
                <h5 class="mb-3">Collision Summary</h5>
                <div class="row">
                    <div class="col-6 mb-3">
                        <div class="text-center">
                            <div class="h4 {'text-danger' if total_collisions > 0 else 'text-success'} mb-0">{total_collisions}</div>
                            <small class="text-muted">Collisions Detected</small>
                        </div>
                    </div>
                    <div class="col-6 mb-3">
                        <div class="text-center">
                            <div class="h4 {'text-warning' if sudden_stop_count > 0 else 'text-success'} mb-0">{sudden_stop_count}</div>
                            <small class="text-muted">Sudden Stops</small>
                        </div>
                    </div>
                    <div class="col-6 mb-3">
                        <div class="text-center">
                            <div class="h4 text-info mb-0">{min_proximity:.2f}m</div>
                            <small class="text-muted">Min Proximity</small>
                        </div>
                    </div>
                    <div class="col-6 mb-3">
                        <div class="text-center">
                            <div class="h4 text-secondary mb-0">{max_speed_drop:.2f}</div>
                            <small class="text-muted">Max Speed Drop (m/s)</small>
                        </div>
                    </div>
                </div>
                <hr>
                <div class="mb-2">
                    <strong>Risk Bands:</strong><br>
                    {risk_bands_html if risk_bands_html else '<span class="text-muted">No risk data</span>'}
                </div>
                <div>
                    <strong>Data Sources:</strong> {collision_avail_html if collision_avail_html else '<span class="text-muted">Unknown</span>'}
                </div>
                <div class="mt-2 small text-muted">
                    <em>Note: Collision analysis is advisory only and does not affect ODD compliance verdict.</em>
                </div>
            </div>
        </div>
        <div class="col-lg-6">
            <div class="chart-container-compact">
                {charts.get('proximity_svg', '<div class="text-muted text-center p-4">No proximity data</div>')}
            </div>
        </div>
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
