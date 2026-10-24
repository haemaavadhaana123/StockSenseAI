import pandas as pd

from utils.inventory_data import (
    enrich_inventory,
    valid_replenishment_candidates,
)


def get_inventory_summary(inventory: pd.DataFrame) -> dict:
    """
    Return a summary of inventory stock conditions.

    Invalid records are counted separately and are not
    treated as normal, low-stock, or out-of-stock products.
    """

    enriched = enrich_inventory(inventory)

    statuses = enriched["stock_status"]

    return {
        "total_products": len(enriched),
        "normal_stock": int((statuses == "Normal").sum()),
        "low_stock": int((statuses == "Low Stock").sum()),
        "out_of_stock": int((statuses == "Out of Stock").sum()),
        "invalid_records": int((statuses == "Invalid Data").sum()),
    }


def get_products_needing_attention(
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """
    Return valid products that need replenishment attention.

    Invalid inventory records are excluded.
    """

    return valid_replenishment_candidates(inventory)


def get_inventory_alerts(inventory: pd.DataFrame) -> list[dict]:
    """
    Generate readable alerts for products that need attention.

    Each alert includes the product ID, name, stock status,
    current stock, minimum stock, and a human-readable message.
    """

    enriched = enrich_inventory(inventory)

    alerts = []

    attention_statuses = {
        "Low Stock",
        "Out of Stock",
        "Invalid Data",
    }

    attention_products = enriched[enriched["stock_status"].isin(attention_statuses)]

    for _, row in attention_products.iterrows():
        status = row["stock_status"]

        if status == "Invalid Data":
            message = row["validation_message"]

        elif status == "Out of Stock":
            message = "This product is out of stock."

        else:
            message = "Current stock is below the minimum stock level."

        alerts.append(
            {
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "stock_status": status,
                "current_stock": row["current_stock"],
                "minimum_stock": row["minimum_stock"],
                "unit": row["unit"],
                "message": message,
            }
        )

    return alerts
