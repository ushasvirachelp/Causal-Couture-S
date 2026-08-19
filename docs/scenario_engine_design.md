# Causal Couture — Scenario Engine Design

## Purpose

The Scenario Engine will extend the existing Causal Couture analytics layer by allowing a user to test hypothetical changes in business conditions.

The goal is to compare the current analytical baseline with a user-defined scenario.

Scenario outputs are simulations. They are not causal estimates.

## Scenario Inputs

The first version of the engine will support four adjustable inputs:

- demand_change_pct
- inventory_change_pct
- engagement_change_pct
- conversion_change_pct

Example:

- demand_change_pct = 20
- inventory_change_pct = -10
- engagement_change_pct = 15
- conversion_change_pct = 5

## Baseline Metrics

Before applying the scenario, the system will calculate the existing baseline:

- demand pressure score
- stock risk score
- engagement momentum score
- conversion strength score
- overall signal score
- recommendation

These values will come from the current unified scorecard logic.

## Scenario Adjustments

The scenario engine will apply percentage-based adjustments to the baseline business signals.

### Demand

A positive demand change increases demand pressure.

Example:

Current demand score: 50

Scenario:
demand +20%

Adjusted demand score:
60

### Inventory

A negative inventory change increases stock risk.

Example:

Current stock risk: 20

Scenario:
inventory -25%

Adjusted stock risk:
higher than baseline

### Engagement

A positive engagement change increases engagement momentum.

### Conversion

A positive conversion change increases conversion strength.

## Output Structure

The scenario response should return:

### Baseline

- demand pressure
- stock risk
- engagement momentum
- conversion strength
- overall signal
- recommendation

### Scenario

- adjusted demand pressure
- adjusted stock risk
- adjusted engagement momentum
- adjusted conversion strength
- adjusted overall signal
- updated recommendation

### Comparison

For each metric:

- baseline value
- scenario value
- absolute difference
- direction of change

Example:

Demand Pressure

Baseline: 53
Scenario: 64
Difference: +11
Direction: increase

## Recommendation Categories

The next recommendation layer will use structured categories.

### REORDER

Use when demand pressure is high and inventory risk is increasing.

### MONITOR

Use when signals are positive but inventory pressure is not yet critical.

### HOLD

Use when demand and inventory conditions are stable.

### DEPRIORITIZE

Use when demand signals are weak and inventory availability is sufficient.

## Recommendation Output

Each recommendation should include:

- action
- priority
- reason
- confidence
- recommendation text

Example:

Action:
REORDER

Priority:
HIGH

Reason:
Demand pressure increased while projected inventory availability declined.

Confidence:
MEDIUM

## Input Validation

Initial accepted percentage range:

-100% to +300%

Values outside this range should be rejected.

This is intended to prevent unrealistic scenario inputs.

## Planned API

Endpoint:

POST /phase4/scenario

Expected inputs:

- processed_filename
- demand_change_pct
- inventory_change_pct
- engagement_change_pct
- conversion_change_pct

Expected response:

- baseline
- scenario
- comparison
- recommendation
- scenario metadata

## Example Scenario

Input:

Demand: +20%
Inventory: -10%
Engagement: +15%
Conversion: +5%

Possible output:

Baseline Overall Score:
77

Scenario Overall Score:
82

Recommendation:
REORDER

Priority:
HIGH

Explanation:
Demand and engagement signals strengthen while inventory availability declines, increasing inventory pressure.

## Limitations

The Scenario Engine will not:

- predict actual future sales
- estimate causal effects
- model external shocks
- estimate uncertainty
- optimize purchase quantities

It is a structured what-if analysis layer.

## Future Extensions

Later versions may include:

- SKU-specific scenarios
- time horizon selection
- reorder quantity estimates
- uncertainty ranges
- scenario history
- comparison between multiple scenarios
- causal effect estimates