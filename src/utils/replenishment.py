"""Recommendations and request creation using the team's existing CSV storage."""

from decimal import Decimal
import math
from uuid import uuid4

import pandas as pd

from utils import inventory_data, workflow_storage as storage


def load_recommendations(inventory_source=None) -> pd.DataFrame:
    """Recommend positive, finite quantities without rounding fractional units."""
    inventory = inventory_data.enrich_inventory(
        inventory_data.load_inventory(inventory_source)
    )
    candidates = inventory_data.valid_replenishment_candidates(inventory)
    finite = (
        candidates[["current_stock", "minimum_stock", "target_stock"]]
        .apply(lambda column: column.map(lambda value: math.isfinite(float(value))))
        .all(axis=1)
    )
    candidates = candidates.loc[finite].copy()
    candidates["proposed_quantity"] = [
        float(Decimal(str(target)) - Decimal(str(current)))
        for target, current in zip(
            candidates["target_stock"], candidates["current_stock"]
        )
    ]
    return candidates.loc[candidates["proposed_quantity"] > 0].copy()


def create_replenishment_requests(
    product_ids: list[str], user_role: str = "Inventory Manager", inventory_source=None
) -> int:
    """Recheck current eligibility, then persist requests and creation activities."""
    selected = list(dict.fromkeys(str(product_id) for product_id in product_ids))
    if not selected:
        raise ValueError("Select at least one product.")
    if not user_role.strip():
        raise ValueError("A user role is required.")

    # Do not trust selections from an older page run.
    existing = storage.load_requests()
    pending_ids = set(
        existing.loc[existing["status"] == "Pending", "product_id"].astype(str)
    )
    if pending_ids.intersection(selected):
        raise ValueError(
            "A selected product already has a pending request. "
            "Refresh the page before trying again."
        )
    recommendations = load_recommendations(inventory_source)
    recommendations["product_id"] = recommendations["product_id"].astype(str)
    if not set(selected).issubset(set(recommendations["product_id"])):
        raise ValueError(
            "A selected product is no longer eligible for replenishment. "
            "Refresh the page to review the latest recommendations."
        )
    if recommendations["product_id"].duplicated().any():
        raise ValueError(
            "Inventory contains duplicate product IDs; correct them first."
        )

    rows = []
    by_product = recommendations.set_index("product_id")
    for product_id in selected:
        product = by_product.loc[product_id]
        rows.append(
            {
                "request_id": "REQ-" + uuid4().hex.upper(),
                "product_id": product_id,
                "product_name": product["product_name"],
                "proposed_quantity": product["proposed_quantity"],
                "unit": product["unit"],
                "supplier": product["supplier"],
                "timestamp": storage.now_string(),
                "status": "Pending",
                "decision_role": "",
            }
        )

    storage.save_requests(pd.concat([existing, pd.DataFrame(rows)], ignore_index=True))
    for row in rows:
        storage.log_activity(
            activity="Replenishment request created",
            product_id=row["product_id"],
            request_id=row["request_id"],
            details=f"Proposed quantity: {row['proposed_quantity']:g} {row['unit']}",
            user_role=user_role.strip(),
        )
    return len(rows)
