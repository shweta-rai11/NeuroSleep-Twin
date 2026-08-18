# NeuroSleep Twin

**Mapping how the sleeping brain responds to disrupted breathing.**

NeuroSleep Twin is a research-grade platform for studying how the brain, heart, and blood oxygen respond to individual respiratory disturbances during sleep — not just how often those disturbances happen.

> **NeuroSleep Twin is a computational neuroscience platform for investigating how respiratory disturbances during sleep interact with cortical, autonomic, oxygenation, and recovery dynamics.**
> The central innovation is **event-level neuro-respiratory phenotyping, rather than event counting alone.**

---

## ⚠️ Research Prototype — read this first

This application is a **research prototype**. It is designed for research and educational exploration of sleep physiology. It does **not** independently diagnose obstructive sleep apnea or neurological disease, and it does **not** replace professional interpretation of polysomnography or other medical assessments.

It must never be used to:
- Diagnose sleep apnea or any neurological disease
- Prescribe or adjust CPAP or any treatment
- Change medication
- Claim brain damage, glymphatic dysfunction, or precise brain-region activation
- Make automated treatment decisions

Every screen that shows an inferred or modeled result must clearly label it as one of:

| Label | Meaning |
|---|---|
| **Observed measurement** | Directly recorded signal value (e.g., raw SpO2 reading) |
| **Derived physiological metric** | Calculated from observed signals using a defined formula (e.g., oxygen desaturation index) |
| **Machine-learning estimate** | Output of a statistical/ML model, with a version and confidence (e.g., candidate respiratory event) |
| **Research hypothesis** | A pattern surfaced by analysis or the AI research assistant, not a clinical claim |

---

## 1. What this project is

