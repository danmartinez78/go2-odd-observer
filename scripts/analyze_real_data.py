#!/usr/bin/env python3
"""
Analyze real robot data collections with ODD workflow.

This script:
1. Processes all real robot data collections
2. Captures all results (reports, logs, errors)
3. Organizes output by collection and timestamp
4. Generates summary comparison across runs
"""

from google.genai import Client
from odd_agents import run_odd_workflow
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
import traceback
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class RealDataAnalyzer:
    """Analyze real robot data collections."""

    def __init__(self, api_key: str, output_base: Path):
        self.api_key = api_key
        self.genai_client = Client(api_key=api_key)
        self.output_base = output_base
        self.output_base.mkdir(parents=True, exist_ok=True)

        # Track results
        self.results = []
        self.errors = []

    def find_collections(self, data_dir: Path) -> List[Path]:
        """Find all processed collections."""
        collections = sorted(data_dir.glob("collection_*"))
        print(f"Found {len(collections)} collections:")
        for c in collections:
            index_file = c / f"index_{c.name}.csv"
            if index_file.exists():
                with open(index_file) as f:
                    num_windows = len(f.readlines()) - 1  # subtract header
                print(f"  - {c.name}: {num_windows} windows")
        return collections

    async def analyze_collection(
        self,
        collection_path: Path,
        odd_description: str
    ) -> Optional[Dict]:
        """Analyze a single collection."""
        collection_name = collection_path.name
        print(f"\n{'='*80}")
        print(f"Analyzing: {collection_name}")
        print(f"{'='*80}\n")

        # Create output directory for this collection
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.output_base / f"{collection_name}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Log file for this run
        log_file = output_dir / "analysis.log"

        try:
            # Capture stdout/stderr
            with open(log_file, 'w') as log:
                log.write(f"Collection: {collection_name}\n")
                log.write(f"Started: {datetime.now().isoformat()}\n")
                log.write(f"Data path: {collection_path}\n\n")
                log.flush()

                # Run ODD workflow
                result = await run_odd_workflow(
                    scenario_path=str(collection_path),
                    genai_client=self.genai_client,
                    api_key=self.api_key,
                    nl_odd_description=odd_description,
                    # Use default models (Flash 2.0)
                )

                log.write(f"\nCompleted: {datetime.now().isoformat()}\n")
                log.flush()

            if result:
                # Save full result
                result_file = output_dir / "full_result.json"
                with open(result_file, 'w') as f:
                    json.dump(result, f, indent=2)

                # Save executive summary
                if 'report' in result:
                    summary_file = output_dir / "executive_summary.json"
                    with open(summary_file, 'w') as f:
                        json.dump(result['report'], f, indent=2)

                # Save full analysis
                if 'full_analysis' in result:
                    analysis_file = output_dir / "full_analysis.json"
                    with open(analysis_file, 'w') as f:
                        json.dump(result['full_analysis'], f, indent=2)

                # Extract key metrics
                metrics = self._extract_metrics(result, collection_name)
                metrics['output_dir'] = str(output_dir)

                print(f"\n✅ Analysis complete for {collection_name}")
                print(f"   Output: {output_dir}")
                print(f"   Compliance: {metrics.get('compliance', 'N/A')}")
                print(f"   Violations: {metrics.get('num_violations', 0)}")
                print(f"   Warnings: {metrics.get('num_warnings', 0)}")

                return metrics
            else:
                error_msg = "Workflow returned None - analysis failed"
                print(f"\n❌ {error_msg}")
                self.errors.append({
                    'collection': collection_name,
                    'error': error_msg,
                    'output_dir': str(output_dir)
                })
                return None

        except Exception as e:
            error_msg = f"Exception during analysis: {str(e)}"
            print(f"\n❌ {error_msg}")
            traceback.print_exc()

            # Save error details
            error_file = output_dir / "error.txt"
            with open(error_file, 'w') as f:
                f.write(f"Collection: {collection_name}\n")
                f.write(f"Error: {error_msg}\n\n")
                f.write(traceback.format_exc())

            self.errors.append({
                'collection': collection_name,
                'error': error_msg,
                'traceback': traceback.format_exc(),
                'output_dir': str(output_dir)
            })
            return None

    def _extract_metrics(self, result: Dict, collection_name: str) -> Dict:
        """Extract key metrics from result."""
        metrics = {
            'collection': collection_name,
            'timestamp': datetime.now().isoformat()
        }

        # Get report info
        if 'report' in result:
            report = result['report']
            metadata = report.get('scenario_metadata', {})
            metrics['windows_analyzed'] = metadata.get(
                'total_windows_analyzed', 0)
            metrics['data_source'] = metadata.get('data_source', 'unknown')
            metrics['data_source_confidence'] = metadata.get(
                'data_source_confidence', 'N/A')

        # Get compliance info
        if 'full_analysis' in result:
            compliance = result['full_analysis'].get('odd_compliance', {})
            metrics['compliance'] = compliance.get(
                'overall_compliance', 'unknown')
            metrics['num_violations'] = len(compliance.get('violations', []))
            metrics['num_warnings'] = len(compliance.get('warnings', []))
            metrics['recommendations'] = len(
                compliance.get('recommendations', []))

        return metrics

    async def analyze_all(
        self,
        data_dir: Path,
        odd_description: str
    ):
        """Analyze all collections."""
        collections = self.find_collections(data_dir)

        if not collections:
            print("No collections found!")
            return

        print(f"\nStarting analysis of {len(collections)} collections...")
        print(f"Results will be saved to: {self.output_base}\n")

        # Process each collection
        for collection in collections:
            metrics = await self.analyze_collection(collection, odd_description)
            if metrics:
                self.results.append(metrics)

        # Generate summary
        self._generate_summary()

    def _generate_summary(self):
        """Generate summary report comparing all collections."""
        summary_file = self.output_base / "SUMMARY.md"

        with open(summary_file, 'w') as f:
            f.write("# Real Robot Data Analysis Summary\n\n")
            f.write(
                f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Overall stats
            f.write(f"## Overall Statistics\n\n")
            f.write(f"- **Total Collections Analyzed:** {len(self.results)}\n")
            f.write(f"- **Failed Analyses:** {len(self.errors)}\n")

            total_windows = sum(r.get('windows_analyzed', 0)
                                for r in self.results)
            f.write(f"- **Total Windows Processed:** {total_windows}\n\n")

            # Results table
            if self.results:
                f.write("## Analysis Results\n\n")
                f.write(
                    "| Collection | Windows | Compliance | Violations | Warnings | Output |\n")
                f.write(
                    "|------------|---------|------------|------------|----------|--------|\n")

                for r in self.results:
                    f.write(f"| {r['collection']} | "
                            f"{r.get('windows_analyzed', 'N/A')} | "
                            f"{r.get('compliance', 'N/A')} | "
                            f"{r.get('num_violations', 0)} | "
                            f"{r.get('num_warnings', 0)} | "
                            f"[link]({r.get('output_dir', '')}) |\n")

                f.write("\n")

            # Errors
            if self.errors:
                f.write("## Errors\n\n")
                for err in self.errors:
                    f.write(f"### {err['collection']}\n\n")
                    f.write(f"- **Error:** {err['error']}\n")
                    f.write(
                        f"- **Output:** {err.get('output_dir', 'N/A')}\n\n")

            # Compliance summary
            if self.results:
                f.write("## Compliance Summary\n\n")
                compliant = sum(1 for r in self.results
                                if r.get('compliance', '').lower() == 'compliant')
                non_compliant = sum(1 for r in self.results
                                    if r.get('compliance', '').lower() == 'non-compliant')

                f.write(f"- **Compliant:** {compliant}/{len(self.results)}\n")
                f.write(
                    f"- **Non-Compliant:** {non_compliant}/{len(self.results)}\n")

                total_violations = sum(r.get('num_violations', 0)
                                       for r in self.results)
                total_warnings = sum(r.get('num_warnings', 0)
                                     for r in self.results)

                f.write(f"- **Total Violations:** {total_violations}\n")
                f.write(f"- **Total Warnings:** {total_warnings}\n")

        print(f"\n{'='*80}")
        print(f"Summary saved to: {summary_file}")
        print(f"{'='*80}\n")

        # Also save JSON version
        summary_json = self.output_base / "summary.json"
        with open(summary_json, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': self.results,
                'errors': self.errors
            }, f, indent=2)


async def main():
    """Main entry point."""
    import os

    # Get API key
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set")
        sys.exit(1)

    # Paths
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data" / "processed" / "runs"
    output_base = project_root / "data" / "analysis_results" / \
        "real_robot" / datetime.now().strftime("%Y%m%d_%H%M%S")

    # ODD description
    odd_description = """
    Indoor laboratory environment with:
    - Flat, smooth floor surfaces (tile, concrete)
    - Controlled lighting conditions
    - No obstacles or minimal static obstacles
    - Dry conditions
    - Temperature controlled (18-25°C)
    - Low to moderate foot traffic
    - Operating speed: walking pace (0.5-1.5 m/s)
    """

    # Run analysis
    analyzer = RealDataAnalyzer(api_key, output_base)
    await analyzer.analyze_all(data_dir, odd_description)

    print("\n✅ All analyses complete!")
    print(f"\nResults location: {output_base}")


if __name__ == "__main__":
    asyncio.run(main())
