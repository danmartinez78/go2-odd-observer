#!/bin/bash
# Generate HTML reports for all test data scenarios

set -e

echo "=================================="
echo "Test Scenario Report Generator"
echo "=================================="
echo ""

# Real scenarios
REAL_SCENARIOS=(
    "real_01_173442"
    "real_02_173813"
    "real_03_174232"
    "real_04_174321"
    "real_05_174503"
    "real_06_174604"
)

# Sim scenarios
SIM_SCENARIOS=(
    "sim_run_test"
)

ANALYSIS_DIR="data/analysis_results/automated/test_reports_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ANALYSIS_DIR"

echo "Analysis results will be saved to: $ANALYSIS_DIR"
echo ""

# Function to run analysis and generate report
run_scenario() {
    local scenario=$1
    local data_type=$2  # "real" or "sim"
    
    echo "====================================="
    echo "Processing: $scenario ($data_type)"
    echo "====================================="
    
    # Run ODD analysis
    python scripts/run_odd_analysis.py \
        --scenario "data/processed/test_data/$data_type/$scenario" \
        --output "$ANALYSIS_DIR/${scenario}" \
        --auto-confirm
    
    # Generate HTML report
    python scripts/generate_html_report.py \
        --input "$ANALYSIS_DIR/${scenario}/full_result.json" \
        --scenario-dir "data/processed/test_data/$data_type/$scenario" \
        --output "docs/reports/${scenario}_report.html"
    
    echo "✅ Completed: $scenario"
    echo ""
}

# Process real scenarios
echo "Processing REAL robot scenarios..."
echo ""
for scenario in "${REAL_SCENARIOS[@]}"; do
    run_scenario "$scenario" "real"
done

# Process sim scenarios
echo "Processing SIMULATION scenarios..."
echo ""
for scenario in "${SIM_SCENARIOS[@]}"; do
    run_scenario "$scenario" "sim"
done

echo "=================================="
echo "✅ ALL REPORTS GENERATED"
echo "=================================="
echo ""
echo "Results:"
echo "  - Analysis JSON: $ANALYSIS_DIR/"
echo "  - HTML Reports: docs/reports/"
echo ""
echo "Next steps:"
echo "  1. Review reports in docs/reports/"
echo "  2. Update docs/index.html to link to all reports"
echo "  3. Commit and push to deploy to GitHub Pages"
