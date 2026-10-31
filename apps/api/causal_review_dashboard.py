from __future__ import annotations
from html import escape
from typing import Any


def _safe(value: Any) -> str:
    return escape(str(value if value is not None else "Not available"), quote=True)


def render_validation_html(profile: dict[str, Any] | None, review: dict[str, Any] | None, source: str) -> str:
    """Return an offline HTML report; all source-derived text is escaped."""
    status = (profile or {}).get("model_run_guidance", "not_profiled")
    readiness = (review or {}).get("decision_readiness", "not_run")
    cards = [
        ("Source", source),
        ("Data preflight", status),
        ("Candidate causal rows", (profile or {}).get("candidate_causal_rows")),
        ("Usable SKUs", (profile or {}).get("unique_skus")),
        ("Evidence review", readiness),
        ("Observed effect", (review or {}).get("primary_observational_effect")),
    ]
    card_html = "".join(f'<div class="metric"><div class="label">{_safe(k)}</div><div class="value">{_safe(v)}</div></div>' for k, v in cards)
    issues = (profile or {}).get("issues", [])
    flags = (review or {}).get("caution_flags", [])
    diagnostics = (review or {}).get("diagnostics", [])
    issue_html = "".join(f'<li><b>{_safe(x.get("code"))}</b> — {_safe(x.get("detail"))}</li>' for x in issues) or "<li>No predefined data issue flagged. This does not certify data quality.</li>"
    flag_html = "".join(f'<li><b>{_safe(x.get("code"))}</b> — {_safe(x.get("finding"))}</li>' for x in flags) or "<li>No predefined evidence warning reported, or no review was run.</li>"
    diag_html = "".join(f'<tr><td>{_safe(x.get("diagnostic"))}</td><td>{_safe(x.get("status"))}</td><td>{_safe(x.get("evidence_signal"))}</td></tr>' for x in diagnostics)
    if not diag_html:
        diag_html = '<tr><td colspan="3">No evidence review run. Use --input-json or --run-phase5 to generate one.</td></tr>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Causal Couture | Week 14 Validation</title>
<style>
:root{{--bg:#f6f4f8;--ink:#251c35;--muted:#706779;--accent:#6040a5;--border:#e3dfe9}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,sans-serif}}
main{{max-width:1120px;margin:0 auto;padding:44px 24px 90px}}header{{background:linear-gradient(115deg,#251c35,#65449e);color:white;padding:38px;border-radius:18px}}
.eyebrow{{text-transform:uppercase;letter-spacing:.15em;font-size:12px;opacity:.8}}h1{{font-size:36px;margin:10px 0 5px}}header p{{margin:0;color:#e3d9f7}}
.metrics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:24px 0}}
.metric,section{{background:white;border:1px solid var(--border);border-radius:14px;padding:20px;box-shadow:0 2px 12px #221b2b08}}
.label{{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}}.value{{font-size:19px;font-weight:700;overflow-wrap:anywhere;margin-top:8px}}
section{{margin-top:18px}}h2{{font-size:20px;margin:0 0 12px}}li{{margin:8px 0}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;border-bottom:1px solid var(--border);padding:10px}}th{{color:var(--muted)}}
.note{{padding:14px 18px;border-left:4px solid var(--accent);background:#f1edf8;border-radius:4px}}footer{{margin-top:24px;color:var(--muted);font-size:13px}}
@media(max-width:700px){{.metrics{{grid-template-columns:1fr}}h1{{font-size:27px}}main{{padding:20px 12px}}header{{padding:25px}}}}
</style></head><body><main><header><div class="eyebrow">Humanitarians.ai · Causal Couture · Phase 5</div>
<h1>Evidence &amp; Data Readiness</h1><p>Week 14 · Offline analytical validation report</p></header>
<div class="metrics">{card_html}</div>
<section><h2>Data-quality findings</h2><ul>{issue_html}</ul></section>
<section><h2>Evidence cautions</h2><ul>{flag_html}</ul></section>
<section><h2>Diagnostic inventory</h2><table><thead><tr><th>Diagnostic</th><th>Execution status</th><th>Evidence signal</th></tr></thead><tbody>{diag_html}</tbody></table></section>
<section><h2>Interpretation boundary</h2><div class="note">This report is an exploratory audit, not a validation certificate or causal proof. Data preflight is not a model-quality assessment. Missing diagnostics and warnings require analyst review; no automatic retail action is authorized.</div></section>
<footer>Generated locally from supplied project inputs. No network connection required. Results should be interpreted with the underlying source and methodology.</footer>
</main></body></html>'''