#!/usr/bin/env python3
"""
Interactive HTML Report Generator for ODD Analysis

Generates a stunning, interactive HTML report from ODD analysis results.
Designed for GitHub Pages deployment and portfolio showcase.

Usage:
    python scripts/generate_html_report.py --input docs/examples/report_demo_source/full_result.json \
                                           --scenario-dir data/processed/test_data/real/real_03_174232 \
                                           --output docs/report.html

Features:
    - Interactive timeline of analysis windows
    - Critical event spotlight with image pairs
    - Plotly.js charts (acceleration, risk matrix, compliance radar)
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
from typing import Dict, Any, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_analysis_result(json_path: Path) -> Dict[str, Any]:
    """Load the full analysis JSON result."""
    with open(json_path) as f:
        return json.load(f)


def get_compliance_data(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract compliance data, handling potential double nesting."""
    compliance = result['full_analysis']['odd_compliance']
    if 'odd_compliance' in compliance:
        return compliance['odd_compliance']
    return compliance


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


def get_window_status(window_id: str, result: Dict[str, Any]) -> Tuple[str, str]:
    """Determine window status (safe/warning/violation) and color."""
    compliance = get_compliance_data(result)

    # Check if this window has violations (simplified - looking at overall data)
    # In a more sophisticated version, we'd track per-window compliance
    overall_status = compliance.get('overall_compliance', 'UNKNOWN')

    if overall_status == 'IN_ODD':
        return 'safe', '#28a745'  # green
    elif overall_status == 'ODD_BOUNDARY':
        return 'warning', '#ffc107'  # yellow
    else:
        return 'violation', '#dc3545'  # red


