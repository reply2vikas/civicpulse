# CivicPulse — BBMP Grievance Intelligence

**Track B — Accelerated Data Intelligence Tool** (Google Cloud + NVIDIA)
Gen AI Academy APAC, Cohort 2.

> CivicPulse turns six years of real Bengaluru civic-complaint data into a
> **ranked, cost-aware action roadmap** for a BBMP ward officer — and uses
> GPU acceleration so the officer can re-analyse the entire city's complaint
> history *interactively* instead of waiting on overnight batch jobs.

---

## The one-liner (for deck + demo video)

*Bengaluru citizens file 750+ civic complaints a day; CivicPulse uses
GPU-accelerated analytics and Gemini to tell a ward officer exactly which
issues to fix first — turning a backlog into a prioritized, explainable plan.*

## The user & the decision

**User:** a BBMP ward officer / engineer (AE/JE) — the person who already owns
the complaint data but has no analysis engine.
**Decision:** *given a fixed weekly crew/budget, which ward × issue-type do I
act on first this week?*

Most civic-tech builds "another citizen reporting app" that dies from low
adoption. CivicPulse instead serves the **decision-maker inside the system**.

## The 5-point story (Track B rubric)

1. **Real user & problem** — ward officer drowning in an unprioritized backlog.
2. **A data-dependent decision** — where to send limited crews this week.
3. **Pipeline** — ingest → clean → severity+priority scoring → cluster → map.
4. **Useful output** — ranked ward/issue hotspots, backlog & SLA view,
   Gemini-written intervention roadmap, exportable worklist.
5. **Acceleration proof** — re-scoring/re-clustering the full multi-year corpus
   (all 198 wards) is interactive on GPU (cuDF/cuML) but stalls on CPU. Every
   filter change (category, time window, severity) re-runs the pipeline live.

## Data (real, Public Domain)

BBMP Grievances Data, OpenCity Urban Data Portal — six yearly CSVs (2020–2025).
Row-level schema:

```
Complaint ID, Category, Sub Category, Grievance Date,
Ward Name, Grievance Status, Staff Remarks, Staff Name
```

~127k complaints in H1-2025 alone across 198 wards; combined years + in-pipeline
amplification give the volume needed for a credible GPU benchmark.

## Architecture

```
OpenCity CSVs ─► ingest.py (clean) ─► parquet / BigQuery
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                                ▼
        pipeline (pandas)                              pipeline (cuDF/cuML)   ◄─ Track B
        severity + priority + cluster                  same logic, GPU
                 │                                                │
                 └──────────────► benchmark (CPU vs GPU timing) ◄─┘
                                         │
                                         ▼
              Gemini (intervention roadmap text)  +  ward-geo join
                                         │
                                         ▼
                     Streamlit dashboard  ──►  Cloud Run (public URL)
```

- **Google Cloud:** Cloud Storage / BigQuery (data), Vertex AI or Gemini API
  (roadmap generation), Cloud Run (deploy).
- **NVIDIA:** cuDF + cuML for the accelerated pipeline; benchmark in `notebooks/`.

## Repo layout

```
src/config.py      dataset URLs, column maps, severity constants
src/ingest.py      download + clean + combine CSVs -> parquet   ✅ working
src/severity.py    severity (1-5) + priority scoring            ✅ working
src/pipeline.py    ward×category aggregation, ranking, clustering   (next)
src/benchmark.py   CPU vs GPU timing harness                        (next)
src/gemini_brief.py Gemini roadmap generator                        (next)
app/streamlit_app.py  dashboard                                     (next)
notebooks/benchmark_cpu_vs_gpu.ipynb  acceleration proof            (next)
Dockerfile, deploy/   Cloud Run                                     (next)
data/sample/       committed sample CSV for offline runs
```

## Quickstart

```bash
pip install -r requirements.txt

# offline smoke test on the committed sample:
python -m src.ingest --local data/sample --years 2025

# full build (needs open internet to data.opencity.in):
python -m src.ingest
```

## 3-day plan

- **Day 1** — ingest ✅, severity ✅, ward-geo join, aggregation/ranking, sample map.
- **Day 2** — cuDF/cuML pipeline + CPU-vs-GPU benchmark notebook; Gemini roadmap; wire Streamlit.
- **Day 3** — deploy to Cloud Run (public URL), README + GitHub, ≤3-min demo video, 5-slide deck.

## Data credit

BBMP grievance data via OpenCity (data.opencity.in), Public Domain.
