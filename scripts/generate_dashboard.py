#!/usr/bin/env python3
"""
Generate an interactive results dashboard aggregating batch analysis data.

This script creates a comprehensive overview of all analyzed scenarios with:
- Aggregate statistics and compliance distribution
- Interactive charts showing trends across scenarios
- Violation patterns and risk analysis
- Performance benchmarks

Usage:
    python scripts/generate_dashboard.py --batch-dir data/analysis_results/automated/batch_20250123
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter, defaultdict
import argparse


def load_batch_results(batch_dir: Path) -> List[Dict[str, Any]]:
    """Load all full_result.json files from batch analysis directory."""
    results = []
    
    # Find all full_result.json files recursively
    for result_file in batch_dir.rglob('full_result.json'):
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
                # Add metadata about the file location
                data['_source_file'] = str(result_file.relative_to(batch_dir))
                data['_scenario_id'] = result_file.parent.name
                results.append(data)
        except Exception as e:
            print(f"⚠️  Failed to load {result_file}: {e}")
    
    return results


def aggregate_compliance_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate aggregate compliance statistics across all results."""
    total_windows = len(results)
    compliance_counts = Counter()
    violation_counts = defaultdict(int)
    environment_types = Counter()
    terrain_types = Counter()
    
    # Aggregate stats
    total_violations = 0
    max_acceleration = 0.0
    collision_count = 0
    
    for result in results:
        # Get compliance status (handle nested structure)
        compliance_data = result.get('full_analysis', {}).get('compliance', {})
        if 'compliance' in compliance_data:  # Double-nested
            compliance_data = compliance_data['compliance']
        
        status = compliance_data.get('overall_compliance', 'UNKNOWN')
        compliance_counts[status] += 1
        
        # Count violations
        violations = compliance_data.get('violations', [])
        total_violations += len(violations)
        for v in violations:
            violation_counts[v.get('parameter', 'unknown')] += 1
        
        # Perception data
        perception = result.get('full_analysis', {}).get('perception', {})
        env_type = perception.get('environment_type', 'unknown')
        terrain_type = perception.get('terrain_type', 'unknown')
        environment_types[env_type] += 1
        terrain_types[terrain_type] += 1
        
        # Motion data
        motion = result.get('full_analysis', {}).get('motion', {})
        overall_stats = motion.get('overall_stats', {})
        if overall_stats:
            max_accel = overall_stats.get('max_acceleration_magnitude', 0.0)
            max_acceleration = max(max_acceleration, max_accel)
        
        # Collision data
        collision = result.get('full_analysis', {}).get('collision', {})
        if collision.get('collision_detected', False):
            collision_count += 1
    
    return {
        'total_windows': total_windows,
        'compliance_distribution': dict(compliance_counts),
        'violation_breakdown': dict(violation_counts),
        'total_violations': total_violations,
        'environment_distribution': dict(environment_types),
        'terrain_distribution': dict(terrain_types),
        'max_acceleration': max_acceleration,
        'collision_count': collision_count,
        'avg_violations_per_window': total_violations / total_windows if total_windows > 0 else 0
    }


