import pandas as pd


def analyze_treatment_overlap(df: pd.DataFrame) -> dict:
    """
    Diagnose treatment variation and basic positivity/overlap
    for engagement_rate_t.

    This does not prove positivity, but it helps identify whether
    treatment values are concentrated into a very narrow range.
    """

    if "engagement_rate_t" not in df.columns:
        raise ValueError(
            "engagement_rate_t is required for overlap analysis."
        )

    overlap_df = df.copy()

    if "causal_row_valid" in overlap_df.columns:
        overlap_df = overlap_df[
            overlap_df["causal_row_valid"] == 1
        ].copy()

    if "inventory_constrained_flag" in overlap_df.columns:
        overlap_df = overlap_df[
            overlap_df["inventory_constrained_flag"] == 0
        ].copy()

    treatment = pd.to_numeric(
        overlap_df["engagement_rate_t"],
        errors="coerce",
    ).dropna()

    if treatment.empty:
        return {
            "status": "insufficient_data",
            "rows_used": 0,
        }

    quantiles = treatment.quantile(
        [0.05, 0.25, 0.50, 0.75, 0.95]
    )

    unique_values = int(
        treatment.nunique()
    )

    treatment_range = float(
        treatment.max() - treatment.min()
    )

    if unique_values < 3:
        overlap_status = "poor"
        message = (
            "Treatment has very little variation. "
            "Causal comparisons are not well supported."
        )

    elif treatment_range == 0:
        overlap_status = "poor"
        message = (
            "Treatment is constant across observations."
        )

    else:
        overlap_status = "review"
        message = (
            "Treatment variation exists. Distribution should still "
            "be reviewed before strong causal interpretation."
        )

    return {
        "status": "analyzed",
        "rows_used": int(len(treatment)),
        "unique_treatment_values": unique_values,
        "minimum": round(float(treatment.min()), 6),
        "maximum": round(float(treatment.max()), 6),
        "mean": round(float(treatment.mean()), 6),
        "std_dev": round(float(treatment.std()), 6),
        "quantiles": {
            "p05": round(float(quantiles.loc[0.05]), 6),
            "p25": round(float(quantiles.loc[0.25]), 6),
            "p50": round(float(quantiles.loc[0.50]), 6),
            "p75": round(float(quantiles.loc[0.75]), 6),
            "p95": round(float(quantiles.loc[0.95]), 6),
        },
        "treatment_range": round(
            treatment_range,
            6,
        ),
        "overlap_status": overlap_status,
        "interpretation": message,
        "methodology_note": (
            "This is a diagnostic of observed treatment variation, "
            "not a formal proof of the causal positivity assumption."
        ),
    }