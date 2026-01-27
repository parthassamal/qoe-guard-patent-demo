#!/usr/bin/env python3
"""
POC Scenario Runner

Automated script to run all POC validation scenarios and generate a summary report.
This script validates that all features work correctly and produces a demo-ready report.
"""

import sys
import os
import json
import time
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qoe_guard.diff import json_diff
from qoe_guard.features import extract_features
from qoe_guard.model import score
from qoe_guard.scoring.brittleness import compute_brittleness_score
from qoe_guard.scoring.qoe_risk import assess_qoe_risk
from qoe_guard.scoring.drift import classify_drift, DriftType

# Configuration
QOE_GUARD_URL = os.getenv("QOE_GUARD_URL", "http://localhost:8010")
DEMO_TARGET_URL = os.getenv("DEMO_TARGET_URL", "http://localhost:8001")
TIMEOUT = 15


@dataclass
class ScenarioResult:
    """Result of a validation scenario."""
    name: str
    version: int
    expected_result: str
    actual_result: str
    risk_score: float
    brittleness_score: Optional[float] = None
    qoe_risk_score: Optional[float] = None
    changes_count: int = 0
    passed: bool = False
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class POCReport:
    """Complete POC test report."""
    timestamp: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    results: List[ScenarioResult]
    summary: Dict[str, Any]


