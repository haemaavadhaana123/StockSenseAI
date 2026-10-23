"""Shared activity-logging interface for StockSense AI.

All activity records are stored through workflow_storage.py
in data/activity_log.csv.
"""

from utils.workflow_storage import log_activity


def record_activity(
    activity: str,
    product_id: str = "",
    request_id: str = "",
    details: str = "",
    user_role: str = "Inventory Manager",
) -> None:
    """Record an activity in the shared StockSense AI activity log."""
    log_activity(
        activity=activity,
        product_id=product_id,
        request_id=request_id,
        details=details,
        user_role=user_role,
    )


def log_inventory_activity(
    activity: str,
    product_id: str = "",
    details: str = "",
    user_role: str = "Inventory Manager",
) -> None:
    """Record an inventory-related activity."""
    record_activity(
        activity=activity,
        product_id=product_id,
        details=details,
        user_role=user_role,
    )
