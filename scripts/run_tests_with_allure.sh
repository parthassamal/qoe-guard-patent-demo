#!/bin/bash
# Run tests and generate Allure report in one command
#
# Usage:
#   ./scripts/run_tests_with_allure.sh
#   ./scripts/run_tests_with_allure.sh --serve
#   ./scripts/run_tests_with_allure.sh --unit
#   ./scripts/run_tests_with_allure.sh --integration
#   ./scripts/run_tests_with_allure.sh --smoke

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Determine test suite
TEST_SUITE=""
SERVE_FLAG=""

case "$1" in
    --unit)
        TEST_SUITE="tests/test_unit*.py"
        echo "🧪 Running unit tests..."
        ;;
    --integration)
        TEST_SUITE="tests/test_integration*.py"
        echo "🔗 Running integration tests..."
        ;;
    --smoke)
        TEST_SUITE="tests/test_smoke.py"
        echo "💨 Running smoke tests..."
        ;;
    --serve)
        SERVE_FLAG="--serve"
        TEST_SUITE="tests/"
        echo "🧪 Running all tests..."
        ;;
    *)
        TEST_SUITE="tests/"
        echo "🧪 Running all tests..."
        ;;
esac

# Check if --serve was passed as second argument
if [[ "$2" == "--serve" ]] || [[ "$1" == "--serve" ]]; then
    SERVE_FLAG="--serve"
fi

# Check if allure-pytest is installed
if python -c "import allure" 2>/dev/null; then
    echo "✅ Allure plugin detected"
    ALLURE_OPTS="--alluredir=allure-results --clean-alluredir"
else
    echo "⚠️  Allure plugin not found. Install with: pip install allure-pytest"
    echo "   Running tests without Allure..."
    ALLURE_OPTS=""
fi

# Run tests
echo "Running: pytest $TEST_SUITE -v $ALLURE_OPTS"
echo ""

pytest "$TEST_SUITE" -v $ALLURE_OPTS

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Tests completed successfully!"
    echo ""
    
    # Generate and optionally serve Allure report
    "$SCRIPT_DIR/generate_allure_report.sh" $SERVE_FLAG
else
    echo ""
    echo "❌ Tests failed. Check output above for details."
    echo ""
    echo "💡 You can still generate Allure report for partial results:"
    echo "   ./scripts/generate_allure_report.sh"
    exit 1
fi
