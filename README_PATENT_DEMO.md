# QoE-Guard Patent Demo

> **See [README.md](README.md) for full documentation.**

This is a **working, runnable prototype** demonstrating a concrete implementation of a **QoE-aware JSON variance analytics system for streaming API validation**.

---

## 🎯 Purpose

Use this demo to show patent counsel:

1. **This is not abstract** — it's implemented with specific data structures and algorithms
2. **Reduction to practice** — every component is working code you can run
3. **Technical improvement** — solves a real problem in streaming API validation

---

## ⚡ 5-Minute Demo (for attorney screen share)

### Setup (2 terminals)

**Terminal A:**
```bash
cd qoe_guard_patent_demo
source .venv/bin/activate
python demo_target_service.py
```

**Terminal B:**
```bash
cd qoe_guard_patent_demo
source .venv/bin/activate
uvicorn qoe_guard.server:app --reload --port 8010
```

### Demo Flow

1. **Open** `http://127.0.0.1:8010`
2. **Click** "Seed baseline" → stores v1 response
3. **Click** "Run v1 (PASS)" → expect **PASS** (risk ~0.23)
4. **Click** "Run v2 (WARN/FAIL)" → expect **FAIL** (risk ~0.68)
5. **Open** the report and point to:
   - Risk score
   - Policy thresholds (`fail: 0.72`, `warn: 0.45`)
   - Top signals (`critical_changes: 6`, `type_changes: 1`)
   - Path-level JSON changes table

---

## 📂 Files to Show

| File | What it demonstrates |
|------|---------------------|
| `qoe_guard/diff.py` | Hierarchical JSON diff with path-level change records |
| `qoe_guard/features.py` | Variance feature extraction (structural drift, numeric deltas) |
| `qoe_guard/model.py` | QoE-aware risk scoring + policy thresholds |
| `qoe_guard/server.py` | Orchestration, scenario repository, report generation |
| `demo_target_service.py` | Controlled v1/v2 responses showing drift scenarios |

---

## 📋 Patent Documentation

| Document | Purpose |
|----------|---------|
| [EMAIL_TO_COUNSEL.md](EMAIL_TO_COUNSEL.md) | Ready-to-send email requesting reconsideration |
| [PATENT_REVISIT_PACKET.md](PATENT_REVISIT_PACKET.md) | Full technical appendix + claim skeletons |
| [ONE_PAGE_101_DEFENSE.md](ONE_PAGE_101_DEFENSE.md) | Focused 101/abstractness rebuttal |
| [ATTORNEY_SCREENSHARE_SCRIPT.md](ATTORNEY_SCREENSHARE_SCRIPT.md) | Detailed 5-min demo script |

---

## 🔑 Key Inventive Aspects

1. **Variance feature vector** derived from hierarchical JSON diff
2. **Classification of deltas** into QoE-impacting vs QoE-neutral
3. **Policy engine** applying risk to CI/CD gating decisions
4. **Explainable contribution scores** for changed JSON paths
5. **Audit trail** with run persistence and evidence

---

## 💡 Why This Is Not Abstract

The claims can recite:
- Specific change record types (added/removed/type_changed/value_changed)
- Specific variance signals (structural drift counts, type flips, array cardinality variance, numeric delta features)
- Specific outputs (risk score + pass/warn/fail gating + evidence identifying paths)
- Concrete deployment context (streaming endpoint validation, CI/CD gating)

---

## 📞 Next Steps

1. Schedule 30-min call with counsel
2. Run demo live (5 minutes)
3. Review claim skeletons in `PATENT_REVISIT_PACKET.md`
4. Discuss narrowing strategy if needed