def generate_plotly_aggregate_charts(stats: Dict[str, Any]) -> str:
    """Generate Plotly chart configurations for aggregate data."""
    
    # Compliance Distribution Pie Chart
    compliance_data = stats['compliance_distribution']
    compliance_chart = f"""
    {{
        data: [{{
            type: 'pie',
            labels: {json.dumps(list(compliance_data.keys()))},
            values: {json.dumps(list(compliance_data.values()))},
            marker: {{
                colors: ['#28a745', '#ffc107', '#dc3545', '#6c757d']
            }},
            textinfo: 'label+percent',
            textposition: 'outside',
            hovertemplate: '<b>%{{label}}</b><br>Count: %{{value}}<br>Percentage: %{{percent}}<extra></extra>'
        }}],
        layout: {{
            title: 'Compliance Distribution Across All Windows',
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#e1e4e8' }},
            showlegend: true,
            height: 400
        }}
    }}
    """
    
    # Violation Breakdown Bar Chart
    violation_data = stats['violation_breakdown']
    sorted_violations = sorted(violation_data.items(), key=lambda x: x[1], reverse=True)
    violation_chart = f"""
    {{
        data: [{{
            type: 'bar',
            x: {json.dumps([v[0] for v in sorted_violations])},
            y: {json.dumps([v[1] for v in sorted_violations])},
            marker: {{ color: '#dc3545' }},
            hovertemplate: '<b>%{{x}}</b><br>Count: %{{y}}<extra></extra>'
        }}],
        layout: {{
            title: 'Violation Breakdown by Parameter',
            xaxis: {{ 
                title: 'Parameter',
                tickangle: -45,
                color: '#e1e4e8'
            }},
            yaxis: {{ 
                title: 'Count',
                color: '#e1e4e8'
            }},
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(30,30,30,0.5)',
            font: {{ color: '#e1e4e8' }},
            height: 400
        }}
    }}
    """
    
    # Environment Distribution
    env_data = stats['environment_distribution']
    env_chart = f"""
    {{
        data: [{{
            type: 'bar',
            x: {json.dumps(list(env_data.keys()))},
            y: {json.dumps(list(env_data.values()))},
            marker: {{ color: '#667eea' }},
            hovertemplate: '<b>%{{x}}</b><br>Count: %{{y}}<extra></extra>'
        }}],
        layout: {{
            title: 'Environment Type Distribution',
            xaxis: {{ 
                title: 'Environment Type',
                tickangle: -45,
                color: '#e1e4e8'
            }},
            yaxis: {{ 
                title: 'Count',
                color: '#e1e4e8'
            }},
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(30,30,30,0.5)',
            font: {{ color: '#e1e4e8' }},
            height: 400
        }}
    }}
    """
    
    return compliance_chart, violation_chart, env_chart


