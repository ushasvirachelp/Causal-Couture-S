# Phase 5 Methodological Refinement: SKU-Level Cluster Bootstrap

## Overview

This update strengthens the uncertainty analysis used in Causal Couture's
Phase 5 causal intelligence layer.

The existing causal validation workflow used row-level bootstrap resampling
to estimate uncertainty around the engagement effect. While useful as an
initial diagnostic, row-level resampling treats observations as independently
resampled units.

Causal Couture's analytical dataset contains repeated observations for the
same SKU across time. Observations belonging to the same product may therefore
share product-specific characteristics and temporal dependence.

To better reflect this structure, an SKU-level cluster bootstrap was added.

---

## Existing Approach

The original bootstrap procedure resamples individual valid causal-analysis
rows with replacement.

It provides:

- bootstrap mean effect
- bootstrap median effect
- bootstrap standard error
- 95% percentile interval

This remains available as the original uncertainty diagnostic.

---

## Methodological Limitation

The canonical Causal Couture dataset operates at:

**date × SKU**

Therefore, multiple observations can belong to the same SKU.

Independently resampling these observations may break the natural grouping of
repeated observations belonging to a product.

This does not necessarily invalidate the original bootstrap diagnostic, but it
means its uncertainty estimate may not adequately represent within-SKU
dependence.

---

## SKU-Level Cluster Bootstrap

The new procedure treats each SKU as a resampling cluster.

Instead of independently sampling rows, the algorithm:

1. Identifies unique SKUs in the valid causal-analysis dataset.
2. Samples SKU clusters with replacement.
3. Includes all eligible observations belonging to each sampled SKU.
4. Assigns unique bootstrap cluster identifiers when the same SKU is selected
   multiple times.
5. Re-estimates the engagement effect for each bootstrap sample.
6. Repeats the process across bootstrap iterations.
7. Constructs an empirical distribution of the estimated engagement effect.

The resulting distribution is used to calculate:

- mean estimated effect
- median estimated effect
- bootstrap standard error
- 95% percentile interval
- number of successful bootstrap samples

---

## Why Cluster Resampling Matters

Cluster resampling better preserves the dependence structure among repeated
observations belonging to the same product.

For example, observations from one SKU may share characteristics related to:

- baseline demand
- product popularity
- historical engagement
- inventory behavior
- other product-specific characteristics

Keeping observations from the same SKU together during resampling provides a
more appropriate robustness check than relying exclusively on independent
row-level resampling.

---

## Implementation

A new backend module was added:

`apps/api/causal_cluster_bootstrap.py`

The module provides:

`cluster_bootstrap_engagement_effect()`

The existing Phase 5 causal-validation endpoint was extended to expose both
uncertainty approaches.

The response now includes:

`uncertainty`

for the original row-level bootstrap, and:

`cluster_uncertainty`

for the SKU-level cluster bootstrap.

This preserves the existing Phase 5 workflow while allowing the two
uncertainty estimates to be compared.

---

## Interpretation

If the row-level and SKU-level bootstrap results are reasonably similar, this
provides additional evidence that the estimated effect is not highly sensitive
to the resampling unit.

If the cluster-bootstrap interval becomes substantially wider or the effect
distribution changes considerably, that suggests within-SKU dependence is
important and the simpler row-level bootstrap may understate uncertainty.

Neither result should be interpreted as proof of causality.

---

## Analytical Boundary

The SKU-level cluster bootstrap improves uncertainty estimation under repeated
product observations.

It does NOT:

- prove that the estimated relationship is causal
- eliminate unobserved confounding
- validate the assumed causal DAG
- correct model misspecification
- establish treatment positivity
- replace placebo or robustness diagnostics
- guarantee independence across SKU clusters

It should therefore be interpreted as an additional robustness and uncertainty
diagnostic within the broader observational causal-analysis framework.

---

## Week 7 Outcome

This refinement improves the methodological reliability of the existing
Phase 5 causal intelligence system without introducing a new causal question
or expanding the scope of the platform.

The Phase 5 validation workflow can now compare:

**Row-Level Bootstrap Uncertainty**

with

**SKU-Level Cluster Bootstrap Uncertainty**

This provides a clearer view of how the estimated engagement effect behaves
when repeated observations from the same products are treated as dependent
clusters.