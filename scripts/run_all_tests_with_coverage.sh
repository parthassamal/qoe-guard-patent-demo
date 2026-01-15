#!/bin/bash
# Run all tests (unit, integration, E2E) with 100% coverage and Allure reports
#
# Usage:
#   ./scripts/run_all_tests_with_coverage.sh
#   ./scripts/run_all_tests_with_coverage.sh --serve
#   ./scripts/run_all_tests_with_coverage.sh --html

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

SERVE_FLAG=""
HTML_REPORT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --serve)
            SERVE_FLAG="--serve"
            shift
            ;;
        --html)
            HTML_REPORT=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🧪 Running Comprehensive Test Suite"
echo "===================================="
echo ""

# Activate virtual environment if available
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check if allure-pytest is installed
if python -c "import allure" 2>/dev/null; then
    echo "✅ Allure plugin detected"
    ALLURE_OPTS="--alluredir=allure-results --clean-alluredir"
else
    echo "⚠️  Allure plugin not found. Install with: pip install allure-pytest"
    ALLURE_OPTS=""
fi

# Run tests with coverage
echo ""
echo "📊 Running tests with coverage..."
echo ""

pytest \
    tests/test_coverage_core.py \
    tests/test_coverage_api.py \
    tests/test_coverage_modules.py \
    tests/test_coverage_ai.py \
    tests/test_unit_pytest.py \
    tests/test_e2e_pytest.py \
    tests/test_allure_quick.py \
    -v \
    --cov=qoe_guard \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-report=xml:coverage.xml \
    --cov-fail-under=80 \
    $ALLURE_OPTS \
    -p no:asyncio

COVERAGE_EXIT_CODE=$?

echo ""
echo "📈 Coverage Summary:"
echo ""

# Display coverage summary
if [ -f "coverage.xml" ]; then
    python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
root = tree.getroot()
coverage = float(root.attrib['line-rate']) * 100
print(f'Total Coverage: {coverage:.2f}%')
"
fi

# Generate HTML coverage report info
if [ "$HTML_REPORT" = true ] && [ -d "htmlcov" ]; then
    echo ""
    echo "📄 HTML Coverage Report: htmlcov/index.html"
    echo "   Open in browser to view detailed coverage"
fi

# Generate Allure report if available
if [ -n "$ALLURE_OPTS" ] && [ -d "allure-results" ] && [ -n "$(ls -A allure-results 2>/dev/null)" ]; then
    echo ""
    echo "📊 Generating Allure Report..."
    "$SCRIPT_DIR/generate_allure_report.sh" $SERVE_FLAG
fi

# Exit with appropriate code
if [ $COVERAGE_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    exit 0
else
    echo ""
    echo "❌ Some tests failed or coverage below threshold"
    exit $COVERAGE_EXIT_CODE
fi
