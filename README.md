# NeuroSleep Twin

A research tool for looking at what actually happens in the body around a breathing disturbance during sleep — not just how many of them there were.

Most sleep-apnea tools stop at AHI: count the events, divide by hours. Two people can post the same AHI and have completely different nights — one person's oxygen barely dips, the other's crashes and takes minutes to recover. This project tries to look at that difference instead of collapsing it into one number. For every candidate respiratory event it pulls together the oxygen response, the heart-rate/HRV response, and (when EEG is available) the cortical response into a per-event fingerprint, and clusters those fingerprints into descriptive phenotypes.

It runs on public PSG data (PhysioNet's MIT-BIH Polysomnographic Database) or on a study you upload yourself, through the same pipeline, so the two are actually comparable.

## Read this before using it

This is a research prototype, not a medical device. It does not diagnose sleep apnea or any neurological condition, and it is not a substitute for a real sleep study read by a physician.

Don't use it to:
- diagnose sleep apnea or any other condition
- decide on or adjust CPAP or any other treatment
- change medication
- make claims about brain damage, glymphatic function, or which brain regions did what
- make an automated treatment decision of any kind

Every result the UI shows is labeled with what kind of claim it actually is, because these are not the same thing and shouldn't be presented as if they were:

| Label | What it means |
|---|---|
| Observed measurement | A signal value as recorded — e.g. a raw SpO2 reading |
| Derived physiological metric | Computed from observed signals with a defined formula — e.g. oxygen desaturation index |
| Machine-learning estimate | Output of a model, versioned, with a confidence — e.g. a candidate respiratory event |
| Research hypothesis | A pattern the analysis or the AI assistant surfaced — not a clinical claim |

The AI research assistant only narrates numbers the pipeline already computed; it doesn't get to reason over raw signals or invent a finding. Its system prompt says not to make diagnostic or treatment claims, and since a prompt is not an enforcement mechanism on its own, its output also gets scanned for phrases like "you have sleep apnea" or "you should start CPAP" — if one slips through, that response is swapped for a deterministic template answer instead of being shown as-is.

## What it does

**Public data.** A small catalog of openly licensed sleep datasets, starting with MIT-BIH PSG from PhysioNet. Every entry keeps its source URL, version, license, citation, and checksum, and every analysis built from it shows that provenance.

**Your own data.** Upload a sleep study as EDF/EDF+, WFDB, or CSV+JSON, and it goes through the same format detection → channel mapping → QC → analysis pipeline as the public datasets. Uploads are private by default and never used for training without explicit opt-in.

**Personal recordings, no PSG hardware.** `personal-sleep-tracker/` is a phone-only path: a self-contained HTML page records breathing-sound loudness and motion overnight (never raw audio — just a numeric loudness level), and the result can be run through either the real app or a standalone live-replay viewer using the same event detector. It's explicitly a screening/tracking tool, not a diagnostic one — a phone mic isn't a calibrated sensor, and the app is upfront everywhere that oxygen, heart rhythm, and brain activity just aren't measured this way. A related acoustic-analysis pipeline (`backend/app/services/acoustic/`) picks up breathing pauses from an uploaded audio/video recording directly, kept separate from the real EEG/ECG/SpO2 pipeline and labeled as a much rougher proxy.

**Apple Health import.** If you export your data from the Health app (Settings → your name → Export All Health Data), the app can pull out one night at a time: sleep stages come in as real annotations (Apple's own classifier, labeled as such — it's accelerometer + heart rate, not EEG), and heart rate / SpO2 / respiratory rate come in as viewable channels. Those channels are deliberately left unmapped rather than fed into the respiratory-event detector — Apple Watch gives you a spot-check every so often, not a continuous waveform, and running a detector built for a real effort belt against once-a-minute numbers just manufactures fake events out of noise.

**Cardiovascular context.** The live-replay viewer includes a panel that maps your detected-event rate onto AASM AHI severity bands and shows what four real cohort studies (Peppard 2000, the Sleep Heart Health Study, Marin 2005, Punjabi 2009) found at that band — population-level context with citations, not a personal risk score, since building an actual personalized model would need outcome-labeled data this project doesn't have.

## Architecture

```
                     React + TypeScript (Vite, Tailwind, shadcn/ui)
                     Plotly (scientific plots) · D3 (timelines) · Three.js (digital twin)
                                        │
                                        ▼
                              FastAPI (REST API)
                                        │
                                        ▼
                         Redis-backed task queue (Celery)
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

Signal processing runs asynchronously in the Celery worker — the API never blocks a request on it. Every dataset, public or uploaded, normalizes into the same schema (study → channels → signals → annotations → sleep stages → respiratory/arousal/oxygen/autonomic events → derived features) before anything downstream touches it, and the original signal is never overwritten — processed versions live alongside it.

## Repository layout

```
SleepApnea/
├── frontend/src/
│   ├── pages/                 one folder per screen: datasets, upload, channel-mapping,
│   │                          qc, viewer, events, sleep-staging, brain-response,
│   │                          autonomic, oxygen-burden, beyond-ahi, phenotyping,
│   │                          benchmark-lab, longitudinal, research-assistant,
│   │                          reports, digital-twin, settings
│   ├── components/            synchronized viewer, charts, night-map,
│   │                          event fingerprint (radar chart), digital twin (Three.js)
│   └── api/, store/, hooks/, types/, utils/, tests/
│
├── backend/app/
│   ├── api/v1/endpoints/      REST endpoints
│   ├── db/models/, db/migrations/, schemas/
│   ├── services/              one folder per pipeline stage — ingestion, channel_mapping,
│   │                          qc, preprocessing, sleep_staging, respiratory_events,
│   │                          oxygen_burden, brain_response, autonomic_response,
│   │                          acoustic, fingerprint, phenotyping, benchmarking,
│   │                          longitudinal, explainability, digital_twin, reports
│   └── worker/tasks/, storage/
│
├── scientific/neuroresp/      importable science library, no API dependency
│   ├── preprocessing/, features/, events/, fingerprint/
│   ├── phenotyping/           PCA/UMAP + clustering
│   └── models/, validation/   patient-level splits, benchmarking, leakage checks
│
├── personal-sleep-tracker/    phone recorder + standalone live-replay viewer
├── data/                      datasets/, uploads/, processed/ — all gitignored except registry metadata
├── infra/                     Dockerfiles, CI config
├── docs/                      architecture, API reference, research notes, report templates
└── scripts/
    ├── dataset_import/        CLI scripts to import/validate public datasets
    └── dev/                   local dev helpers, including the live-replay demo server
```

## Pipeline

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

A few screens worth knowing about: the **Night Map** lets you click any point and jump to that event's synchronized raw signals; **Beyond AHI** lines up AHI/ODI against oxygen, arousal, autonomic, and recovery burden side by side — every one of those numbers is a straight aggregation of what the pipeline already computed, nothing new gets detected for it, and a dimension with no matching channel says so instead of showing a fabricated zero; the **Benchmark Lab** shows sensitivity/specificity/AUROC/AUPRC/calibration against ground-truth annotations; and there's a conceptual 3D brain-body **digital twin** (Three.js) that animates the respiratory → oxygen/effort → EEG → autonomic → recovery cascade — labeled as a conceptual model, not real-time neuronal activity, because it isn't one.

## Validation rules I'm not willing to bend on

- **Patient-level splits.** A person never shows up in both train and test; multiple nights from the same person stay together unless the analysis is explicitly about longitudinal generalization.
- **Dataset-level validation.** Train/validation/external-test come from separate datasets where possible, not a random shuffle across everything.
- **No invented numbers.** If something hasn't been computed, the UI says "not available," not a placeholder metric.
- **Everything is versioned** — model, pipeline, feature set, dataset, parameters, random seed — so any result can be reproduced with one action.

## Tech stack

| Layer | Choices |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Plotly, D3, Three.js |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Redis, Celery |
| Scientific | NumPy, SciPy, Pandas, WFDB, MNE, NeuroKit2, scikit-learn, XGBoost, PyTorch where deep learning is actually justified, SHAP, Statsmodels |
| Storage | PostgreSQL for metadata/relations, S3-compatible object storage for raw/processed waveforms and reports |
| Other | ffmpeg (audio/video upload decoding), Ollama (local LLM for the research assistant) |

## What's built

The core app went in as 18 sequential phases, referenced by number in code comments where it's useful context (e.g. `upload.py` still says "Phase 3's real upload pipeline"):

1. Application shell
2. Public dataset ingestion (MIT-BIH PSG via PhysioNet)
3. Real file upload
4. Channel mapping
5. Signal QC / readiness score
6. Synchronized signal viewer
7. Respiratory event analysis
8. Sleep staging
9. EEG brain-response analysis
10. Autonomic analysis
11. Event fingerprint
12. Phenotyping
13. Benchmarking (Benchmark Lab)
14. Longitudinal analysis
15. AI explanation (structured-output-only)
16. Digital twin (Three.js)
17. Research report export
18. Security & deployment basics (see below for what's still missing)

Since then: Beyond AHI went from stub to real aggregation, audio/video upload + acoustic pause detection, the personal phone-recorder tracker with its own live-replay viewer, the cardiovascular-risk-context panel, an Apple Health import path, and an output-side overclaim guard on the research assistant.

**First demo target** was: load a real MIT-BIH PSG record, view EEG/ECG/respiration with annotations, detect respiratory events, show event-centered EEG response, generate fingerprints, cluster events, produce a neuro-respiratory profile, show the Night Map, export a report — then do the same on an uploaded study and compare it against the public cohort. That path works end to end today.

## Getting started

```bash
# Postgres: create the role/db (adjust if you already run Postgres differently)
psql postgres -c "CREATE ROLE neurosleep WITH LOGIN PASSWORD 'neurosleep';"
psql postgres -c "CREATE DATABASE neurosleep OWNER neurosleep;"

# Redis (macOS)
brew install redis && brew services start redis

# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in API_AUTH_TOKEN etc. — see "Security & privacy" below
alembic upgrade head

# Frontend
cd frontend
npm install
cp .env.example .env   # VITE_API_TOKEN must match backend's API_AUTH_TOKEN
```

Audio/video upload and acoustic analysis also need `ffmpeg`/`ffprobe` on PATH (`brew install ffmpeg`).

Then either run `./scripts/dev/start.sh` from the repo root, or start each piece yourself:

```bash
# Backend (from backend/)
uvicorn app.main:app --reload

# Worker (from backend/)
celery -A app.worker.celery_app worker --loglevel=info

# Frontend (from frontend/)
npm run dev
```

Open http://localhost:5173 — Dashboard → Public Datasets → pick a MIT-BIH PSG record (downloads once from PhysioNet, ~1-2 min) and the rest of the pipeline runs from there.

## Data sources & licensing

Public datasets only ever come from official, institutionally maintained sources (PhysioNet, NIH repositories, official research repositories) with clear licenses — never scraped, never a restricted dataset pulled automatically. Every dataset record stores `source_url`, `dataset_name`, `version`, `license`, `citation`, `download_date`, and `checksum`, and every analysis built on it shows that provenance.

**Initial dataset:** [MIT-BIH Polysomnographic Database](https://physionet.org/content/slpdb/) (PhysioNet) — ECG, EEG, and respiration recordings with sleep-stage and apnea-related annotations.

## Security & privacy

What's actually in place:
- uploaded data is private and not used for model training by default
- a shared-secret bearer token (`API_AUTH_TOKEN`) gates every endpoint except `/health` when set — this is single-operator auth, not a multi-user identity system
- every mutating request (upload, ingest, delete, mapping edit, relabeling) is written to an append-only `audit_log` table, viewable at `GET /api/v1/audit-log`
- file-type extension checks plus content-signature verification (EDF header, ZIP magic bytes, JSON parseability, a real decodable audio stream) gate uploads before they touch disk
- you can delete your studies and data at any time (`DELETE /api/v1/studies/{id}`, wired into the UI)

What's still deployment-time work, not something this repo does for you:
- real malware/AV scanning of uploads (the checks above catch spoofed extensions, not malicious payloads)
- per-user accounts — today's token is all-or-nothing, which is fine for one person running this locally and not fine for anything more
- TLS — this assumes a local, trusted network; putting it behind HTTPS is on whoever deploys it beyond localhost

## Where this sits

This doesn't claim to diagnose sleep apnea with AI. What it's actually trying to do is look at how an individual's brain, heart, and blood oxygen respond to each of their own respiratory disturbances — not just count how many happened — and keep that clearly separated from anything resembling a clinical claim. Real validation, and any regulated medical-device claim, is a separate and much later step that this project hasn't taken.
