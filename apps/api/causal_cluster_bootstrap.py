import numpy as np
import pandas as pd
from typing import Callable, Any


def cluster_bootstrap_engagement_effect(
    df: pd.DataFrame,
    estimator_function: Callable[[pd.DataFrame], dict[str, Any]],
    n_bootstrap: int = 300,
    random_state: int = 42,
) -> dict[str, Any]:
    """
    Estimate uncertainty using SKU-level cluster bootstrap.

    Instead of resampling individual rows independently, this
    procedure resamples entire SKU clusters with replacement.
    This better preserves within-SKU dependence across time.

    The estimator_function should return a dictionary containing
    'estimated_engagement_effect' when estimation succeeds.
    """

    working_df = df.copy()

    # ---------------------------------------------------------
    # 1. BASIC VALIDATION
    # ---------------------------------------------------------

    if "sku_id" not in working_df.columns:
        return {
            "status": "missing_columns",
            "missing_columns": ["sku_id"],
            "method": "sku_cluster_bootstrap",
        }

    if "causal_row_valid" in working_df.columns:
        working_df = working_df[
            working_df["causal_row_valid"] == 1
        ].copy()

    if "inventory_constrained_flag" in working_df.columns:
        working_df = working_df[
            working_df["inventory_constrained_flag"] == 0
        ].copy()

    working_df = working_df.dropna(
        subset=["sku_id"]
    )

    unique_skus = (
        working_df["sku_id"]
        .astype(str)
        .unique()
    )

    n_clusters = len(unique_skus)

    if n_clusters < 2:
        return {
            "status": "insufficient_clusters",
            "clusters_available": int(n_clusters),
            "method": "sku_cluster_bootstrap",
            "message": (
                "At least two SKU clusters are required "
                "for cluster bootstrap."
            ),
        }

    # ---------------------------------------------------------
    # 2. RANDOM GENERATOR
    # ---------------------------------------------------------

    rng = np.random.default_rng(
        random_state
    )

    bootstrap_effects = []

    # ---------------------------------------------------------
    # 3. CLUSTER BOOTSTRAP
    # ---------------------------------------------------------

    for bootstrap_id in range(
        n_bootstrap
    ):
        sampled_skus = rng.choice(
            unique_skus,
            size=n_clusters,
            replace=True,
        )

        sampled_frames = []

        for draw_number, sku in enumerate(
            sampled_skus
        ):
            sku_rows = working_df[
                working_df["sku_id"].astype(str)
                == str(sku)
            ].copy()

            if sku_rows.empty:
                continue

            # Important:
            # If the same SKU is drawn multiple times,
            # give each bootstrap copy a unique cluster ID.
            #
            # Otherwise fixed effects may collapse duplicate
            # bootstrap clusters into the same SKU category.
            sku_rows["sku_id"] = (
                sku_rows["sku_id"]
                .astype(str)
                + f"__bootstrap_{bootstrap_id}_{draw_number}"
            )

            sampled_frames.append(
                sku_rows
            )

        if not sampled_frames:
            continue

        bootstrap_df = pd.concat(
            sampled_frames,
            ignore_index=True,
        )

        try:
            result = estimator_function(
                bootstrap_df
            )
        except Exception:
            continue

        if (
            result.get("status")
            != "estimated"
        ):
            continue

        effect = result.get(
            "estimated_engagement_effect"
        )

        if effect is None:
            continue

        try:
            effect = float(effect)
        except (
            TypeError,
            ValueError,
        ):
            continue

        if np.isfinite(effect):
            bootstrap_effects.append(
                effect
            )

    # ---------------------------------------------------------
    # 4. CHECK SUCCESS RATE
    # ---------------------------------------------------------

    successful_samples = len(
        bootstrap_effects
    )

    minimum_successful = min(
        30,
        max(
            10,
            int(
                n_bootstrap * 0.20
            ),
        ),
    )

    if (
        successful_samples
        < minimum_successful
    ):
        return {
            "status": "insufficient_bootstrap_samples",
            "method": "sku_cluster_bootstrap",
            "bootstrap_requested": int(
                n_bootstrap
            ),
            "bootstrap_successful": int(
                successful_samples
            ),
            "clusters_available": int(
                n_clusters
            ),
            "message": (
                "Too few cluster-bootstrap samples produced "
                "usable effect estimates."
            ),
        }

    # ---------------------------------------------------------
    # 5. SUMMARY STATISTICS
    # ---------------------------------------------------------

    effects_array = np.array(
        bootstrap_effects,
        dtype=float,
    )

    mean_effect = float(
        np.mean(
            effects_array
        )
    )

    median_effect = float(
        np.median(
            effects_array
        )
    )

    standard_error = float(
        np.std(
            effects_array,
            ddof=1,
        )
    )

    lower = float(
        np.percentile(
            effects_array,
            2.5,
        )
    )

    upper = float(
        np.percentile(
            effects_array,
            97.5,
        )
    )

    # ---------------------------------------------------------
    # 6. FINAL RESPONSE
    # ---------------------------------------------------------

    return {
        "status": "estimated",
        "method": "sku_cluster_bootstrap",
        "cluster_variable": "sku_id",
        "clusters_available": int(
            n_clusters
        ),
        "bootstrap_requested": int(
            n_bootstrap
        ),
        "bootstrap_successful": int(
            successful_samples
        ),
        "mean_effect": round(
            mean_effect,
            6,
        ),
        "median_effect": round(
            median_effect,
            6,
        ),
        "bootstrap_standard_error": round(
            standard_error,
            6,
        ),
        "confidence_interval_95": {
            "lower": round(
                lower,
                6,
            ),
            "upper": round(
                upper,
                6,
            ),
        },
        "interpretation": (
            "This uncertainty estimate resamples entire SKU clusters "
            "rather than individual observations, which better preserves "
            "dependence among repeated observations of the same product."
        ),
        "methodology_note": (
            "SKU-level cluster bootstrap improves the treatment of "
            "within-product dependence, but it does not resolve causal "
            "identification assumptions or other forms of model misspecification."
        ),
    }