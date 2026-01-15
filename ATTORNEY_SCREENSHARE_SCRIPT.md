# Attorney Screen Share Script (5 minutes)

## Before the call

1. Ensure both servers are running:
   - Terminal A: `python demo_target_service.py` (port 8001)
   - Terminal B: `uvicorn qoe_guard.server:app --reload --port 8010`
2. Open browser to `http://127.0.0.1:8010`
3. Clear any existing runs if needed (delete `data/runs.json`)

---

## Script

### [0:00] Introduction (30 sec)

> "This is QoE-Guard — a working prototype that validates streaming API responses by comparing them to stored baselines, computing QoE risk, and gating releases with PASS/WARN/FAIL decisions.
>
> Let me show you the complete workflow."

### [0:30] Seed baseline (30 sec)

**Action:** Click "Seed baseline" button

> "First, I seed a baseline scenario. This captures the v1 response from our demo endpoint and stores it as the 'known-good' state.
>
> Notice it saved a scenario with the endpoint `/play` and our base URL."

### [1:00] Run v1 validation — expect PASS (1 min)

**Action:** Click "Run v1 (PASS)" → wait for report

> "Now I run validation against v1 — the same version as our baseline.
>
> **Point to:** Risk score is **0.23**, decision is **PASS**.
>
> No drift detected because the candidate matches the baseline."

### [2:00] Run v2 validation — expect FAIL (1 min)

**Action:** Click "← Back" then "Run v2 (WARN/FAIL)" → wait for report

> "Now I run against v2, which has intentional drift.
>
> **Point to:** Risk score jumped to **0.68**, decision is **FAIL**.
>
> The system detected the QoE-impacting changes."

### [3:00] Explain the report (1.5 min)

**Action:** Scroll through the report, pointing to each section

> "Let me walk through what the report shows:
>
> **Summary:** Run ID, endpoint, risk score, and the FAIL decision.
>
> **Scroll to Top signals:**
> - Policy thresholds: fail at 0.72, warn at 0.45
> - Critical override: 3+ critical changes AND 1+ type change triggers FAIL
> - Top signals: 6 critical changes, 1 type change, 12.0 numeric delta
>
> **Scroll to JSON changes:**
> - `$.playback.maxBitrateKbps` — type_changed (number → string!)
> - `$.playback.manifestUrl` — value_changed (URL changed)
> - `$.playback.startPositionSec` — value_changed (0 → 12)
> - `$.playback.lowLatencyMode` — added
> - `$.ads.adDecision` — removed
>
> Each change is classified by type and shows before/after values."

### [4:30] Wrap up (30 sec)

> "This is a complete, implemented system with:
>
> 1. **Hierarchical diff** at JSON path granularity
> 2. **Engineered variance features** (not just schema checks)
> 3. **QoE risk scoring** with weighted signals
> 4. **Policy gating** with explicit PASS/WARN/FAIL
> 5. **Explainable reports** with audit trail
>
> The technical appendix I sent has claim skeletons aligned to these mechanics.
>
> Can we discuss whether a narrowly-tailored filing makes sense?"

---

## Key talking points if asked

**Q: How is this different from schema validation?**
> Schema validation can't catch QoE-bad changes that are still schema-valid (e.g., URL changes, type coercions). We use baseline scenario comparison + drift features.

**Q: How is this different from snapshot testing?**
> Snapshot tests just diff — they don't score risk, weight critical paths, or produce gating decisions with explainability.

**Q: Is this just comparing JSON?**
> No. We extract engineered features (structural drift counts, type flips, numeric deltas, critical path indicators) and compute a weighted risk score. The claims can recite these specific mechanics.

**Q: Can you handle endpoints we don't have access to?**
> Yes — "Real data mode" supports pasting JSON directly. No network call needed. Copy/paste from logs, Postman, or any source.

---

## Files to have ready

- `qoe_guard/diff.py` — show the `Change` dataclass and `_walk` function
- `qoe_guard/features.py` — show `Features` dataclass and `CRITICAL_PATH_PREFIXES`
- `qoe_guard/model.py` — show `WEIGHTS` and `score()` function with thresholds
