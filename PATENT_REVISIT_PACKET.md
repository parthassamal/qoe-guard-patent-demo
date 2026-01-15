## QoE-Guard — Patent Revisit Packet (reduction to practice + 101 defense + claim-ready detail)

### 1) Executive summary (what the invention is)
**QoE-Guard** is a system for **validating streaming API responses** by measuring **hierarchical JSON variance** versus a stored baseline scenario and predicting **QoE risk** to gate releases with an explicit **PASS/WARN/FAIL** decision and an explainable report.

This is not “just an idea.” The prototype implements specific data structures and processing steps that (a) compute structural/value drift over nested payloads, (b) convert drift into engineered signals, (c) compute a risk score and policy decision, and (d) persist and present auditable evidence.

### 2) Reduction to practice (what exists today)
The repository contains a runnable prototype demonstrating the full pipeline:

- **Scenario repository (baseline capture + storage)**: stores baseline response JSON per endpoint and tags/time metadata.  
  - Code: `qoe_guard/storage.py`
- **Canonical hierarchical JSON diff**: emits path-level change records (added/removed/type_changed/value_changed) and array-length markers.  
  - Code: `qoe_guard/diff.py`
- **Variance feature extractor**: transforms change records into a compact “variance feature vector” (structural drift counts, numeric delta stats, array cardinality variance, critical-path changes).  
  - Code: `qoe_guard/features.py`
- **QoE-aware risk scoring + policy engine**: computes risk score and applies explicit thresholds/overrides to output PASS/WARN/FAIL plus top signals.  
  - Code: `qoe_guard/model.py`
- **Validation server + explainable report UI**: orchestration (fetch baseline, fetch candidate, diff, featurize, score), run persistence, and report rendering.  
  - Code: `qoe_guard/server.py`, templates in `qoe_guard/templates/`
- **Controlled target endpoint (versioned candidate responses)**: stable baseline v1 and intentionally drifted v2 (type flips, critical-field changes, add/remove, numeric delta, etc.).  
  - Code: `demo_target_service.py`
- **Run instructions**: quick start and demo flow for a live screen-share.  
  - Doc: `README_PATENT_DEMO.md`

### 3) Technical problem and technical improvement
**Problem:** Streaming clients (players, entitlement/DRM flows, ad decisioning, playback configuration) are sensitive to server-side response drift. Conventional validation (schema checks, unit tests, static type checks) often fails to catch **QoE-impacting** drift because:
- drift can be **structural** (added/removed paths, type flips) and **value-based** (numeric deltas) inside nested payloads,
- “schema-valid” changes can still be QoE-bad (e.g., bitrate caps, start position, DRM/license URL path changes, ad object removals),
- teams need **auditable evidence** and gating decisions for CI/CD.

**Improvement:** QoE-Guard introduces an automated pipeline that:
- computes **hierarchical diffs** over real baseline scenarios,
- derives a **variance feature vector** capturing drift severity and criticality,
- infers a **QoE risk score** and applies policy thresholds to gate releases,
- produces **explainable, field-level evidence** and stores run artifacts for audit.

This is a concrete improvement to API validation and deployment safety in a streaming computer/network system.

### 4) System architecture (claim-friendly)
- **Scenario repository**: stores baseline scenarios for one or more endpoints (baseline payload + metadata).
- **Candidate fetcher**: obtains candidate payloads from a target service (test, staging, canary, production shadow).
- **Hierarchical diff engine**: generates change records keyed by JSON path, classifying change types and capturing before/after values.
- **Variance feature extractor**: converts change records into a feature vector; includes drift counts, numeric delta stats, array cardinality variance, and “critical path” indicators.
- **QoE risk scoring model**: produces a risk score; may be rule-based, weighted linear model, learned model, or hybrid.
- **Policy engine**: applies thresholds/overrides to yield PASS/WARN/FAIL and recommended remediation.
- **Explainer/report generator**: produces human-readable and machine-readable evidence, including top contributing paths/signals and diffs.
- **Audit log/run store**: persists runs, features, decision outputs, and evidence for traceability and governance.

