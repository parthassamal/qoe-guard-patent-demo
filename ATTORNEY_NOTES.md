# Attorney Notes: QoE-Guard Prototype

## One-sentence description
A system that validates streaming APIs by measuring JSON variance against baseline scenarios and predicting QoE impact to decide pass/warn/fail with explainable field-level evidence.

## What to demonstrate live (5 minutes)
1) Seed baseline (Scenario repository)
2) Run against v1 (PASS)
3) Run against v2 (WARN/FAIL)
4) Open report: risk score + top signals + path-level changes

## Key inventive aspects you can discuss
- Scenario-driven baseline management for streaming endpoints
- JSON delta → engineered features capturing structural/value variance
- QoE-aware risk scoring (field criticality + drift signals)
- Deployment gating workflow and explainable reporting
- Auditability and controlled baseline promotion (described in the design)

## Suggested claim vocabulary (non-exhaustive)
- "variance feature vector derived from hierarchical structured response payloads"
- "classification of response deltas into QoE-impacting vs QoE-neutral"
- "policy engine applying learned risk to CI/CD gating decisions"
- "explainable contribution scores for changed JSON paths"

