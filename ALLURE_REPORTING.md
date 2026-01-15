# Allure Reporting Integration

QoE-Guard uses [Allure Report](https://allurereport.org) for comprehensive test reporting with detailed visualizations, attachments, and test history.

## Installation

### Step 1: Install Allure Commandline

**macOS:**
```bash
brew install allure
```

**Linux:**
```bash
# Download from https://github.com/allure-framework/allure2/releases
# Or use package manager
```

**Windows:**
```powershell
scoop install allure
```

### Step 2: Install Python Dependencies

```bash
# Install all dependencies including allure-pytest
pip install -r requirements.txt

# Or install just allure-pytest
pip install allure-pytest==2.13.2
```

**Verify Installation:**
```bash
# Check if allure-pytest is installed
python -c "import allure; print('✅ Allure plugin installed')"

# Check if allure commandline is available
allure --version
```

## Running Tests with Allure

### Option 1: Run Tests and Generate Report (Recommended)

```bash
# Run all tests and generate report
./scripts/run_tests_with_allure.sh

# Run and open report in browser
./scripts/run_tests_with_allure.sh --serve

# Run specific test suite
./scripts/run_tests_with_allure.sh --unit
./scripts/run_tests_with_allure.sh --integration
./scripts/run_tests_with_allure.sh --smoke
```

### Option 2: Manual Steps

```bash
# Step 1: Run tests (results saved to allure-results/)
pytest tests/ -v

# Step 2: Generate report
./scripts/generate_allure_report.sh

# Step 3: Open report in browser
allure open allure-report
```

### Option 3: Direct pytest Command

```bash
# Run tests with Allure (requires allure-pytest installed)
pytest tests/ -v --alluredir=allure-results --clean-alluredir

# Or use the Allure-enabled config file
pytest -c pytest-allure.ini tests/ -v

# Generate report
allure generate allure-results -o allure-report --clean

# Serve report
allure open allure-report
```

### Option 4: Run Tests Without Allure (Fallback)

If `allure-pytest` is not installed, tests will still run normally:

```bash
# Tests run without Allure options
pytest tests/ -v

# No Allure report will be generated, but all tests execute
```

## Viewing Reports

### Local Development

After generating a report:

```bash
allure open allure-report
```

This will:
- Start a local web server
- Open the report in your default browser
- Display at `http://localhost:XXXX`

### CI/CD Integration

For CI/CD pipelines, you can:

1. **Upload artifacts** (GitHub Actions example):
```yaml
- name: Generate Allure Report
  run: allure generate allure-results -o allure-report --clean

- name: Upload Allure Report
  uses: actions/upload-artifact@v3
  with:
    name: allure-report
    path: allure-report/
```

2. **Publish to Allure TestOps** (if using Allure TestOps):
```yaml
- name: Publish to Allure TestOps
  run: |
    allure-publish --project-id YOUR_PROJECT_ID \
                   --endpoint https://your-testops-instance.com \
                   --token YOUR_TOKEN \
                   allure-results/
```

## Allure Features in QoE-Guard Tests

### Test Annotations

Our tests use Allure annotations for better reporting:

- **@allure.feature()** - Groups tests by feature (e.g., "JSON Diff Engine", "Scoring System")
- **@allure.story()** - Sub-features or user stories
- **@allure.title()** - Custom test titles
- **@allure.description()** - Detailed test descriptions
- **@allure.severity()** - Test severity levels (TRIVIAL, MINOR, NORMAL, CRITICAL, BLOCKER)
- **@allure.step()** - Step-by-step test execution breakdown

### Attachments

Tests automatically attach:

- **JSON Inputs/Outputs** - Baseline and candidate JSON responses
- **Change Details** - Detected changes with paths and types
- **Feature Vectors** - Extracted features for scoring
- **Analysis Summaries** - Complete diff analysis results
- **Test Data** - Sample data used in tests

### Example Test with Allure

```python
@allure.feature("JSON Diff Engine")
@allure.story("Breaking Change Detection")
@allure.title("Type changes should be flagged as breaking")
@allure.severity(allure.severity_level.CRITICAL)
def test_type_change_detected(self):
    """Type changes should be detected and flagged as critical."""
    with allure.step("Prepare test data"):
        old = {"value": 100}
        new = {"value": "100"}
    
    with allure.step("Execute diff"):
        result = json_diff(old, new)
    
    with allure.step("Verify breaking change"):
        self.assertTrue(result.changes[0].is_breaking)
        
        allure.attach(
            json.dumps({
                "change": result.changes[0].__dict__,
                "decision": result.decision
            }, indent=2),
            "Breaking Change Analysis",
            allure.attachment_type.JSON
        )
```

## Report Structure

Allure reports include:

### Overview
- **Total Tests** - Passed, failed, skipped, broken
- **Duration** - Total test execution time
- **Trends** - Historical test results (if using Allure TestOps)

### Test Suites
- **Features** - Grouped by `@allure.feature()`
- **Stories** - Grouped by `@allure.story()`
- **Packages** - Grouped by test file/package

### Test Details
- **Steps** - Step-by-step execution with `@allure.step()`
- **Attachments** - JSON files, screenshots, logs
- **Parameters** - Test parameters and data
- **History** - Previous test runs (if configured)

### Graphs
- **Severity Distribution** - Tests by severity level
- **Duration** - Test execution time distribution
- **Retries** - Retry statistics (if using retries)

## Configuration

### pytest.ini (Default - Allure Optional)

The default `pytest.ini` works without Allure. To enable Allure:

1. Install `allure-pytest`: `pip install allure-pytest`
2. Use `pytest-allure.ini` or add Allure options manually:

```bash
# Use Allure-enabled config
pytest -c pytest-allure.ini tests/ -v

# Or add options manually
pytest tests/ -v --alluredir=allure-results --clean-alluredir
```

### pytest-allure.ini (Allure Enabled)

```ini
[pytest]
addopts = 
    -v 
    --tb=short
    --alluredir=allure-results
    --clean-alluredir

[allure]
results_dir = allure-results
report_dir = allure-report
```

### Environment Variables

```bash
# Allure report directory
export ALLURE_RESULTS_DIR=allure-results
export ALLURE_REPORT_DIR=allure-report

# Allure TestOps (optional)
export ALLURE_ENDPOINT=https://your-testops-instance.com
export ALLURE_TOKEN=your-token
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests with Allure

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          npm install -g allure-commandline
      
      - name: Run tests
        run: pytest tests/ -v
      
      - name: Generate Allure Report
        run: allure generate allure-results -o allure-report --clean
      
      - name: Upload Allure Report
        uses: actions/upload-artifact@v3
        with:
          name: allure-report
          path: allure-report/
          retention-days: 30
```

### Jenkins

```groovy
pipeline {
    agent any
    
    stages {
        stage('Test') {
            steps {
                sh 'pytest tests/ -v'
            }
        }
        
        stage('Allure Report') {
            steps {
                allure([
                    includeProperties: false,
                    jdk: '',
                    properties: [],
                    reportBuildPolicy: 'ALWAYS',
                    results: [[path: 'allure-results']]
                ])
            }
        }
    }
}
```

## Best Practices

1. **Use Descriptive Features/Stories**
   - Group related tests with `@allure.feature()`
   - Use `@allure.story()` for user stories or scenarios

2. **Add Meaningful Steps**
   - Break complex tests into steps with `@allure.step()`
   - Makes failures easier to debug

3. **Attach Relevant Data**
   - Attach JSON inputs/outputs
   - Include error messages and stack traces
   - Add screenshots for UI tests

4. **Set Appropriate Severity**
   - Use `@allure.severity()` to prioritize tests
   - Critical tests should be marked as CRITICAL or BLOCKER

5. **Keep Reports Clean**
   - Use `--clean-alluredir` to remove old results
   - Archive old reports regularly

## Troubleshooting

### "Allure command not found"

Install Allure commandline:
```bash
# macOS
brew install allure

# Or download from https://github.com/allure-framework/allure2/releases
```

### "No test results found"

Run tests first:
```bash
pytest tests/ -v
```

### Report not updating

Clear old results:
```bash
rm -rf allure-results allure-report
pytest tests/ -v
allure generate allure-results -o allure-report --clean
```

### Import errors

Ensure `allure-pytest` is installed:
```bash
pip install allure-pytest==2.13.2
```

### "unrecognized arguments: --alluredir"

This means `allure-pytest` is not installed. Either:

1. **Install allure-pytest:**
   ```bash
   pip install allure-pytest==2.13.2
   ```

2. **Or run tests without Allure:**
   ```bash
   pytest tests/ -v  # Works without Allure options
   ```

3. **Or use the Allure-enabled config:**
   ```bash
   pytest -c pytest-allure.ini tests/ -v
   ```

## Resources

- [Allure Report Documentation](https://allurereport.org/docs/)
- [Allure Python Integration](https://github.com/allure-framework/allure-python)
- [Allure GitHub Repository](https://github.com/allure-framework/allure2)
