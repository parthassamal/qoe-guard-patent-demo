#!/bin/bash
# Generate Allure Report from test results
#
# Usage:
#   ./scripts/generate_allure_report.sh
#   ./scripts/generate_allure_report.sh --serve
#
# Prerequisites:
#   - Install Allure: https://allurereport.org/docs/gettingstarted/
#   - Run tests first: pytest tests/ -v

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

RESULTS_DIR="allure-results"
REPORT_DIR="allure-report"

# Check if Allure is installed
if ! command -v allure &> /dev/null; then
    echo "❌ Allure is not installed!"
    echo ""
    echo "Install Allure:"
    echo "  macOS:   brew install allure"
    echo "  Linux:   See https://allurereport.org/docs/gettingstarted/"
    echo "  Windows: scoop install allure"
    echo ""
    exit 1
fi

# Check if results directory exists
if [ ! -d "$RESULTS_DIR" ] || [ -z "$(ls -A $RESULTS_DIR 2>/dev/null)" ]; then
    echo "⚠️  No test results found in $RESULTS_DIR"
    echo ""
    echo "Run tests first with Allure:"
    echo "  pip install allure-pytest"
    echo "  pytest tests/ -v --alluredir=allure-results"
    echo "  or"
    echo "  ./scripts/run_tests_with_allure.sh"
    echo ""
    exit 1
fi

echo "📊 Generating Allure Report..."
echo "   Results: $RESULTS_DIR"
echo "   Output:  $REPORT_DIR"
echo ""

# Generate report
allure generate "$RESULTS_DIR" -o "$REPORT_DIR" --clean

if [ $? -eq 0 ]; then
    echo "✅ Allure report generated successfully!"
    echo "   Report location: $REPORT_DIR/index.html"
    echo ""
    
    # Serve report if --serve flag is provided
    if [[ "$1" == "--serve" ]]; then
        echo "🌐 Opening Allure report in browser..."
        echo "   Press Ctrl+C to stop the server"
        echo ""
        allure open "$REPORT_DIR"
    else
        echo "💡 To view the report, run:"
        echo "   allure open $REPORT_DIR"
        echo "   or"
        echo "   ./scripts/generate_allure_report.sh --serve"
    fi
else
    echo "❌ Failed to generate Allure report"
    exit 1
fi