def generate_dashboard_html(stats: Dict[str, Any], results: List[Dict[str, Any]], output_path: Path):
    """Generate the HTML dashboard with aggregate statistics and charts."""
    
    compliance_chart, violation_chart, env_chart = generate_plotly_aggregate_charts(stats)
    
    # Calculate percentages
    total = stats['total_windows']
    in_odd_pct = (stats['compliance_distribution'].get('IN_ODD', 0) / total * 100) if total > 0 else 0
    out_odd_pct = (stats['compliance_distribution'].get('OUT_ODD', 0) / total * 100) if total > 0 else 0
    boundary_pct = (stats['compliance_distribution'].get('BOUNDARY', 0) / total * 100) if total > 0 else 0
    
    # Build scenario summary table
    scenario_rows = []
    for result in sorted(results, key=lambda x: x.get('_scenario_id', '')):
        scenario_id = result.get('_scenario_id', 'unknown')
        
        compliance_data = result.get('full_analysis', {}).get('compliance', {})
        if 'compliance' in compliance_data:
            compliance_data = compliance_data['compliance']
        
        status = compliance_data.get('overall_compliance', 'UNKNOWN')
        violations = len(compliance_data.get('violations', []))
        
        perception = result.get('full_analysis', {}).get('perception', {})
        env_type = perception.get('environment_type', 'unknown')
        
        motion = result.get('full_analysis', {}).get('motion', {}).get('overall_stats', {})
        max_accel = motion.get('max_acceleration_magnitude', 0.0)
        
        collision = result.get('full_analysis', {}).get('collision', {})
        has_collision = '🔴 Yes' if collision.get('collision_detected', False) else '✅ No'
        
        # Status badge
        if status == 'IN_ODD':
            badge = '<span class="badge bg-success">IN ODD</span>'
        elif status == 'OUT_ODD':
            badge = '<span class="badge bg-danger">OUT ODD</span>'
        elif status == 'BOUNDARY':
            badge = '<span class="badge bg-warning">BOUNDARY</span>'
        else:
            badge = '<span class="badge bg-secondary">UNKNOWN</span>'
        
        scenario_rows.append(f"""
        <tr>
            <td><code>{scenario_id}</code></td>
            <td>{badge}</td>
            <td>{violations}</td>
            <td>{env_type}</td>
            <td>{max_accel:.2f} m/s²</td>
            <td>{has_collision}</td>
        </tr>
        """)
    
    scenario_table = '\n'.join(scenario_rows)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ODD Analysis Dashboard - Aggregate Results</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #1c2128;
            --text-primary: #e1e4e8;
            --text-secondary: #8b949e;
            --border-color: #30363d;
            --accent-color: #667eea;
        }}
        
        body {{
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            padding: 2rem 0;
        }}
        
        .dashboard-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 3rem 2rem;
            margin-bottom: 3rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }}
        
        .stat-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .chart-container {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
        }}
        
        .table {{
            color: var(--text-primary);
        }}
        
        .table thead {{
            background: var(--bg-tertiary);
            border-bottom: 2px solid var(--border-color);
        }}
        
        .table tbody tr {{
            border-bottom: 1px solid var(--border-color);
        }}
        
        .table tbody tr:hover {{
            background: var(--bg-tertiary);
        }}
        
        h2, h3 {{
            color: var(--text-primary);
            margin-bottom: 1.5rem;
        }}
        
        .section {{
            margin-bottom: 4rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="dashboard-header text-center">
            <h1 class="display-4 mb-3">📊 ODD Analysis Dashboard</h1>
            <p class="lead mb-0">Aggregate Results & Performance Metrics</p>
            <p class="text-white-50 mt-2">Analyzed {stats['total_windows']} windows across multiple scenarios</p>
        </div>
        
        <!-- Key Metrics -->
        <div class="section">
            <h2>Key Metrics</h2>
            <div class="row">
                <div class="col-md-3">
                    <div class="stat-card text-center">
                        <div class="stat-value">{stats['total_windows']}</div>
                        <div class="stat-label">Total Windows</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card text-center">
                        <div class="stat-value">{in_odd_pct:.1f}%</div>
                        <div class="stat-label">In ODD</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card text-center">
                        <div class="stat-value">{stats['total_violations']}</div>
                        <div class="stat-label">Total Violations</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card text-center">
                        <div class="stat-value">{stats['avg_violations_per_window']:.1f}</div>
                        <div class="stat-label">Avg per Window</div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-3">
                    <div class="stat-card text-center">
                        <div class="stat-value">{stats['max_acceleration']:.2f}</div>
                        <div class="stat-label">Peak Accel (m/s²)</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card text-center">
                        <div class="stat-value">{stats['collision_count']}</div>
                        <div class="stat-label">Collisions</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card text-center">
                        <div class="stat-value">{out_odd_pct:.1f}%</div>
                        <div class="stat-label">Out of ODD</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card text-center">
                        <div class="stat-value">{boundary_pct:.1f}%</div>
                        <div class="stat-label">Boundary</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Charts Section -->
        <div class="section">
            <h2>Distribution Analysis</h2>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="chart-container">
                        <div id="complianceChart"></div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="chart-container">
                        <div id="environmentChart"></div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-12">
                    <div class="chart-container">
                        <div id="violationChart"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Scenario Details Table -->
        <div class="section">
            <h2>Scenario Details</h2>
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Scenario ID</th>
                            <th>Status</th>
                            <th>Violations</th>
                            <th>Environment</th>
                            <th>Peak Accel</th>
                            <th>Collision</th>
                        </tr>
                    </thead>
                    <tbody>
                        {scenario_table}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="text-center mt-5" style="color: var(--text-secondary);">
            <p class="mb-0">Generated by ODD Observer Dashboard Generator</p>
            <p class="small">Powered by Multi-Agent AI Analysis Pipeline</p>
        </div>
    </div>
    
    <script>
        // Render charts
        Plotly.newPlot('complianceChart', {compliance_chart});
        Plotly.newPlot('violationChart', {violation_chart});
        Plotly.newPlot('environmentChart', {env_chart});
    </script>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"✅ Dashboard generated: {output_path}")
    print(f"   Total windows analyzed: {stats['total_windows']}")
    print(f"   In ODD: {in_odd_pct:.1f}%")
    print(f"   Out of ODD: {out_odd_pct:.1f}%")
    print(f"   Total violations: {stats['total_violations']}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate aggregate dashboard from batch analysis results'
    )
    parser.add_argument(
        '--batch-dir',
        type=Path,
        required=True,
        help='Directory containing batch analysis results'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('docs/dashboard.html'),
        help='Output HTML file path (default: docs/dashboard.html)'
    )
    
    args = parser.parse_args()
    
    if not args.batch_dir.exists():
        print(f"❌ Batch directory not found: {args.batch_dir}")
        sys.exit(1)
    
    print(f"📂 Loading batch results from: {args.batch_dir}")
    results = load_batch_results(args.batch_dir)
    
    if not results:
        print(f"❌ No results found in {args.batch_dir}")
        sys.exit(1)
    
    print(f"📊 Aggregating statistics from {len(results)} results...")
    stats = aggregate_compliance_stats(results)
    
    print(f"🎨 Generating dashboard HTML...")
    generate_dashboard_html(stats, results, args.output)
    
    print()
    print("🎉 Dashboard generation complete!")
    print(f"   Open in browser: file://{args.output.absolute()}")


if __name__ == '__main__':
    main()
