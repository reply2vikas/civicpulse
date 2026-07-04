"""Turn the top hotspots into a short, written intervention roadmap.
 
Uses Google's unified GenAI SDK (`google-genai`) with the current Gemini
flash model when GOOGLE_API_KEY / GEMINI_API_KEY is set; otherwise falls back
to a deterministic template so the app always renders.
"""
from __future__ import annotations
import os
 
import pandas as pd
 
# Models tried in order. `gemini-flash-latest` always points at the current
# GA flash model, so this survives Google's model rotations.
_MODELS = ["gemini-flash-latest", "gemini-3.5-flash",
           "gemini-2.5-flash", "gemini-3.1-flash-lite"]
 
 
def _context(hotspots: pd.DataFrame, kpi: dict, n: int = 8) -> str:
    rows = hotspots.head(n)
    lines = [
        f"{r.rank}. {r.ward} - {r.category}: {int(r.complaints)} complaints, "
        f"{r.unresolved_rate*100:.0f}% unresolved, severity {int(r.severity)}, "
        f"last seen {r.last_seen}"
        for r in rows.itertuples()
    ]
    return (
        f"City snapshot: {kpi['total_complaints']:,} complaints across "
        f"{kpi['wards']} wards, {kpi['unresolved_pct']}% unresolved, "
        f"{kpi['public_safety_pct']}% public-safety.\n\n"
        "Top priority hotspots (ward - category):\n" + "\n".join(lines)
    )
 
 
PROMPT = """You are advising a BBMP ward officer in Bengaluru who must decide \
where to send limited repair crews THIS WEEK. Using the data below, write a \
crisp intervention roadmap. Requirements:
- Start with a 1-sentence bottom line.
- Give 3-5 numbered actions, each: the ward + issue, why it's urgent (tie to \
severity/backlog/volume), and a concrete first step.
- Flag any public-health/safety items explicitly.
- Keep it under 180 words. Plain, decisive language. No preamble.
 
DATA:
{context}
"""
 
 
def _fallback(hotspots: pd.DataFrame, kpi: dict, note: str = "") -> str:
    rows = hotspots.head(4)
    out = [
        f"**Bottom line:** {kpi['unresolved_pct']}% of {kpi['total_complaints']:,} "
        f"complaints are unresolved; focus crews on the highest-severity backlog first.\n"
    ]
    for i, r in enumerate(rows.itertuples(), 1):
        flag = " (public-safety)" if r.severity >= 4 else ""
        out.append(
            f"{i}. **{r.ward} - {r.category}**{flag}: {int(r.complaints)} complaints, "
            f"{r.unresolved_rate*100:.0f}% still open (severity {int(r.severity)}). "
            f"First step: dispatch an inspection team and clear the oldest open tickets."
        )
    if note:
        out.append(f"\n_{note}_")
    return "\n".join(out)
 
 
def generate_brief(hotspots: pd.DataFrame, kpi: dict) -> str:
    if hotspots is None or len(hotspots) == 0:
        return "No complaints match the current filters."
 
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback(hotspots, kpi,
                         "Template brief - add a Gemini API key for AI-generated guidance.")
 
    try:
        from google import genai
    except Exception:
        return _fallback(hotspots, kpi,
                         "Template brief - google-genai SDK not installed.")
 
    client = genai.Client(api_key=api_key)
    prompt = PROMPT.format(context=_context(hotspots, kpi))
 
    last_err = None
    for name in _MODELS:
        try:
            resp = client.models.generate_content(model=name, contents=prompt)
            if resp and getattr(resp, "text", None):
                return resp.text.strip()
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue
 
    return _fallback(hotspots, kpi, f"AI unavailable ({last_err}); showing template.")
