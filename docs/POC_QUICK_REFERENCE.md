# QoE-Guard POC - Quick Reference

## 🚀 Quick Start

```bash
# Start everything
./scripts/poc_demo.sh

# Or manually
docker compose up -d --build
```

## 📍 Service URLs

| Service | URL |
|---------|-----|
| **QoE-Guard UI** | http://localhost:8010 |
| **Demo Target API** | http://localhost:8001 |
| **API Docs** | http://localhost:8010/docs |
| **OpenAPI Spec** | http://localhost:8001/openapi.json |

## 🎯 Demo Scenarios

| Version | Risk Level | URL | Expected Result |
|---------|------------|-----|-----------------|
| v=1 | Baseline | `/run?v=1` | No changes |
| v=3 | **PASS** | `/run?v=3` | Minor safe changes |
| v=2 | **WARN** | `/run?v=2` | Moderate changes |
| v=4 | **FAIL** | `/run?v=4` | Breaking changes |

## 📋 Common Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f qoe-guard
docker compose logs -f demo-target

# Restart services
docker compose restart

# Run automated scenarios
python scripts/poc_scenarios.py

# Seed baseline
curl http://localhost:8010/seed
```

## 🔗 Key Endpoints

### QoE-Guard
- `GET /` - Dashboard
- `GET /seed` - Seed baseline
- `GET /run?v={n}` - Run validation
- `GET /runs` - List runs
- `GET /runs/{id}/report` - View report
- `GET /swagger` - Swagger analyzer
- `GET /docs` - API documentation

### Demo Target
- `GET /play?v={n}` - Get playback config
- `GET /openapi.json` - OpenAPI spec

## 📊 Score Ranges

### Risk Score (0.0 - 1.0)
- **0.0 - 0.44**: PASS
- **0.45 - 0.71**: WARN
- **0.72 - 1.0**: FAIL

### Brittleness Score (0 - 100)
- **0 - 30**: Low (stable)
- **31 - 60**: Medium
- **61 - 100**: High (fragile)

### QoE Risk Score (0.0 - 1.0)
- **0.0 - 0.44**: Low impact
- **0.45 - 0.71**: Medium impact
- **0.72 - 1.0**: High impact

## 🎬 Demo Flow

```
1. Start: ./scripts/poc_demo.sh
   ↓
2. Seed: http://localhost:8010/seed
   ↓
3. Run PASS: http://localhost:8010/run?v=3
   ↓
4. Run WARN: http://localhost:8010/run?v=2
   ↓
5. Run FAIL: http://localhost:8010/run?v=4
   ↓
6. Review: http://localhost:8010/runs
```

## 🔍 What to Look For

### PASS Scenario (v=3)
- ✅ Risk Score: 0.15-0.25
- ✅ Changes: 1-2 (minor additions)
- ✅ All critical paths intact

### WARN Scenario (v=2)
- ⚠️ Risk Score: 0.45-0.65
- ⚠️ Type changes detected
- ⚠️ Critical fields modified

### FAIL Scenario (v=4)
- ❌ Risk Score: 0.75-0.95
- ❌ Major structural changes
- ❌ Multiple breaking changes

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| Services not starting | `docker compose up -d --build` |
| Connection refused | Wait 30s, check `docker compose ps` |
| No scenarios found | Run `curl http://localhost:8010/seed` |
| Internal Server Error | Check logs: `docker compose logs qoe-guard` |

## 📝 Key Features

- ✅ Hierarchical JSON diff
- ✅ QoE-aware scoring
- ✅ Brittleness analysis
- ✅ Drift classification
- ✅ Policy-based gating
- ✅ Baseline governance
- ✅ Swagger discovery
- ✅ AI/ML analysis (optional)

## 🎯 Critical Paths

Fields that directly impact QoE:
- `playback.manifestUrl` - Video URL
- `drm.licenseUrl` - DRM server
- `entitlement.allowed` - Access control
- `ads.adDecision` - Ad configuration

## 📈 Expected Results

| Scenario | Risk | Brittleness | QoE Risk | Decision |
|----------|------|-------------|----------|----------|
| v=3 (PASS) | 0.15-0.25 | 10-20 | 0.10-0.20 | PASS |
| v=2 (WARN) | 0.45-0.65 | 40-60 | 0.45-0.60 | WARN |
| v=4 (FAIL) | 0.75-0.95 | 70-90 | 0.75-0.90 | FAIL |

## 🔄 Cleanup

```bash
# Stop and remove containers
docker compose down

# Remove all data
docker compose down -v
rm -rf data/*.json
```

## 📚 Documentation

- **Full POC Guide**: `docs/POC_GUIDE.md`
- **App Walkthrough**: `docs/APP_WALKTHROUGH.md`
- **API Docs**: http://localhost:8010/docs
- **README**: `README.md`

---

**Quick Tip**: Bookmark http://localhost:8010 for easy access during demos!
