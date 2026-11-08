from __future__ import annotations
from html import escape
from typing import Any


def safe(value: Any) -> str:
    return escape(str("Not available" if value is None else value), quote=True)


def render_quality_html(profile: dict[str, Any], comparison: dict[str, Any] | None,
                        review: dict[str, Any] | None, source_name: str, source_sha: str) -> str:
    def metric(name: str, value: Any) -> str:
        return f'<div class="metric"><span>{safe(name)}</span><strong>{safe(value)}</strong></div>'

    metrics = [
        ("Quality gate", profile["quality_gate"]),
        ("Input rows", profile["total_rows"]),
        ("Usable SKUs", profile["unique_skus"]),
        ("Next-day pairs", profile["next_day_pairs"]),
        ("Phase 5-like candidates", profile["phase5_like_candidate_rows"]),
        ("Strict 3-day windows", profile["strict_three_day_windows"]),
        ("Multi-day gaps", profile["multi_day_gaps"]),
        ("Duplicate-key rows", profile["duplicate_key_rows"]),
    ]
    metrics_html = "".join(metric(a, b) for a, b in metrics)
    stages = profile.get("attrition", [])
    maximum = max((x["rows"] for x in stages), default=0) or 1
    bars = "".join(
        f'<div class="barrow"><div class="barlabel">{safe(x["stage"])} <b>{safe(x["rows"])}</b></div>'
        f'<div class="track"><div class="fill" style="width:{max(0, min(100, x["rows"] / maximum * 100)):.1f}%"></div></div></div>'
        for x in stages
    ) or '<p>Not available: required fields are missing or input is empty.</p>'
    issues = "".join(f'<li><span class="tag">{safe(i["severity"])}</span> <b>{safe(i["code"])}</b> — {safe(i["detail"])}<div class="muted">Action: {safe(i["analyst_action"])}</div></li>' for i in profile["issues"]) or "<li>No predefined issue detected; this is not proof of analytical validity.</li>"
    sku_rows = "".join(
        "<tr>" + "".join(f"<td>{safe(row.get(field))}</td>" for field in ("sku_id", "usable_rows", "next_day_pairs", "phase5_like_candidates", "strict_three_day_windows", "multi_day_gaps", "engagement_distinct")) + "</tr>"
        for row in sorted(profile["per_sku"], key=lambda r: (-r["usable_rows"], r["sku_id"]))[:30]
    ) or '<tr><td colspan="7">No usable SKU observations</td></tr>'
    comparison_html = '<p>No baseline supplied. Use --baseline-csv for descriptive comparison.</p>'
    if comparison:
        changes = "".join(f'<tr><td>{safe(x["metric"])}</td><td>{safe(x["baseline"])}</td><td>{safe(x["current"])}</td><td>{safe(x["absolute_change"])}</td></tr>' for x in comparison["metric_changes"])
        comparison_html = (f'<p>Shared SKUs: <b>{safe(comparison["sku_overlap_count"])}</b>; baseline-only: {safe(comparison["sku_only_baseline_count"])}; current-only: {safe(comparison["sku_only_current_count"])}.</p>'
                           '<div class="tablewrap"><table><thead><tr><th>Metric</th><th>Baseline</th><th>Current</th><th>Difference</th></tr></thead><tbody>' + changes + '</tbody></table></div>'
                           f'<p class="muted">{safe(comparison["interpretation_boundary"])}</p>')
    evidence_html = '<p>No Phase 5 JSON supplied. This quality report does not estimate a causal effect.</p>'
    if review:
        flags = "".join(f'<li>{safe(x["code"])} — {safe(x["finding"])}</li>' for x in review["caution_flags"]) or '<li>No predefined caution flag; not causal proof.</li>'
        diags = "".join(f'<tr><td>{safe(x["diagnostic"])}</td><td>{safe(x["status"])}</td><td>{safe(x["evidence_signal"])}</td></tr>' for x in review["diagnostics"])
        evidence_html = (f'<p>Evidence review: <b>{safe(review["decision_readiness"])}</b>. Observational estimate: {safe(review["primary_observational_effect"])}.</p>'
                         f'<ul>{flags}</ul><div class="tablewrap"><table><thead><tr><th>Diagnostic</th><th>Status</th><th>Interpretation</th></tr></thead><tbody>{diags}</tbody></table></div>')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Causal Couture · Week 15 Quality Intelligence</title><style>