### 5) Concrete example (what the demo shows)
The target endpoint `/play` returns:
- **v1 baseline**: stable response with nested objects for playback/DRM/entitlement/ads/metadata.
- **v2 candidate**: introduces drift such as:
  - type change (`maxBitrateKbps` number → string),
  - critical field change (`manifestUrl` changed),
  - removed object (`ads.adDecision` removed),
  - added fields (`playback.lowLatencyMode`, entitlement region policy, metadata audioTracks),
  - numeric delta (`startPositionSec` changed).

QoE-Guard detects these path-level deltas, extracts drift features, computes a risk score, and gates with PASS/WARN/FAIL while producing a report with evidence.

### 6) Claim vocabulary (reusable phrasing)
Non-exhaustive phrases aligned to the implemented mechanics:
- “**variance feature vector** derived from hierarchical structured response payloads”
- “classification of response deltas into **QoE-impacting** versus QoE-neutral”
- “policy engine applying risk to **CI/CD gating decisions**”
- “**explainable contribution scores** for changed JSON paths”
- “canonical diff records comprising (path, change_type, before, after)”
- “array cardinality variance represented by **length-marker paths**”

### 7) Draft claim skeletons (high-level, counsel-ready starting point)
These are intentionally broad-but-technical; counsel can narrow to the best novelty.

#### 7.1 Independent method claim (outline)
A computer-implemented method comprising:
1) storing, in a scenario repository, a baseline structured response payload for an endpoint;  
2) obtaining a candidate structured response payload for the endpoint;  
3) generating, by a hierarchical diff engine, a set of change records keyed by paths within the structured payload, each change record indicating a change type selected from at least added, removed, type-changed, and value-changed;  
4) deriving, from the set of change records, a variance feature vector comprising at least one feature representing structural drift and at least one feature representing value drift;  
5) computing a QoE risk score from the variance feature vector;  
6) applying a policy rule set to the QoE risk score to output a gating decision selected from pass, warn, and fail; and  
7) generating and storing a report comprising the gating decision and evidence identifying one or more paths contributing to the gating decision.

#### 7.2 Independent system claim (outline)
A system comprising one or more processors and memory storing instructions that cause the system to:
- store baseline scenarios; fetch candidate payloads; compute hierarchical diffs; derive a variance feature vector; compute a QoE risk score; apply gating policy; and generate/store an explainable report with path-level evidence.

#### 7.3 Independent non-transitory medium claim (outline)
A non-transitory computer-readable medium storing instructions that when executed perform the method of 7.1.

#### 7.4 Dependent claim ideas (examples)
- criticality: weighting changes under specific path prefixes (e.g., playback/DRM/entitlement/ads) higher than non-critical paths  
- numeric drift: using both numeric delta max and numeric delta sum features  
- array drift: representing array-length drift via explicit length-marker change records  
- explainability: outputting the top-N contributing change records/paths  
- baseline promotion workflow: controlled promotion of candidate payloads to baseline upon satisfaction of criteria and/or human approval  
- multi-baseline: maintaining multiple baselines by device/region/client version/feature flag  
- sampling/shadow traffic: validating canary/shadow responses to prevent rollout regressions

### 8) 101 / “abstractness” rebuttal (practical framing)
**Core position:** The invention is directed to a **specific improvement in computer technology** (API validation and deployment safety in streaming/network systems) implemented through concrete, technical steps and data structures:
- hierarchical diff records keyed by machine-interpretable JSON paths,
- engineered feature vector derived from diffs,
- QoE risk scoring + gating policy thresholds,
- stored audit artifacts and explainable reporting.

It is not a generic “analyze data and decide.” The claims can be drafted to recite:
- particular kinds of change records (added/removed/type/value),
- specific variance signals (structural drift counts, type flips, array cardinality variance, numeric delta features),
- specific outputs (risk score + pass/warn/fail gating + evidence identifying paths),
- and a concrete deployment context (streaming endpoint validation, CI/CD gating, canary/shadow validation).

