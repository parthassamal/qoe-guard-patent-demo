#!/usr/bin/env python3
"""
QoE-Guard CLI — Run validations from command line for CI/CD integration.

Exit codes:
  0 = PASS
  1 = WARN
  2 = FAIL
  3 = ERROR

Usage:
  # Validate with pasted JSON
  qoe-guard validate --baseline baseline.json --candidate candidate.json

  # Validate from URL
  qoe-guard validate --baseline-url http://api/v1 --candidate-url http://api/v2

  # Output formats
  qoe-guard validate ... --format json
  qoe-guard validate ... --format summary
  qoe-guard validate ... --format github  # GitHub Actions annotation format
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .diff import diff_json
from .features import extract_features, to_dict
from .model import score

EXIT_PASS = 0
EXIT_WARN = 1
EXIT_FAIL = 2
EXIT_ERROR = 3


def load_json_file(path: str) -> Dict[str, Any]:
    """Load JSON from file path."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fetch_json_url(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Dict[str, Any]:
    """Fetch JSON from URL."""
    resp = requests.get(url, headers=headers or {}, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def run_validation(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Run QoE validation and return results."""
    changes = diff_json(baseline, candidate)
    features = extract_features(changes)
    decision = score(features)
    
    return {
        "risk_score": decision.risk_score,
        "action": decision.action,
        "features": to_dict(features),
        "reasons": decision.reasons,
        "changes": [
            {
                "path": c.path,
                "change_type": c.change_type,
                "before": c.before,
                "after": c.after,
            }
            for c in changes
        ],
        "change_count": len(changes),
    }


def format_summary(result: Dict[str, Any]) -> str:
    """Format as human-readable summary."""
    lines = [
        f"╔══════════════════════════════════════════╗",
        f"║        QoE-Guard Validation Report       ║",
        f"╠══════════════════════════════════════════╣",
        f"║  Decision:    {result['action']:>25} ║",
        f"║  Risk Score:  {result['risk_score']:>25.4f} ║",
        f"║  Changes:     {result['change_count']:>25} ║",
        f"╠══════════════════════════════════════════╣",
        f"║  Top Signals:                            ║",
    ]
    
    for signal in result["reasons"].get("top_signals", [])[:4]:
        lines.append(f"║    {signal['signal']}: {signal['value']:>22} ║")
    
    lines.append(f"╚══════════════════════════════════════════╝")
    
    # Add change details
    if result["changes"]:
        lines.append("")
        lines.append("Path-level changes:")
        for c in result["changes"][:10]:
            lines.append(f"  [{c['change_type']}] {c['path']}")
        if len(result["changes"]) > 10:
            lines.append(f"  ... and {len(result['changes']) - 10} more")
    
    return "\n".join(lines)


def format_github(result: Dict[str, Any]) -> str:
    """Format as GitHub Actions annotations."""
    lines = []
    
    # Set output variables
    lines.append(f"::set-output name=decision::{result['action']}")
    lines.append(f"::set-output name=risk_score::{result['risk_score']}")
    lines.append(f"::set-output name=change_count::{result['change_count']}")
    
    # Add annotation based on decision
    if result["action"] == "FAIL":
        lines.append(f"::error::QoE-Guard FAIL - Risk score {result['risk_score']:.4f} exceeds threshold")
    elif result["action"] == "WARN":
        lines.append(f"::warning::QoE-Guard WARN - Risk score {result['risk_score']:.4f}")
    else:
        lines.append(f"::notice::QoE-Guard PASS - Risk score {result['risk_score']:.4f}")
    
    # Add change annotations
    for c in result["changes"][:5]:
        if c["change_type"] == "type_changed":
            lines.append(f"::error file=api::Type change at {c['path']}: {c['before']} → {c['after']}")
        elif c["change_type"] == "removed":
            lines.append(f"::warning file=api::Removed field at {c['path']}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="QoE-Guard CLI — Validate API responses for QoE risk",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit codes:
  0 = PASS (safe to deploy)
  1 = WARN (review recommended)
  2 = FAIL (do not deploy)
  3 = ERROR (validation failed)

Examples:
  %(prog)s validate -b baseline.json -c candidate.json
  %(prog)s validate --baseline-url http://api/v1 --candidate-url http://api/v2
  %(prog)s validate -b baseline.json -c candidate.json --format github
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Run validation")
    validate_parser.add_argument("-b", "--baseline", help="Path to baseline JSON file")
    validate_parser.add_argument("-c", "--candidate", help="Path to candidate JSON file")
    validate_parser.add_argument("--baseline-url", help="URL to fetch baseline JSON")
    validate_parser.add_argument("--candidate-url", help="URL to fetch candidate JSON")
    validate_parser.add_argument("--header", action="append", help="HTTP header (key:value)")
    validate_parser.add_argument(
        "-f", "--format",
        choices=["json", "summary", "github"],
        default="summary",
        help="Output format (default: summary)"
    )
    validate_parser.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="Exit with code 2 (FAIL) on WARN results"
    )
    
    args = parser.parse_args()
    
    if args.command != "validate":
        parser.print_help()
        sys.exit(EXIT_ERROR)
    
    try:
        # Parse headers
        headers = {}
        if args.header:
            for h in args.header:
                key, value = h.split(":", 1)
                headers[key.strip()] = value.strip()
        
        # Load baseline
        if args.baseline:
            baseline = load_json_file(args.baseline)
        elif args.baseline_url:
            baseline = fetch_json_url(args.baseline_url, headers)
        else:
            print("Error: Must provide --baseline or --baseline-url", file=sys.stderr)
            sys.exit(EXIT_ERROR)
        
        # Load candidate
        if args.candidate:
            candidate = load_json_file(args.candidate)
        elif args.candidate_url:
            candidate = fetch_json_url(args.candidate_url, headers)
        else:
            print("Error: Must provide --candidate or --candidate-url", file=sys.stderr)
            sys.exit(EXIT_ERROR)
        
        # Run validation
        result = run_validation(baseline, candidate)
        
        # Output result
        if args.format == "json":
            print(json.dumps(result, indent=2))
        elif args.format == "github":
            print(format_github(result))
        else:
            print(format_summary(result))
        
        # Determine exit code
        if result["action"] == "FAIL":
            sys.exit(EXIT_FAIL)
        elif result["action"] == "WARN":
            sys.exit(EXIT_FAIL if args.fail_on_warn else EXIT_WARN)
        else:
            sys.exit(EXIT_PASS)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()
