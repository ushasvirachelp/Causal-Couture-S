# Causal Question 1 — Social Engagement and Product Demand

## Phase

Phase 5 — Causal Intelligence Foundation

## Business Question

What is the causal effect of social engagement on subsequent product sales?

The goal is to determine whether increases in social engagement are followed by meaningful changes in product demand, while accounting for other observable factors that may influence both engagement and sales.

This analysis is intended to move Causal Couture beyond descriptive business signals and scenario simulation toward formal causal-effect estimation.

---

## Unit of Analysis

The canonical analytical grain remains:

date × SKU

Each observation represents the business state of one SKU on one date.

---

## Treatment

Primary treatment variable:

engagement_rate

The engagement rate is calculated from:

engagement / impressions

The treatment represents the level of social engagement associated with a SKU at time t.

---

## Outcome

Initial outcome variable:

units_sold at t + 1

Rather than comparing social engagement and sales on the same day, the initial causal analysis will evaluate whether engagement at time t is associated with subsequent sales.

This preserves temporal ordering:

engagement at time t
→
sales at time t + 1

Future versions may evaluate longer response windows such as cumulative sales over the following three days.

---

## Candidate Adjustment Variables

The first causal model will evaluate observable variables that may influence the relationship between social engagement and sales.

Candidate variables include:

- prior units_sold
- closing_stock
- prior engagement_rate
- product_views
- view_to_cart_rate
- SKU identity
- date / temporal effects

These variables will be reviewed before estimation to determine whether they should be treated as confounders, mediators, or supporting variables.

---

## Inventory Constraint

Observed units sold are not always equivalent to true product demand.

If inventory is very low or reaches zero, sales may be suppressed because customers cannot purchase additional units.

For example:

high demand + zero inventory
→
observed sales may appear low

Therefore, inventory availability must be considered when interpreting the outcome.

Variables currently available for this include:

- opening_stock
- closing_stock
- sell_through_rate
- low_stock_flag

Stockout-related observations may eventually require separate handling or adjustment when estimating latent demand.

---

## Existing Supporting Signals

The unified Causal Couture dataset also contains engineered variables that may support analysis and diagnostics:

### Sales

- units_sold
- rolling_units_sold_3d
- sales_spike_flag

### Inventory

- opening_stock
- closing_stock
- sell_through_rate
- low_stock_flag

### Social

- engagement
- impressions
- engagement_rate
- social_spike_flag

### Web

- product_views
- add_to_cart
- view_to_cart_rate

---

## Temporal Design

The initial causal dataset will introduce lagged and future variables.

Planned variables include:

- engagement_rate_t
- engagement_rate_lag1
- units_sold_t
- units_sold_lag1
- units_sold_next_day
- closing_stock_t
- product_views_t
- view_to_cart_rate_t

Rows will remain ordered by SKU and date so that lag and lead features are generated within each SKU rather than across products.

---

## Initial Causal Structure

The first working hypothesis is:

social engagement at time t
→
subsequent product sales

while accounting for prior demand, inventory availability, SKU-level differences, and temporal effects.

The causal graph will be defined explicitly before formal causal estimation.

---

## Important Methodological Boundary

This document defines a causal question.

It does not establish that social engagement causes product sales.

The current Causal Couture scorecard and Scenario Lab remain heuristic decision-support tools.

Phase 5 will separately introduce causal identification, estimation, diagnostics, and refutation testing.

The platform should maintain a clear distinction between:

1. Observed Signal
2. Scenario Simulation
3. Estimated Causal Effect

Only the third category should be presented as a causal estimate after the required assumptions and validation steps have been completed.

---

## Next Development Step

Build a dedicated causal-analysis dataset from the existing unified date × SKU dataset.

The new dataset will introduce temporal lag and lead variables required for the first causal analysis.