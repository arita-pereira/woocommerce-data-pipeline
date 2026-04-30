# GOLD layer — builds the fact_order_items table by joining Silver datasets.

import numpy as np
from utils.io import write_parquet
from config.paths import PATHS


def create_fact_order_items(order_items_silver, order_itemmeta_silver):
    """
    Build the fact_order_items table by joining order_items_silver with
    order_itemmeta_silver on order_item_id.

    Beyond the join, this function computes two derived metrics:
    - unit_price: line_total divided by quantity (safely handles zeros and nulls)
    - total_with_tax: line_total + line_tax, or just line_total if tax isn't
      broken out separately (WooCommerce sometimes bundles tax into the line total)
    """

    # Left join so we keep all order items even if their metadata is missing
    fact = order_items_silver.merge(
        order_itemmeta_silver,
        on="order_item_id",
        how="left",
    )

    # Compute unit price safely — returns NaN for any row where quantity is
    # zero, null, or the line total is missing, rather than raising an error
    def safe_unit_price(row):
        lt = row.get("line_total")
        q  = row.get("quantity")
        if q is None or q == 0 or q is np.nan:
            return np.nan
        if lt is None or lt is np.nan:
            return np.nan
        try:
            return lt / q
        except Exception:
            return np.nan

    fact["unit_price"] = fact.apply(safe_unit_price, axis=1)

    # Add up line total and tax if tax is available as a separate column.
    # If not, we assume WooCommerce already included tax in line_total.
    if "line_tax" in fact.columns:
        fact["total_with_tax"] = fact[["line_total", "line_tax"]].sum(axis=1, min_count=1)
    else:
        fact["total_with_tax"] = fact["line_total"].astype(float)

    # Cast all ID and quantity fields to nullable integers
    for c in ["order_item_id", "order_id", "product_id", "variation_id", "quantity"]:
        if c in fact.columns:
            fact[c] = fact[c].astype("Int64")

    # Put the most useful columns up front for BI tools, skipping any that
    # didn't make it through the join
    cols_first = [
        "order_item_id", "order_id", "product_id", "variation_id",
        "order_item_name", "order_item_color", "order_item_size",
        "quantity", "line_total", "line_tax", "line_subtotal",
        "line_subtotal_tax", "unit_price", "total_with_tax",
    ]
    cols_first  = [c for c in cols_first if c in fact.columns]
    other_cols  = [c for c in fact.columns if c not in cols_first]
    fact = fact[cols_first + other_cols]

    write_parquet(fact, f"{PATHS['gold']}/fact_order_items.parquet")
    return fact
