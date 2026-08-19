# Causal Couture — Analytics Limitations

## Purpose

This document records the current limitations of the Causal Couture analytics layer before scenario analysis and causal modeling are added.

## Current Scoring Approach

The existing scorecard combines four business signals:

- demand pressure
- stock risk
- engagement momentum
- conversion strength

These values are currently calculated using deterministic heuristic rules.

The scorecard is useful for organizing business signals and producing early decision-support recommendations, but it should not be interpreted as a causal model.

## Current Limitations

### 1. Heuristic scoring

The current score values are based on manually defined transformations and weights.

For example, the overall signal combines the four business dimensions using fixed weights.

These weights are not currently learned from historical business outcomes.

### 2. No causal identification

The current system does not determine whether one business variable caused another variable to change.

For example:

High social engagement occurring alongside higher sales does not prove that social engagement caused the increase in sales.

### 3. No confounder control

The current workflow does not explicitly control for variables that may influence both the suspected cause and the outcome.

Possible confounders may include:

- promotions
- seasonality
- pricing
- holidays
- product launches
- weather
- external trends
- marketing campaigns

### 4. Limited time-series reasoning

The current prototype uses simple rolling metrics but does not yet model:

- longer-term trends
- seasonality
- temporal lag effects
- structural breaks
- changing demand regimes

### 5. Stockout-suppressed demand

Observed sales may underestimate true demand when inventory is unavailable.

A product that sells zero units because it was out of stock should not automatically be interpreted as having zero demand.

Future versions should distinguish:

observed sales

from

latent demand

### 6. Limited uncertainty reporting

The current scorecard returns point estimates but does not yet provide:

- confidence intervals
- uncertainty bands
- statistical significance
- model confidence
- evidence strength

### 7. Current recommendations are rule-based

Recommendations such as prioritizing inventory are generated from score thresholds.

They are intended as early decision-support logic rather than validated optimization recommendations.

## Why Scenario Analysis Comes Next

Scenario analysis provides an intermediate step between heuristic analytics and causal inference.

It allows the user to change assumptions such as:

- demand +20%
- inventory -10%
- engagement +15%
- conversion +5%

and observe how the existing analytical system responds.

This does not estimate causality.

Instead, it provides structured what-if analysis.

## Future Causal Layer

Later phases should introduce:

- treatment variables
- outcome variables
- confounder selection
- causal DAGs
- temporal ordering
- effect estimation
- placebo and refutation tests
- stockout-adjusted demand
- uncertainty reporting

The eventual system should clearly distinguish among:

1. descriptive observations
2. heuristic analytical signals
3. scenario simulations
4. estimated causal effects