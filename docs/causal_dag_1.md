# Causal DAG 1 — Social Engagement → Subsequent Sales

## Phase

Phase 5 — Causal Intelligence

## Causal Question

What is the causal effect of social engagement at time t on product sales at time t+1?

---

## Treatment

engagement_rate_t

---

## Outcome

units_sold_next_day

---

## Core Causal Structure

The initial causal hypothesis is:

prior demand
→ social engagement
→ future sales

prior demand
→ future sales

inventory availability
→ future sales

SKU characteristics
→ social engagement

SKU characteristics
→ future sales

time effects
→ social engagement

time effects
→ future sales

---

## Candidate Confounders

### Prior Demand

Variable:

units_sold_lag1

Products that were already popular may receive more social engagement and may also continue selling strongly.

Therefore prior demand may influence both:

- engagement_rate_t
- units_sold_next_day

It should be considered an adjustment variable.

---

## Inventory Availability

Variable:

closing_stock_t

Inventory availability directly affects whether demand can become observed sales.

Low or zero stock can suppress units_sold even when customer demand is high.

Inventory will therefore be included in the initial adjustment set and separately monitored through the inventory constraint flag.

---

## SKU-Level Characteristics

Variable:

sku_id

Different products may naturally differ in:

- popularity
- product category
- baseline demand
- social visibility
- customer preference

SKU identity therefore represents persistent product-level differences that may affect both engagement and sales.

---

## Time Effects

Variable:

date

Demand and engagement may vary because of:

- weekday patterns
- seasonality
- external events
- general changes over time

Time-based controls will be derived from the existing date variable.

---

## Prior Engagement

Variable:

engagement_rate_lag1

Previous engagement may influence current engagement and may also reflect existing product popularity.

This variable will be evaluated as an additional adjustment variable.

---

## Web Variables

Available variables include:

- product_views_t
- view_to_cart_rate_t

These variables require special treatment.

Web activity may occur after social engagement and could represent part of the pathway:

social engagement
→ product views
→ purchase

If so, controlling for web activity could block part of the causal effect we are trying to estimate.

Therefore web variables will initially be treated as potential mediators or diagnostic variables rather than automatically included as confounders.

---

## Initial Adjustment Set

The first estimation model will begin with:

- units_sold_lag1
- closing_stock_t
- engagement_rate_lag1
- SKU effects
- time effects

The adjustment set may change as the causal structure is refined.

---

## Variables Not Automatically Controlled

The following variables will not automatically enter the first adjustment set:

- product_views_t
- view_to_cart_rate_t
- sales_spike_flag
- social_spike_flag
- sell_through_rate
- low_stock_flag

Some of these variables are engineered from variables already represented in the model, while others may lie downstream of the treatment.

---

## Initial DAG

Conceptually:

SKU characteristics ─────→ Engagement_t ─────→ Sales_t+1
        │                       ↑                  ↑
        │                       │                  │
        └───────────────────────┼──────────────────┘
                                │
Prior Demand ───────────────────┤
      │                         │
      └─────────────────────────→ Sales_t+1

Prior Engagement ───────────────→ Engagement_t
        │
        └───────────────────────→ Sales_t+1

Time Effects ──────────────────→ Engagement_t
      │
      └────────────────────────→ Sales_t+1

Inventory_t ───────────────────→ Sales_t+1

Possible mediated pathway:

Engagement_t
→ Product Views
→ Add to Cart / Conversion
→ Sales_t+1

---

## Identification Goal

The goal is to estimate the effect of changing engagement_rate_t on units_sold_next_day while blocking major observable backdoor paths between treatment and outcome.

The initial model will rely on observational data.

Therefore causal interpretation depends on assumptions including:

1. Important confounders are sufficiently measured.
2. Treatment precedes the outcome.
3. Comparable observations exist across different treatment levels.
4. The treatment/outcome relationship is not entirely driven by stock constraints.
5. No major unobserved confounder invalidates the estimated effect.

---

## Methodological Boundary

The DAG represents the causal assumptions used by the model.

It does not prove that the assumed causal relationships are correct.

Causal Couture will expose these assumptions alongside future estimates and validation results.

---

## Next Step

Create the first causal estimator using the prepared causal-analysis dataset and the initial adjustment set.