def fetch_json(url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Fetch JSON from URL."""
    try:
        response = requests.get(url, params=params or {}, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise ValueError(f"Failed to fetch {url}: {e}")


def run_scenario(
    name: str,
    version: int,
    expected_result: str,
    baseline: Dict[str, Any],
    candidate_url: str
) -> ScenarioResult:
    """Run a single validation scenario."""
    start_time = time.time()
    
    try:
        # Fetch candidate response
        candidate = fetch_json(candidate_url, params={"v": version})
        
        # Perform diff analysis
        diff_result = json_diff(baseline, candidate)
        
        # Extract features
        features = extract_features(diff_result)
        
        # Calculate scores
        decision = score(features)
        
        # Calculate brittleness (if available)
        brittleness = None
        try:
            brittleness = compute_brittleness_score(
                total_changes=len(diff_result.changes),
                critical_changes=sum(1 for c in diff_result.changes if c.is_critical),
                type_changes=sum(1 for c in diff_result.changes if c.change_type == "type_changed"),
            )
        except Exception:
            pass
        
        # Calculate QoE risk
        qoe_risk = None
        try:
            qoe_result = assess_qoe_risk(
                changes_count=len(diff_result.changes),
                critical_changes=sum(1 for c in diff_result.changes if c.is_critical),
                type_changes=sum(1 for c in diff_result.changes if c.change_type == "type_changed"),
                removed_fields=sum(1 for c in diff_result.changes if c.change_type == "removed"),
            )
            qoe_risk = qoe_result.score
        except Exception:
            pass
        
        duration = (time.time() - start_time) * 1000
        
        # Determine if scenario passed
        passed = decision.action == expected_result
        
        return ScenarioResult(
            name=name,
            version=version,
            expected_result=expected_result,
            actual_result=decision.action,
            risk_score=decision.risk_score,
            brittleness_score=brittleness,
            qoe_risk_score=qoe_risk,
            changes_count=len(diff_result.changes),
            passed=passed,
            duration_ms=duration
        )
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return ScenarioResult(
            name=name,
            version=version,
            expected_result=expected_result,
            actual_result="ERROR",
            risk_score=0.0,
            passed=False,
            error=str(e),
            duration_ms=duration
        )


def run_all_scenarios() -> POCReport:
    """Run all POC scenarios."""
    print("=" * 70)
    print("QoE-Aware JSON Variance Analytics System - POC Scenario Runner")
    print("=" * 70)
    print()
    
    # Load baseline
    print("Loading baseline scenario...")
    baseline_url = f"{DEMO_TARGET_URL}/play"
    baseline = fetch_json(baseline_url, params={"v": 1})
    print(f"✓ Baseline loaded from {baseline_url}?v=1")
    print()
    
    # Define scenarios
    scenarios = [
        {
            "name": "PASS - Minor Safe Changes",
            "version": 3,
            "expected": "PASS"
        },
        {
            "name": "WARN - Moderate Changes",
            "version": 2,
            "expected": "WARN"
        },
        {
            "name": "FAIL - Breaking Changes",
            "version": 4,
            "expected": "FAIL"
        }
    ]
    
    print(f"Running {len(scenarios)} validation scenarios...")
    print()
    
    results = []
    for scenario in scenarios:
        print(f"Running: {scenario['name']} (v={scenario['version']})")
        result = run_scenario(
            name=scenario['name'],
            version=scenario['version'],
            expected_result=scenario['expected'],
            baseline=baseline,
            candidate_url=baseline_url
        )
        results.append(result)
        
        status = "✓ PASS" if result.passed else "✗ FAIL"
        if result.error:
            status = f"✗ ERROR: {result.error}"
        
        print(f"  {status}")
        print(f"  Expected: {result.expected_result}, Got: {result.actual_result}")
        print(f"  Risk Score: {result.risk_score:.4f}")
        if result.brittleness_score:
            print(f"  Brittleness: {result.brittleness_score:.2f}")
        if result.qoe_risk_score:
            print(f"  QoE Risk: {result.qoe_risk_score:.4f}")
        print(f"  Changes: {result.changes_count}")
        print(f"  Duration: {result.duration_ms:.2f}ms")
        print()
    
    # Generate summary
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    
    summary = {
        "total_scenarios": len(results),
        "passed": passed,
        "failed": failed,
        "success_rate": f"{(passed/len(results)*100):.1f}%",
        "avg_risk_score": sum(r.risk_score for r in results) / len(results) if results else 0.0,
        "avg_duration_ms": sum(r.duration_ms for r in results) / len(results) if results else 0.0
    }
    
    return POCReport(
        timestamp=datetime.now().isoformat(),
        total_scenarios=len(results),
        passed_scenarios=passed,
        failed_scenarios=failed,
        results=results,
        summary=summary
    )


def print_report(report: POCReport):
    """Print formatted report."""
    print("=" * 70)
    print("POC Test Report")
    print("=" * 70)
    print(f"Timestamp: {report.timestamp}")
    print()
    print("Summary:")
    print(f"  Total Scenarios: {report.total_scenarios}")
    print(f"  Passed: {report.passed_scenarios}")
    print(f"  Failed: {report.failed_scenarios}")
    print(f"  Success Rate: {report.summary['success_rate']}")
    print(f"  Average Risk Score: {report.summary['avg_risk_score']:.4f}")
    print(f"  Average Duration: {report.summary['avg_duration_ms']:.2f}ms")
    print()
    print("Detailed Results:")
    print("-" * 70)
    
    for result in report.results:
        status = "✓" if result.passed else "✗"
        print(f"{status} {result.name} (v={result.version})")
        print(f"    Expected: {result.expected_result}, Actual: {result.actual_result}")
        print(f"    Risk: {result.risk_score:.4f}, Changes: {result.changes_count}")
        if result.error:
            print(f"    Error: {result.error}")
        print()
    
    print("=" * 70)


def save_report(report: POCReport, filename: str = "poc_report.json"):
    """Save report to JSON file."""
    report_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(report_dir, exist_ok=True)
    
    filepath = os.path.join(report_dir, filename)
    
    # Convert to dict for JSON serialization
    report_dict = {
        "timestamp": report.timestamp,
        "total_scenarios": report.total_scenarios,
        "passed_scenarios": report.passed_scenarios,
        "failed_scenarios": report.failed_scenarios,
        "results": [asdict(r) for r in report.results],
        "summary": report.summary
    }
    
    with open(filepath, 'w') as f:
        json.dump(report_dict, f, indent=2)
    
    print(f"Report saved to: {filepath}")


def main():
    """Main entry point."""
    try:
        # Check if services are available
        print("Checking service availability...")
        try:
            requests.get(f"{DEMO_TARGET_URL}/play?v=1", timeout=5)
            print(f"✓ Demo target service available at {DEMO_TARGET_URL}")
        except Exception as e:
            print(f"✗ Demo target service not available: {e}")
            print("  Please start services with: docker compose up -d")
            return 1
        
        try:
            requests.get(QOE_GUARD_URL, timeout=5)
            print(f"✓ QoE-Guard service available at {QOE_GUARD_URL}")
        except Exception:
            print(f"⚠ QoE-Guard service not available at {QOE_GUARD_URL}")
            print("  Continuing with core validation only...")
        print()
        
        # Run scenarios
        report = run_all_scenarios()
        
        # Print report
        print_report(report)
        
        # Save report
        save_report(report)
        
        # Return exit code based on results
        return 0 if report.failed_scenarios == 0 else 1
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
