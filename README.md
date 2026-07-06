CivicPulse — GPU-Accelerated Civic Grievance Intelligence

Track B — Accelerated Data Intelligence Tool · Gen AI Academy APAC (Cohort 2)
Google Cloud (Gemini) + NVIDIA (RAPIDS / cuDF)


CivicPulse turns real Bengaluru civic-complaint data into a ranked, explainable
"act-first" plan for a BBMP ward officer — and uses GPU acceleration to re-rank the
entire city's multi-year complaint history in milliseconds, so the analysis stays
interactive instead of running as an overnight batch job.



Live app: https://civicpulse-cxjn4zazkvykvfxywz2vza.streamlit.app/
Demo video: (add link)


The user & the decision

User: a BBMP ward officer / engineer. Decision: given a fixed weekly crew, which
ward × issue-type do I fix first? Most civic-tech serves citizens filing complaints;
CivicPulse serves the decision-maker who already owns the data but has no prioritisation engine.

What it does


Ingests real BBMP grievance data (126,974 complaints, H1 2025, 198 wards).
Scores every ward × issue by a transparent priority = f(severity, volume, unresolved
backlog, recency).
Ranks hotspots, shows a ward-priority chart and complaint mix, and exports a crew worklist.
Gemini writes a plain-English intervention roadmap for the officer's current filters.
cuDF (NVIDIA RAPIDS) re-runs the whole aggregation on GPU on every filter change.


Acceleration result (measured, NVIDIA T4)

Rows re-rankedCPU (pandas)GPU (cuDF)Speedup3,000,000607 ms22 ms27×6,000,0001,768 ms29 ms62×

Doubling the data ~tripled CPU time but barely moved GPU time — GPU keeps the tool
interactive at city scale. Reproduce it in notebooks/benchmark_cpu_vs_gpu.ipynb
(Colab → GPU runtime → Run all).

Architecture

OpenCity BBMP CSVs ─► src/ingest.py (clean) ─► parquet
                                                 │
                 ┌───────────────────────────────┴──────────────┐
                 ▼                                               ▼
        pandas pipeline (CPU)                          cuDF pipeline (GPU)  ◄─ Track B
        severity + priority + rank                     same logic, RAPIDS
                 │                                               │
                 └──────────► benchmark_cpu_vs_gpu.ipynb ◄───────┘
                                         │
                     Gemini roadmap  ◄───┴──►  Streamlit dashboard ─► public URL


Google Cloud: Gemini (gemini-flash-latest) generates the intervention roadmap.
NVIDIA: cuDF / RAPIDS accelerates the ward × category re-aggregation.


Repo layout

src/config.py        dataset URLs, column maps, severity constants
src/ingest.py        download + clean + combine CSVs -> parquet
src/severity.py      severity (1-5) + priority scoring
src/pipeline.py      load / amplify / aggregate / rank hotspots
src/gemini_brief.py  Gemini roadmap (template fallback if no key)
app/streamlit_app.py dashboard (deployed)
notebooks/benchmark_cpu_vs_gpu.ipynb   CPU vs GPU proof
data/sample/         committed sample for offline runs

Run locally

bashpip install -r requirements.txt
streamlit run app/streamlit_app.py           # dashboard
python -m src.ingest                          # download + build real dataset (open internet)

For live AI briefs, set an environment variable GOOGLE_API_KEY (get a free key at
aistudio.google.com/app/apikey). On Streamlit Cloud, add it under Settings → Secrets.

Data credit

BBMP grievance data via OpenCity (data.opencity.in), Public Domain.
