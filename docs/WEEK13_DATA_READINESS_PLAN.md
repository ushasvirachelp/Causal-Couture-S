# Causal Couture — Week 13: Dataset Readiness Plan

**Reporting window:** October 19–25, 2026  
**Scope:** Short methodology/documentation update; no new model or claimed empirical result.

## Objective

Before interpreting Week 12 evidence-review outputs, verify that the unified daily-SKU input can support the temporal analysis design: social engagement on day *t* and SKU sales on the **next calendar day**, with prior sales as an adjustment variable.

## Proposed checks

- Confirm the required columns: `date`, `sku_id`, `units_sold`, and `engagement_rate`.
- Check missing/invalid values and repeated SKU/date combinations.
- Count usable SKUs, next-calendar-day SKU pairs, and candidate rows that also have prior sales.
- Check whether observed engagement varies and whether enough SKUs exist to attempt cluster-based diagnostics.
- Separate data sufficiency from causal identification: passing a preflight check does not validate a causal claim.

## Hand-off to Week 14

Implement these checks as a reusable Python module, generate structured audit outputs, and produce an offline visual report for review.

**Recordkeeping note:** This Week 13 document is being prepared retrospectively on October 31, 2026. It describes the Week 13 scope; it is **not** evidence that the document was authored, tested, or committed during October 19–25.