NeuroSleep Twin ingests **real physiological sleep data** — either from public research datasets (e.g., PhysioNet's MIT-BIH Polysomnographic Database) or from a user's own uploaded sleep study — and runs it through **one shared analysis pipeline** that:

1. Detects sleep stages and candidate respiratory events
2. Measures the oxygen, cardiovascular ("autonomic"), and — where EEG is available — cortical response around each event
3. Builds a per-event **"fingerprint"** (a normalized feature vector) describing how the brain and body reacted
4. Clusters events/patients into descriptive **neuro-respiratory phenotypes**
5. Benchmarks predictions against known annotations on public datasets
6. Lets a user compare their own study against public research cohorts
7. Explains results with an LLM that only narrates structured, already-computed pipeline output — it never reasons directly over raw signals

The same pipeline runs for public data and user data, so results are comparable and reproducible.

### What it deliberately is *not*
- Not a simple "AHI calculator" or apnea/hypopnea auto-scorer
- Not a diagnostic device or a substitute for a sleep physician
- Not a system that lets an LLM freely query the database or invent biological claims

---

## 2. Two data modes

### Mode A — Explore Public Dataset
A curated catalog of openly licensed sleep research datasets (starting with **MIT-BIH Polysomnographic Database** from PhysioNet). Every dataset entry records its source URL, version, license, citation, and checksum, and analyses always display dataset source, version, license, citation, and access date.

### Mode B — Upload Your Sleep Study
Users can upload their own recordings (EDF / EDF+ / WFDB / CSV + JSON metadata). Uploaded files go through format detection → channel mapping → signal-quality QC → the same analysis pipeline used for public data.

**Data policy:** user-uploaded data is private by default and is **never** used to train models unless the user explicitly opts in under an appropriate consent/governance framework. This is always visible in the UI.

---

## 3. High-level architecture

```
                     React + TypeScript (Vite, Tailwind, shadcn/ui)
                     Plotly (scientific plots) · D3 (timelines) · Three.js (digital twin)
                                        │
                                        ▼
                              FastAPI (REST API)
                                        │
                                        ▼
                         Redis-backed task queue (Celery/RQ)
                                        │
                                        ▼
                       Scientific worker (NumPy / SciPy / Pandas /
                     WFDB / MNE / NeuroKit2 / scikit-learn / XGBoost / SHAP)
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                                ▼
              PostgreSQL (metadata, events,     S3-compatible object storage
              annotations, phenotypes, models)  (raw + processed waveforms, reports)
```

Long-running signal processing (minutes to hours of physiological data) always runs asynchronously in the worker — the API never blocks a browser request on it.

### Standard internal data model

Every dataset — public or user-uploaded — is normalized into the same schema before analysis:

```
Study
 ├── metadata
 ├── channels
 ├── signals            (raw, immutable + processed, versioned)
 ├── annotations
 ├── sleep_stages
 ├── respiratory_events
 ├── arousal_events
 ├── oxygen_events
 ├── autonomic_events
 └── derived_features
```

The original uploaded/downloaded signal is **never overwritten**; processed versions are stored alongside it.

---

## 4. Repository layout

```
SleepApnea/
├── frontend/                  React + TypeScript app
│   └── src/
│       ├── pages/              One folder per major screen (datasets, upload,
│       │                       channel-mapping, qc, viewer, events, sleep-staging,
│       │                       brain-response, autonomic, oxygen-burden, beyond-ahi,
│       │                       phenotyping, benchmark-lab, longitudinal,
│       │                       research-assistant, reports, digital-twin, settings)
│       ├── components/         Reusable UI: synchronized viewer, charts, night-map,
│       │                       event fingerprint (radar chart), digital-twin (Three.js)
│       ├── api/                Typed API client
│       ├── store/, hooks/, types/, utils/, styles/
│       └── tests/
│
├── backend/                   FastAPI application
│   └── app/
│       ├── api/v1/endpoints/   REST endpoints (see API section below)
│       ├── core/               config, security, logging
│       ├── db/models/          SQLAlchemy ORM models
│       ├── db/migrations/      Alembic migrations
│       ├── schemas/            Pydantic request/response schemas
│       ├── services/           One folder per pipeline stage:
│       │                       ingestion, channel_mapping, qc, preprocessing,
│       │                       sleep_staging, respiratory_events, oxygen_burden,
│       │                       brain_response, autonomic_response, fingerprint,
│       │                       phenotyping, benchmarking, longitudinal,
│       │                       explainability, digital_twin, reports
│       ├── worker/tasks/       Celery/RQ background jobs
│       └── storage/            S3-compatible object storage client
│   └── tests/{unit,integration}/
│
├── scientific/                 neuroresp: importable, API-independent science library
│   └── neuroresp/
│       ├── preprocessing/      resampling, filtering, artifact rejection, normalization
│       ├── features/           respiratory/, oxygen/, eeg/, autonomic/ extractors
│       ├── events/              respiratory/arousal event detection
│       ├── fingerprint/         normalized per-event feature vectors
│       ├── phenotyping/         PCA/UMAP/clustering (k-means, HDBSCAN, hierarchical)
│       ├── models/              baseline + advanced models (interpretable-first)
│       └── validation/          patient-level splits, benchmarking, leakage checks
│   └── notebooks/, tests/
│
├── data/
│   ├── datasets/
│   │   ├── registry/            Dataset catalog metadata (name, source, license, citation)
│   │   └── mitbih-psg/          raw/ (downloaded, gitignored) + processed/
│   ├── uploads/                 User-uploaded studies (private, gitignored)
│   └── processed/                Processed outputs (gitignored)
│
├── infra/
│   ├── docker/                  Dockerfiles for frontend/backend/worker
│   └── ci/                      CI pipeline config
│
├── docs/
│   ├── architecture/            System design docs
│   ├── api/                     API reference
│   ├── research/                Research notes, methodology write-ups
│   └── report-templates/        Exportable research-report templates
│
└── scripts/
    ├── dataset_import/          CLI scripts to import/validate public datasets
    └── dev/                     Local dev helper scripts
```

Every currently-empty folder contains a `.gitkeep` placeholder so the structure is preserved in version control until real files land in it.

---

## 5. Core pipeline (same for public & user data)

```
Choose Public Dataset  OR  Upload Real Study
        │
        ▼
Format detection → Channel mapping (editable, confidence-scored) → QC / readiness score
        │
        ▼
Preprocessing (resample, filter, artifact-reject) — raw kept immutable
        │
        ▼
Sleep staging (hypnogram)  →  Respiratory event detection (candidate events)
        │
        ▼
Per-event extraction: oxygen (nadir, desaturation slope, recovery) ·
autonomic (HR response, HRV) · cortical/EEG response (if available) · context
        │
        ▼
Event fingerprint (normalized feature vector, radar-chart comparison)
        │
        ▼
Phenotyping (PCA/UMAP + clustering → descriptive, renamable phenotype labels)
        │
        ▼
Benchmarking (vs. dataset annotations) · Longitudinal analysis (multi-night)
        │
        ▼
Public cohort comparison  →  AI explanation (narrates structured results only)
        │
        ▼
Exportable Research Report (with full provenance)
```

Key screens built on top of this pipeline: the **Night Map** (click any point to jump to that event's synchronized raw signals), **Beyond AHI** (compares AHI/ODI against oxygen/arousal/autonomic/recovery burden — explicitly framed as *exploring* physiology alongside AHI, not replacing it), the **Benchmark Lab** (sensitivity/specificity/AUROC/AUPRC/calibration/confusion matrix vs. ground-truth annotations), and a conceptual **3D brain–body digital twin** (Three.js) that animates the respiratory → oxygen/effort → EEG → autonomic → recovery cascade — explicitly labeled as a conceptual model, not a visualization of real-time neuronal activity.

---

## 6. Validation & reproducibility rules (non-negotiable)

- **Patient-level splits only.** A person never appears in both train and test; multiple nights from the same person stay in one split unless the analysis is explicitly a longitudinal generalization study.
- **Dataset-level validation.** Train / validation / external-test use separate datasets where possible — never a random shuffle across all datasets.
- **No invented numbers.** If a model hasn't been run, the UI states "No benchmark available" rather than showing placeholder metrics.
- **Every analysis is versioned**: model version, pipeline version, feature-set version, dataset version, parameters, and random seed are all recorded so any result can be reproduced with a single "Reproduce analysis" action.

---

## 7. Tech stack

| Layer | Choices |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Plotly, D3, Three.js |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Redis, Celery/RQ |
| Scientific | NumPy, SciPy, Pandas, WFDB, MNE, NeuroKit2, scikit-learn, XGBoost, PyTorch (only where deep learning is justified), SHAP, Statsmodels |
| Storage | PostgreSQL for metadata/relations; S3-compatible object storage for raw/processed waveforms and reports |

---

## 8. Build order (roadmap)

The project is built incrementally — never all at once:

- [x] **Phase 1** — Application shell
- [x] **Phase 2** — Public dataset ingestion (MIT-BIH PSG via PhysioNet)
- [x] **Phase 3** — Real file upload
- [x] **Phase 4** — Channel mapping
- [x] **Phase 5** — Signal QC / readiness score
- [x] **Phase 6** — Synchronized signal viewer
- [x] **Phase 7** — Respiratory event analysis
- [x] **Phase 8** — Sleep staging
- [x] **Phase 9** — EEG brain-response analysis
- [x] **Phase 10** — Autonomic analysis
- [x] **Phase 11** — Event fingerprint
- [x] **Phase 12** — Phenotyping
- [x] **Phase 13** — Benchmarking (Benchmark Lab)
- [x] **Phase 14** — Longitudinal analysis
- [x] **Phase 15** — AI explanation (structured-output-only)
- [x] **Phase 16** — Digital twin (Three.js)
- [x] **Phase 17** — Research report export
- [x] **Phase 18** — Security & deployment (basics — see §11 for what's still deployment-time work)

**First demo target:** load a real MIT-BIH PSG record → view EEG/ECG/respiration with annotations → detect respiratory events → show event-centered EEG response → generate fingerprints → cluster events → produce a Neuro-Respiratory Profile → show the Night Map → export a report. Then repeat the same pipeline on an uploaded user study and compare against the public cohort.

---

## 9. Getting started

All 18 phases above are implemented and run locally. One-time setup:

```bash
# Postgres: create the role/db (adjust if you already have Postgres running differently)
psql postgres -c "CREATE ROLE neurosleep WITH LOGIN PASSWORD 'neurosleep';"
psql postgres -c "CREATE DATABASE neurosleep OWNER neurosleep;"

# Redis (macOS)
brew install redis && brew services start redis

# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in API_AUTH_TOKEN etc. — see §11
alembic upgrade head

# Frontend
cd frontend
npm install
cp .env.example .env   # VITE_API_TOKEN must match backend's API_AUTH_TOKEN
```

Then either run `./scripts/dev/start.sh` from the repo root, or start each piece yourself:

```bash
# Backend (from backend/)
uvicorn app.main:app --reload

# Worker (from backend/)
celery -A app.worker.celery_app worker --loglevel=info

# Frontend (from frontend/)
npm run dev
```

Open http://localhost:5173 — Dashboard → Public Datasets → pick a MIT-BIH PSG record (downloads once from PhysioNet, ~1-2 min) → the rest of the pipeline runs from there.

---

## 10. Data sources & licensing

Public datasets are only ever pulled from **official, institutionally maintained sources** (PhysioNet, NIH repositories, official research repositories) with clear licenses — never scraped from arbitrary websites, and never a restricted dataset downloaded automatically. Every dataset record stores `source_url`, `dataset_name`, `version`, `license`, `citation`, `download_date`, and `checksum`, and every analysis built on it displays that provenance.

**Initial dataset:** [MIT-BIH Polysomnographic Database](https://physionet.org/content/slpdb/) (PhysioNet) — ECG, EEG, and respiration recordings with sleep-stage and apnea-related annotations.

---

## 11. Security & privacy defaults

Implemented today:
- Uploaded data is private and **not** used for model training by default
- A shared-secret Bearer token (`API_AUTH_TOKEN`) gates every endpoint except `/health` when set — this is single-operator authentication, not a multi-user identity system
- Every mutating request (upload, ingest, delete, mapping edit, relabeling) is written to an append-only `audit_log` table, viewable at `GET /api/v1/audit-log`
- File-type extension checks plus content-signature verification (EDF header, ZIP magic bytes, JSON parseability) gate uploads before they touch disk
- Users can delete their studies and data at any time (`DELETE /api/v1/studies/{id}`, wired into the UI)

Still deployment-time work, not implemented here:
- Real malware/AV scanning of uploaded files (the signature checks above catch spoofed extensions, not malicious payloads)
- Per-user accounts/authorization (today's token is all-or-nothing access, appropriate for one operator running this locally)
- TLS — this app assumes a local, trusted network; putting it behind HTTPS is a reverse-proxy concern for whoever deploys it beyond localhost

---

## 12. Positioning

NeuroSleep Twin does not say *"we diagnose sleep apnea using AI."* It says:

> *"NeuroSleep Twin is a computational neuroscience platform for investigating how respiratory disturbances during sleep interact with cortical, autonomic, oxygenation, and recovery dynamics."*

Clinical validation and any regulated medical-device claims come only after appropriate validation, governance, and regulatory assessment — this is a research platform first.
