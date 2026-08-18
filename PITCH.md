# NeuroSleep Twin

**Research prototype · Sleep neuroscience**

> Most sleep-apnea tools count how often breathing stops. This one asks what the brain, heart, and blood actually did about it — event by event.

`18/18 build phases implemented` · `Real data: MIT-BIH PSG, PhysioNet` · `React + FastAPI + neuroresp`

---

## The problem: the metric that undersells the disease

The apnea–hypopnea index (AHI) has run sleep medicine for forty years. It counts events per hour and stops there. Two patients can post an identical AHI and live completely different physiological realities — one's oxygen barely dips and recovers in seconds; the other desaturates hard, spikes heart rate, and takes minutes to settle. AHI can't see that difference. It was never built to.

## The insight: score the reaction, not just the event

NeuroSleep Twin re-centers the unit of analysis on the individual event. For every candidate respiratory disturbance, it builds a **fingerprint** — a normalized vector of how oxygen, heart rhythm, and (where EEG exists) cortical activity moved around that moment: depth, timing, recovery speed. Cluster enough fingerprints and phenotypes emerge — descriptive patterns of how a person's brain and body actually respond, independent of raw event count.

```
Event detected  →  Cortical response (EEG)      →  Fingerprint  →  Phenotype
                    Autonomic response (ECG)         (normalized     (descriptive
                    Oxygen response (SpO2)             vector)         cluster)
```

## How it works: one pipeline, two doors in

The same analysis pipeline runs whether the input is a public PhysioNet recording or a user's own upload, so a result is always comparable to the research cohort it came from.

1. **Ingest & QC** — format detection, channel mapping, signal-quality readiness score
2. **Stage & detect events** — hypnogram + candidate respiratory events
3. **Extract per-event response** — oxygen, autonomic, cortical, context
4. **Fingerprint & phenotype** — normalized vectors → PCA/UMAP + clustering
5. **Benchmark & explain** — sensitivity/specificity vs. ground truth, LLM narration of structured output only

## Why it holds up: defensible, not just interesting

- **Reproducibility is enforced, not claimed** — patient-level splits, dataset-level validation, every result versioned and reproducible in one action.
- **The AI explains, it doesn't diagnose** — the LLM only narrates already-computed pipeline output; it never reasons over raw signals or invents a number.
- **Every dataset carries its receipts** — source, license, citation, and checksum travel with every analysis built from it.
- **One pipeline, not two** — public data and uploaded data get identical treatment, so a user's own night sits directly against the cohort.

## Where it actually is: a working pipeline, not a slide

All 18 build phases run end-to-end locally today: load a real MIT-BIH polysomnography record, detect events, generate fingerprints, cluster phenotypes, and export a research report — then repeat on an uploaded study and compare against the public cohort.

**Stack:** React / TypeScript / Vite · FastAPI / Celery / Redis · PostgreSQL / S3 · `neuroresp` (NumPy, SciPy, MNE, NeuroKit2, scikit-learn)

> "NeuroSleep Twin is a computational neuroscience platform for investigating how respiratory disturbances during sleep interact with cortical, autonomic, oxygenation, and recovery dynamics."
> — positioning statement. **It does not diagnose.**

---

## Three doors in

### Researchers & grant reviewers
A novel phenotyping methodology built on reviewer-grade discipline: patient-level splits, dataset-level validation, and a "no invented numbers" rule baked into the UI itself.

**Ask:** research collaborators, dataset partnerships, and funding to extend validation beyond MIT-BIH PSG to additional cohorts.

### Sleep labs & clinical partners
Built to sit alongside physician judgment, not replace it — the Beyond-AHI view and Benchmark Lab exist so a clinician can check phenotypes against ground truth rather than take them on faith.

**Ask:** a pilot lab willing to run de-identified studies through the pipeline and tell us where the phenotypes do or don't match clinical judgment.

### Open-source contributors
The science lives in `neuroresp`, an API-independent Python library usable outside the app entirely, on top of a typed, modular React/FastAPI/Celery stack.

**Ask:** contributors — especially on event-detection algorithms, new public-dataset importers, and the digital-twin visualization.

---

*Research prototype — not a diagnostic device. v0 · local-first · MIT-BIH PSG*

An interactive, designed version of this pitch is available here: **https://claude.ai/code/artifact/deecf040-df1d-4572-838e-d322d1ff4781**