:root{{--bg:#f7f5f8;--ink:#241d30;--muted:#6d6475;--plum:#4c2768;--lemon:#f5e873;--line:#e7e1eb}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,sans-serif}}
main{{max-width:1150px;margin:auto;padding:32px 24px 70px}}header{{padding:36px;background:linear-gradient(120deg,#25182e,#6c3980);color:white;border-radius:18px}}
.eyebrow{{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--lemon)}}h1{{font-size:clamp(26px,4vw,42px);line-height:1.12;margin:12px 0}}
header p{{color:#e7ddeb;max-width:780px}}.metrics{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0}}
.metric,section{{background:white;border:1px solid var(--line);border-radius:13px;padding:20px}}.metric span{{display:block;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}}
.metric strong{{display:block;font-size:21px;margin-top:8px;overflow-wrap:anywhere}}section{{margin-top:16px}}h2{{margin:0 0 14px;font-size:21px}}
.barlabel{{display:flex;justify-content:space-between;gap:12px;margin:9px 0 4px}}.track{{height:11px;border-radius:10px;background:#ece5f0;overflow:hidden}}
.fill{{height:100%;background:linear-gradient(90deg,#754191,#c1a2d1)}}.barrow{{margin-bottom:13px}}ul{{padding-left:20px}}li{{margin:9px 0}}.muted{{color:var(--muted);font-size:13px}}
.tag{{background:#f2eaf7;padding:2px 7px;border-radius:6px;font-size:12px;text-transform:uppercase}}.tablewrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid var(--line)}}th{{color:var(--muted)}}
.note{{background:#f6f1dc;border-left:4px solid #b4a330;padding:14px 18px;border-radius:6px}}footer{{color:var(--muted);font-size:12px;margin-top:24px;overflow-wrap:anywhere}}
@media(max-width:850px){{.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:520px){{.metrics{{grid-template-columns:1fr}}main{{padding:14px}}header{{padding:24px}}}}
</style></head><body><main><header><div class="eyebrow">Humanitarians.ai · Causal Couture · Phase 5</div><h1>Quality Intelligence &amp; Analytical Governance</h1>
<p>Week 15 · Reproducible dataset integrity, temporal coverage, evidence review, and baseline comparison. No model is fitted.</p></header>
<div class="metrics">{metrics_html}</div><section><h2>Data attrition</h2>{bars}</section>
<section><h2>Quality findings &amp; analyst actions</h2><ul>{issues}</ul></section>
<section><h2>SKU-level temporal coverage</h2><p class="muted">Showing up to 30 SKUs. The complete breakdown is in the accompanying CSV.</p>
<div class="tablewrap"><table><thead><tr><th>SKU</th><th>Usable rows</th><th>Next-day pairs</th><th>Phase 5-like</th><th>Strict 3-day</th><th>Gaps</th><th>Engagement values</th></tr></thead><tbody>{sku_rows}</tbody></table></div></section>
<section><h2>Baseline comparison</h2>{comparison_html}</section><section><h2>Optional Phase 5 evidence</h2>{evidence_html}</section>
<section><h2>Interpretation boundary</h2><div class="note">{safe(profile["interpretation_boundary"])}</div></section>
<footer>Source: {safe(source_name)} · SHA-256: {safe(source_sha)} · Generated locally · No external network assets · Raw source records are not embedded in this report.</footer>
</main></body></html>'''