### 9) Prior art differentiation (talking points)
QoE-Guard is not simply:
- **schema validation** (OpenAPI/JSON schema): schema validity can still allow QoE-bad changes; QoE-Guard uses baseline scenario diff + drift features.  
- **snapshot testing**: snapshot diffs lack risk scoring, criticality weighting, and policy gating with explainability and audit trail.  
- **generic anomaly detection**: QoE-Guard uses engineered drift signals grounded in payload structure and path-level criticality, producing actionable reports for deployment gating.

### 10) Inventor / implementation credibility (use as a cover note, not a claim limitation)
This section is meant for internal/counsel comfort and prosecution narrative; it should not narrow claims.

**AI development | Workflow Automation | LLMs | RAG | Image, Voice AI | Full Stack**

- Open-source first for core components and infra; pragmatic about using best-available tooling when it materially improves quality/safety/time-to-ship (including advanced AI methods; “quantum” where actually relevant to the problem domain).
- Workflow Automation & LLM Integration: Built pipelines connecting Slack, Notion, and internal APIs → reduced response times by 60%.
- RAG Pipelines: hybrid search + custom retrieval → accurate, context-aware responses in production.
- AI Content Detection: Moderation tools using stylometric analysis, embedding similarity, fine-tuned transformers → identify GPT-generated text with high precision.
- Image AI: Tagging & moderation pipeline (CLIP + YOLOv8 on AWS Lambda/S3) → filter thousands of images daily for e-commerce.
- Voice AI: Voice cloning & transcription (Whisper + Tacotron2) → personalized voice assistants with ASR, TTS, and CRM integration.
- Bot development: trading bot, Discord bot, and intelligent bots on multiple platforms.
- Full Stack: Web (React/Next/Node/Laravel/Django + DBs), Mobile (Flutter/React Native/Swift), Cloud/DevOps (AWS/Azure/Docker/K8s).
- LLM Engineering: DSPy, LangChain, AutoGen, CrewAI, ReAct; multi-agent systems; hybrid RAG; multimodal deployments.

### 11) Recommended next steps (to move from “demo” to filing-ready)
- Align on 1–2 best independent claim themes (variance feature vector + QoE gating + explainable path evidence; baseline promotion/audit; multi-baseline context).
- Draft claims narrowly anchored to the implemented mechanics (diff records + features + risk scoring + policy + report).
- Prepare 2–3 additional example payload pairs (beyond `/play`) to show breadth (DRM/license renewal, entitlement denial edge cases, ad decision objects, manifest variants).
- Add a short “production deployment” section: CI/CD integration point, shadow validation, data retention, baseline governance.

### Appendix A) Evidence index (where each mechanism is implemented)
- Scenario repository + persistence (scenarios/runs): `qoe_guard/storage.py` (`upsert_scenario`, `list_scenarios`, `add_run`, `get_run`)
- Baseline seeding + run orchestration: `qoe_guard/server.py` (`/seed`, `/run`, report rendering)
- Hierarchical JSON diff records: `qoe_guard/diff.py` (`Change`, `diff_json`, `_walk`)
- Variance feature vector: `qoe_guard/features.py` (`Features`, `extract_features`, critical path logic)
- QoE risk scoring + gating policy: `qoe_guard/model.py` (`score`, thresholds/overrides)
- Controlled versioned endpoint for demonstration: `demo_target_service.py` (`/play` v1 vs v2)

### Appendix B) “5-minute proof” demo commands (copy/paste)
- Terminal A:
  - `python demo_target_service.py` (serves target API on `127.0.0.1:8001`)
- Terminal B:
  - `uvicorn qoe_guard.server:app --reload --port 8000` (serves validator UI/API on `127.0.0.1:8000`)
- Browser:
  - Open `/` → click “Seed baseline scenario” → run v1 (PASS) → run v2 (WARN/FAIL) → open report and point to: risk score, top signals, and path-level diffs.