def extract_violation_windows(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract windows with violations/warnings for spotlight section."""
    compliance = get_compliance_data(result)
    violations = compliance.get('violations', [])

    # Parse violations to determine which windows have issues
    # For now, we'll highlight all windows if there are violations
    violation_windows = []

    perception = result['full_analysis']['perception']['per_window_perception']
    motion = result['full_analysis']['motion']['per_window_motion']
    collision = result['full_analysis']['collision'].get(
        'collision_events', [])

    for perc, mot in zip(perception, motion):
        window_id = perc['window_id']

        # Find collision data for this window
        coll = next(
            (c for c in collision if c['window_id'] == window_id), None)

        # Determine if this window has critical issues
        is_critical = (
            mot.get('peak_horizontal_accel_mps2', 0) > 5.0 or
            perc.get('traversability_score', 1.0) < 0.3 or
            (coll and coll.get('risk_confidence', 0) > 0.5)
        )

        if is_critical:
            violation_windows.append({
                'window_id': window_id,
                'perception': perc,
                'motion': mot,
                'collision': coll,
                'accel': mot.get('peak_horizontal_accel_mps2', 0),
                'traversability': perc.get('traversability_score', 0),
                'collision_risk': coll.get('risk_confidence', 0) if coll else 0,
            })

    return violation_windows


def load_motion_timeseries(scenario_dir: Path, scenario_name: str, window_ids: List[str]) -> Dict[str, Any]:
    """Load motion timeseries data from motion JSON files."""
    timeseries_data = []

    for window_id in window_ids:
        motion_file = scenario_dir / \
            f"motion_{scenario_name}_w{window_id}.json"
        if motion_file.exists():
            with open(motion_file) as f:
                motion_json = json.load(f)
                timeseries_data.append({
                    'window_id': window_id,
                    'timestamps': motion_json.get('timestamps', []),
                    'accel_x': motion_json.get('accel_x', []),
                    'accel_y': motion_json.get('accel_y', []),
                    'accel_z': motion_json.get('accel_z', []),
                    'gyro_x': motion_json.get('gyro_x', []),
                    'gyro_y': motion_json.get('gyro_y', []),
                    'gyro_z': motion_json.get('gyro_z', []),
                })

    return timeseries_data


def generate_plotly_charts(result: Dict[str, Any], scenario_dir: Path, scenario_name: str) -> Dict[str, str]:
    """Generate Plotly chart configurations as JSON strings."""
    charts = {}

    # Acceleration timeline chart (per-window summary)
    motion_data = result['full_analysis']['motion']['per_window_motion']
    window_ids = [w['window_id'] for w in motion_data]
    accels = [w.get('peak_horizontal_accel_mps2', 0) for w in motion_data]

    accel_chart = {
        'data': [{
            'x': window_ids,
            'y': accels,
            'type': 'bar',
            'marker': {
                'color': ['#dc3545' if a > 5.0 else '#ffc107' if a > 2.0 else '#28a745' for a in accels]
            },
            'name': 'Peak Acceleration'
        }],
        'layout': {
            'title': 'Peak Acceleration by Window',
            'xaxis': {'title': 'Window ID'},
            'yaxis': {'title': 'Acceleration (m/s²)'},
            'shapes': [
                {'type': 'line', 'x0': -0.5, 'x1': len(window_ids)-0.5, 'y0': 2.0, 'y1': 2.0,
                 'line': {'color': '#ffc107', 'dash': 'dash', 'width': 2}},
                {'type': 'line', 'x0': -0.5, 'x1': len(window_ids)-0.5, 'y0': 5.0, 'y1': 5.0,
                 'line': {'color': '#dc3545', 'dash': 'dash', 'width': 2}}
            ],
            'annotations': [
                {'x': len(window_ids)-0.8, 'y': 2.0, 'text': 'IN_ODD (2.0)',
                 'showarrow': False, 'yshift': 10},
                {'x': len(window_ids)-0.8, 'y': 5.0, 'text': 'OUT_ODD (5.0)',
                 'showarrow': False, 'yshift': 10}
            ]
        }
    }
    charts['acceleration'] = json.dumps(accel_chart)

    # Time series charts (IMU data)
    timeseries = load_motion_timeseries(
        scenario_dir, scenario_name, window_ids)

    if timeseries:
        # Acceleration time series (all windows combined)
        accel_traces = []
        for ts in timeseries:
            if ts['accel_x'] and ts['timestamps']:
                # Calculate horizontal acceleration magnitude
                horiz_accel = [((ax**2 + ay**2)**0.5)
                               for ax, ay in zip(ts['accel_x'], ts['accel_y'])]
                accel_traces.append({
                    'x': ts['timestamps'],
                    'y': horiz_accel,
                    'type': 'scatter',
                    'mode': 'lines',
                    'name': f"Window {ts['window_id']}",
                    'line': {'width': 2}
                })

        accel_timeseries_chart = {
            'data': accel_traces,
            'layout': {
                'title': 'Horizontal Acceleration Over Time',
                'xaxis': {'title': 'Time (s)'},
                'yaxis': {'title': 'Acceleration (m/s²)'},
                'hovermode': 'x unified',
                'shapes': [
                    {'type': 'line', 'x0': timeseries[0]['timestamps'][0],
                     'x1': timeseries[-1]['timestamps'][-1] if timeseries else 2.0,
                     'y0': 0.5, 'y1': 0.5,
                     'line': {'color': '#ffc107', 'dash': 'dash', 'width': 1.5}},
                ]
            }
        }
        charts['accel_timeseries'] = json.dumps(accel_timeseries_chart)

        # Angular velocity time series
        gyro_traces = []
        for ts in timeseries:
            if ts['gyro_z'] and ts['timestamps']:
                gyro_traces.append({
                    'x': ts['timestamps'],
                    'y': [abs(gz) for gz in ts['gyro_z']],
                    'type': 'scatter',
                    'mode': 'lines',
                    'name': f"Window {ts['window_id']}",
                    'line': {'width': 2}
                })

        gyro_timeseries_chart = {
            'data': gyro_traces,
            'layout': {
                'title': 'Angular Velocity (Yaw) Over Time',
                'xaxis': {'title': 'Time (s)'},
                'yaxis': {'title': 'Angular Velocity (rad/s)'},
                'hovermode': 'x unified',
                'shapes': [
                    {'type': 'line', 'x0': timeseries[0]['timestamps'][0],
                     'x1': timeseries[-1]['timestamps'][-1] if timeseries else 2.0,
                     'y0': 0.1, 'y1': 0.1,
                     'line': {'color': '#ffc107', 'dash': 'dash', 'width': 1.5}},
                ]
            }
        }
        charts['gyro_timeseries'] = json.dumps(gyro_timeseries_chart)
    else:
        # Provide empty charts if no timeseries data
        charts['accel_timeseries'] = json.dumps(
            {'data': [], 'layout': {'title': 'Acceleration Time Series (No Data)'}})
        charts['gyro_timeseries'] = json.dumps(
            {'data': [], 'layout': {'title': 'Angular Velocity Time Series (No Data)'}})

    # Risk matrix scatter plot
    perception_data = result['full_analysis']['perception']['per_window_perception']
    collision_data = result['full_analysis']['collision'].get(
        'collision_events', [])

    risk_data = []
    for perc in perception_data:
        window_id = perc['window_id']
        coll = next(
            (c for c in collision_data if c['window_id'] == window_id), None)
        risk_data.append({
            'window_id': window_id,
            'traversability': perc.get('traversability_score', 0),
            'collision_risk': coll.get('risk_confidence', 0) if coll else 0,
        })

    risk_chart = {
        'data': [{
            'x': [r['traversability'] for r in risk_data],
            'y': [r['collision_risk'] for r in risk_data],
            'mode': 'markers+text',
            'text': [r['window_id'] for r in risk_data],
            'textposition': 'top center',
            'marker': {
                'size': 15,
                'color': ['#dc3545' if r['collision_risk'] > 0.5 or r['traversability'] < 0.3 else '#28a745' for r in risk_data]
            },
            'name': 'Windows'
        }],
        'layout': {
            'title': 'Risk Matrix: Collision vs Traversability',
            'xaxis': {'title': 'Traversability Score', 'range': [0, 1]},
            'yaxis': {'title': 'Collision Risk', 'range': [0, 1]},
            'shapes': [
                {'type': 'rect', 'x0': 0, 'x1': 0.3, 'y0': 0.5, 'y1': 1,
                 'fillcolor': '#dc3545', 'opacity': 0.2, 'line': {'width': 0}},
            ]
        }
    }
    charts['risk_matrix'] = json.dumps(risk_chart)

    return charts


def generate_html_report(result: Dict[str, Any], scenario_dir: Path, output_path: Path):
    """Generate the complete interactive HTML report."""

    # Extract data
    report = result['report']
    metadata = report['scenario_metadata']
    scenario_name = metadata['scenario_name']
    compliance = get_compliance_data(result)
    overall_status = compliance.get('overall_compliance', 'UNKNOWN')

    # Status color and icon
    status_config = {
        'IN_ODD': {'color': '#28a745', 'icon': '✅', 'label': 'IN ODD'},
        'ODD_BOUNDARY': {'color': '#ffc107', 'icon': '⚠️', 'label': 'BOUNDARY'},
        'OUT_ODD': {'color': '#dc3545', 'icon': '❌', 'label': 'OUT OF ODD'},
        'VIOLATION': {'color': '#dc3545', 'icon': '🔴', 'label': 'CRITICAL'},
    }
    status = status_config.get(overall_status, status_config['OUT_ODD'])

    # Get violation windows
    violation_windows = extract_violation_windows(result)

    # Collect all window images
    windows_with_images = []
    for window_id in result['full_analysis']['perception']['windows_analyzed']:
        images = find_window_images(scenario_dir, window_id, scenario_name)
        if images:
            windows_with_images.append({
                'id': window_id,
                'images': images
            })

    # Generate charts
    charts = generate_plotly_charts(result, scenario_dir, scenario_name)

    # Generate timestamp
    timestamp = datetime.now().strftime("%B %d, %Y at %H:%M:%S")
    
    # JSON filename for download link
    json_filename = f"{scenario_name}_full_result.json"

    # Build HTML (continued in next file due to length)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ODD Analysis Report: {scenario_name}</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Plotly.js -->
    <script src="https://cdn.plotly.com/plotly-2.27.0.min.js"></script>
    
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
        
        .timeline {{
            display: flex;
            gap: 1rem;
            overflow-x: auto;
            padding: 1rem 0;
            margin-bottom: 2rem;
        }}
        
        .timeline-item {{
            min-width: 120px;
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid transparent;
        }}
        
        .timeline-item.safe {{
            background-color: color-mix(in srgb, #28a745 15%, var(--bg-secondary));
            border-color: #28a745;
        }}
        
        .timeline-item.warning {{
            background-color: color-mix(in srgb, #ffc107 15%, var(--bg-secondary));
            border-color: #ffc107;
        }}
        
        .timeline-item.violation {{
            background-color: color-mix(in srgb, #dc3545 15%, var(--bg-secondary));
            border-color: #dc3545;
        }}
        
        .timeline-item:hover {{
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}
        
        .violation-spotlight {{
            background-color: var(--bg-secondary);
            border-left: 4px solid #dc3545;
            padding: 2rem;
            margin-bottom: 2rem;
            border-radius: 8px;
        }}
        
        .image-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin: 1.5rem 0;
        }}
        
        .image-container {{
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .image-container img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        
        .image-label {{
            background-color: var(--bg-primary);
            padding: 0.5rem 1rem;
            font-weight: bold;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .compliance-table {{
            background-color: var(--bg-secondary);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .compliance-table table {{
            margin-bottom: 0;
        }}
        
        .compliance-status-IN_ODD {{
            color: #28a745;
            font-weight: bold;
        }}
        
        .compliance-status-ODD_BOUNDARY {{
            color: #ffc107;
            font-weight: bold;
        }}
        
        .compliance-status-OUT_ODD {{
            color: #dc3545;
            font-weight: bold;
        }}
        
        .chart-container {{
            background-color: var(--bg-secondary);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            min-height: 400px;
        }}
        
        .dark-mode-toggle {{
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            z-index: 1000;
        }}
        
        @media (max-width: 768px) {{
            .image-comparison {{
                grid-template-columns: 1fr;
            }}
            
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
        <div class="mb-3 d-flex justify-content-between align-items-center">
            <a href="../index.html" class="btn btn-outline-light">← Back to Home</a>
            <a href="{json_filename}" class="btn btn-outline-light" download>📥 Download JSON</a>
        </div>
        <div class="row align-items-center">
            <div class="col-md-8">
                <h1 class="display-4">🤖 ODD Analysis Report</h1>
                <h2 class="h3">Data Set: {scenario_name}</h2>
                <p class="lead mb-0">Generated {timestamp}</p>
            </div>
            <div class="col-md-4 text-end">
                <div class="status-badge">
                    {status['icon']} {status['label']}
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Key Metrics -->
<div class="container mb-5">
    <div class="row">
        <div class="col-md-3 col-sm-6">
            <div class="metric-card">
                <div class="metric-value">{metadata['total_windows_analyzed']}</div>
                <div class="metric-label">Windows Analyzed</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="metric-card">
                <div class="metric-value">{len(compliance.get('violations', []))}</div>
                <div class="metric-label">Violations</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="metric-card">
                <div class="metric-value">{result['full_analysis']['motion']['overall_stats'].get('max_horizontal_accel_mps2', 0):.2f}</div>
                <div class="metric-label">Peak Accel (m/s²)</div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6">
            <div class="metric-card">
                <div class="metric-value">{result['full_analysis']['collision']['overall_collision_stats'].get('avg_collision_likelihood', 0):.2f}</div>
                <div class="metric-label">Avg Collision Risk</div>
            </div>
        </div>
    </div>
</div>

<!-- Executive Summary -->
<div class="container mb-5">
    <div class="row">
        <div class="col-12">
            <h2 class="mb-4">📋 Executive Summary</h2>
            <div class="metric-card">
                <p class="lead">{report['executive_summary']}</p>
            </div>
        </div>
    </div>
</div>

<!-- Critical Events Spotlight -->
<div class="container mb-5">
    <h2 class="mb-4">🚨 Critical Events</h2>
    
    {''.join(f'''
    <div class="violation-spotlight">
        <h3>Window {vw['window_id']}: Critical Violation</h3>
        
        <div class="image-comparison">
            <div class="image-container">
                <div class="image-label">Camera View</div>
                <img src="{windows_with_images[int(vw['window_id'])]['images'].get('camera', '')}" alt="Camera view">
            </div>
        </div>
        
        <div class="row mt-3">
            <div class="col-md-3">
                <div class="image-container">
                    <div class="image-label">BEV Occupancy</div>
                    <img src="{windows_with_images[int(vw['window_id'])]['images'].get('bev_occupancy', '')}" alt="BEV occupancy" class="img-fluid">
                </div>
            </div>
            <div class="col-md-3">
                <div class="image-container">
                    <div class="image-label">BEV Height</div>
                    <img src="{windows_with_images[int(vw['window_id'])]['images'].get('bev_height', '')}" alt="BEV height" class="img-fluid">
                </div>
            </div>
            <div class="col-md-3">
                <div class="image-container">
                    <div class="image-label">BEV Density</div>
                    <img src="{windows_with_images[int(vw['window_id'])]['images'].get('bev_density', '')}" alt="BEV density" class="img-fluid">
                </div>
            </div>
            <div class="col-md-3">
                <div class="image-container">
                    <div class="image-label">BEV Roughness</div>
                    <img src="{windows_with_images[int(vw['window_id'])]['images'].get('bev_roughness', '')}" alt="BEV roughness" class="img-fluid">
                </div>
            </div>
        </div>
        
        <div class="mt-3">
            <h5>Violations:</h5>
            <ul>
                {'<li>🔴 <strong>Acceleration:</strong> {:.2f} m/s² (exceeds 5.0 threshold)</li>'.format(vw['accel']) if vw['accel'] > 5.0 else ''}
                {'<li>🔴 <strong>Traversability:</strong> {:.2f} (below 0.3 minimum)</li>'.format(vw['traversability']) if vw['traversability'] < 0.3 else ''}
                {'<li>🔴 <strong>Collision Risk:</strong> {:.2f} (exceeds 0.5 threshold)</li>'.format(vw['collision_risk']) if vw['collision_risk'] > 0.5 else ''}
            </ul>
        </div>
        
        <p class="text-muted fst-italic">"{vw['perception']['camera_summary']}"</p>
    </div>
    ''' for vw in violation_windows)}
</div>

<!-- ODD Compliance Details -->
<div class="container mb-5">
    <h2 class="mb-4">📏 ODD Compliance</h2>
    
    <div class="row">
        <div class="col-md-6">
            <h5>Categorical Compliance</h5>
            <div class="compliance-table">
                <table class="table table-striped mb-0">
                    <thead>
                        <tr>
                            <th>Axis</th>
                            <th>Status</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(f'''
                        <tr>
                            <td>{axis}</td>
                            <td class="compliance-status-{status}">{status}</td>
                            <td>{result['full_analysis']['cod_classification']['cod_classification']['categorical'].get(axis, 'N/A')}</td>
                        </tr>
                        ''' for axis, status in compliance.get('categorical_compliance', {}).items())}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="col-md-6">
            <h5>Numeric Compliance</h5>
            <div class="compliance-table">
                <table class="table table-striped mb-0">
                    <thead>
                        <tr>
                            <th>Axis</th>
                            <th>Status</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(f'''
                        <tr>
                            <td>{axis}</td>
                            <td class="compliance-status-{status}">{status}</td>
                            <td>{result['full_analysis']['cod_classification']['cod_classification']['numeric'].get(axis, 'N/A')}</td>
                        </tr>
                        ''' for axis, status in compliance.get('numeric_compliance', {}).items())}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Key Findings -->
<div class="container mb-5">
    <h2 class="mb-4">🔍 Key Findings</h2>
    <div class="metric-card">
        <ol>
            {''.join(f'<li class="mb-2">{finding}</li>' for finding in report.get('key_findings', []))}
        </ol>
    </div>
</div>

<!-- Recommendations -->
<div class="container mb-5">
    <h2 class="mb-4">💡 Recommendations</h2>
    <div class="metric-card">
        <ol>
            {''.join(f'<li class="mb-2">{rec}</li>' for rec in report.get('recommendations', []))}
        </ol>
    </div>
</div>

<!-- Footer -->
<footer class="container-fluid bg-light text-muted py-4 mt-5">
    <div class="container">
        <div class="row">
            <div class="col-md-6">
                <p class="mb-0">Generated by ODD Observer Analysis Pipeline</p>
                <p class="mb-0"><small>{timestamp}</small></p>
            </div>
            <div class="col-md-6 text-end">
                <p class="mb-0">Environment: {metadata.get('data_source', 'unknown')}</p>
                <p class="mb-0">Confidence: {metadata.get('data_source_confidence', 0):.2%}</p>
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
        
        // Update Plotly charts for dark mode
        const layout_update = newTheme === 'dark' ? {{
            paper_bgcolor: '#25292f',
            plot_bgcolor: '#25292f',
            font: {{ color: '#e9ecef' }},
            xaxis: {{ gridcolor: '#495057' }},
            yaxis: {{ gridcolor: '#495057' }}
        }} : {{
            paper_bgcolor: '#f8f9fa',
            plot_bgcolor: '#f8f9fa',
            font: {{ color: '#212529' }},
            xaxis: {{ gridcolor: '#dee2e6' }},
            yaxis: {{ gridcolor: '#dee2e6' }}
        }};
        
        Plotly.relayout('accel-chart', layout_update);
        Plotly.relayout('risk-chart', layout_update);
        Plotly.relayout('accel-timeseries-chart', layout_update);
        Plotly.relayout('gyro-timeseries-chart', layout_update);
    }}
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    document.getElementById('theme-icon').textContent = savedTheme === 'dark' ? '☀️' : '🌙';
    
    // Initialize Plotly charts
    const accelData = {charts['acceleration']};
    const riskData = {charts['risk_matrix']};
    const accelTimeseriesData = {charts.get('accel_timeseries', '{"data": [], "layout": {"title": "No Data"}}')};
    const gyroTimeseriesData = {charts.get('gyro_timeseries', '{"data": [], "layout": {"title": "No Data"}}')};
    
    // Apply theme to initial charts
    const isDark = savedTheme === 'dark';
    const themeLayout = isDark ? {{
        paper_bgcolor: '#25292f',
        plot_bgcolor: '#25292f',
        font: {{ color: '#e9ecef' }},
    }} : {{
        paper_bgcolor: '#f8f9fa',
        plot_bgcolor: '#f8f9fa',
        font: {{ color: '#212529' }},
    }};
    
    accelData.layout = {{ ...accelData.layout, ...themeLayout }};
    riskData.layout = {{ ...riskData.layout, ...themeLayout }};
    accelTimeseriesData.layout = {{ ...accelTimeseriesData.layout, ...themeLayout }};
    gyroTimeseriesData.layout = {{ ...gyroTimeseriesData.layout, ...themeLayout }};
    
    Plotly.newPlot('accel-chart', accelData.data, accelData.layout, {{responsive: true}});
    Plotly.newPlot('risk-chart', riskData.data, riskData.layout, {{responsive: true}});
    Plotly.newPlot('accel-timeseries-chart', accelTimeseriesData.data, accelTimeseriesData.layout, {{responsive: true}});
    Plotly.newPlot('gyro-timeseries-chart', gyroTimeseriesData.data, gyroTimeseriesData.layout, {{responsive: true}});
    
    // Smooth scroll
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
        anchor.addEventListener('click', function (e) {{
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({{
                behavior: 'smooth'
            }});
        }});
    }});
</script>

</body>
</html>
"""

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # Copy JSON file to same directory for download link
    import shutil
    json_output = output_path.parent / json_filename
    # Find the source JSON (passed as input_path in main)
    # For now, copy from the result dict by re-serializing
    import json as json_module
    with open(json_output, 'w', encoding='utf-8') as f:
        json_module.dump(result, f, indent=2)

    print(f"✅ Report generated: {output_path}")
    print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"📥 JSON exported: {json_output}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate interactive HTML report from ODD analysis")
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

    print(f"🎨 Generating HTML report...")
    generate_html_report(result, args.scenario_dir, args.output)

    print()
    print("🎉 Report generation complete!")
    print(f"   Open in browser: file://{args.output.absolute()}")
    print(
        f"   Or serve locally: python -m http.server -d {args.output.parent}")


if __name__ == '__main__':
    main()
