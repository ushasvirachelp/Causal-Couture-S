# Causal Couture — Current System State

## Purpose

Causal Couture is a retail analytics and decision-support prototype designed for small fashion businesses working with limited historical data.

The current prototype combines sales, inventory, social media, and web analytics data into a unified analytical workflow.

## Current Data Sources

The application currently supports four source types:

- Sales
- Inventory
- Social
- Web analytics

All source data is processed around the shared analytical identifiers:

- date
- sku_id

## Current Workflow

The working pipeline currently follows:

CSV Upload
→ Schema Validation
→ Data Cleaning
→ Feature Engineering
→ Processed Dataset
→ Unified date × SKU Dataset
→ Analytical Scorecard
→ Recommendation
→ Business Explanation

## Phase 1 — Completed Foundation

The current application includes:

- FastAPI backend
- browser-based frontend
- CSV file upload
- source-specific schema validation
- required-column validation
- date parsing checks
- SKU validation
- numeric-field validation
- raw file storage
- processed file storage

## Phase 2 — Current Analytics Pipeline

The preprocessing layer currently:

- normalizes column names
- parses dates
- standardizes SKU identifiers
- converts analytical fields to numeric values
- removes invalid date/SKU records
- produces reusable processed datasets

### Current Engineered Features

Sales:
- 3-day rolling units sold
- sales spike flag

Inventory:
- sell-through rate
- low-stock flag

Social:
- engagement rate
- social spike flag

Web:
- view-to-cart rate

## Unified Analytical Dataset

Processed source files can be merged into a unified dataset using:

date × sku_id

The unified dataset is intended to serve as the common analytical layer for later decision-support and causal modeling.

## Phase 3 — Current Starter Analytics

The current analytics layer produces four heuristic signals:

1. Demand pressure
2. Stock risk
3. Engagement momentum
4. Conversion strength

These signals are combined into an overall signal score.

The current recommendation layer classifies the overall signal into general inventory guidance.

The application also generates a plain-English explanation of the scorecard.

## Current API Capabilities

Current endpoints support:

- health checks
- CSV upload and validation
- processed-file listing
- processed-file grouping by source
- unified-file listing
- processed-data summaries
- unified dataset creation
- starter source analysis
- unified scorecard generation
- business explanation generation

## Current Limitations

The current analytical scoring system is heuristic.

It does not yet:

- estimate causal effects
- model treatment/outcome relationships
- control for confounders
- generate causal graphs
- estimate latent demand
- account fully for stockout-suppressed demand
- simulate future inventory scenarios
- calculate trend changes across comparison periods
- generate structured alert severity
- provide confidence estimates for recommendations

The existing analytics should therefore be interpreted as decision-support signals rather than causal conclusions.

## Next Development Milestone

The next milestone is Scenario Intelligence.

The scenario layer will allow the user to test changes in:

- demand
- inventory
- engagement
- conversion

and compare the simulated result against the current baseline.

This will create a bridge between the existing descriptive/heuristic analytics and the later causal inference layer.
EOF