"""Shared CSV-backed storage for simulated replenishment requests and activity."""

from __future__ import annotations

import math
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# FILE PATHS AND SCHEMAS
# --------------------------------------------------

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

INVENTORY_FILE = DATA_DIR / "sample_inventory.csv"
REQUESTS_FILE = DATA_DIR / "replenishment_request.csv"
ACTIVITY_FILE = DATA_DIR / "activity_log.csv"

# =========================================================

# ACTIVE WORKFLOW STORAGE CONTEXT

# =========================================================

_DEFAULT_DATA_DIR = DATA_DIR

_DEFAULT_INVENTORY_FILE = INVENTORY_FILE

_DEFAULT_REQUESTS_FILE = REQUESTS_FILE

_DEFAULT_ACTIVITY_FILE = ACTIVITY_FILE


def set_storage_context(inventory_path=None, workflow_dir=None):
    """Configure inventory and workflow storage paths."""
    global DATA_DIR, INVENTORY_FILE, REQUESTS_FILE, ACTIVITY_FILE

    if inventory_path is None or workflow_dir is None:
        DATA_DIR = Path(__file__).resolve().parents[1] / "data"
        INVENTORY_FILE = DATA_DIR / "sample_inventory.csv"
        REQUESTS_FILE = DATA_DIR / "replenishment_request.csv"
        ACTIVITY_FILE = DATA_DIR / "activity_log.csv"
        return

    inventory_path = Path(inventory_path)
    workflow_dir = Path(workflow_dir)
    workflow_dir.mkdir(parents=True, exist_ok=True)

    DATA_DIR = workflow_dir
    INVENTORY_FILE = inventory_path
    REQUESTS_FILE = workflow_dir / "replenishment_request.csv"
    ACTIVITY_FILE = workflow_dir / "activity_log.csv"


REQUEST_COLUMNS = [
    "request_id",
    "product_id",
    "product_name",
    "proposed_quantity",
    "unit",
    "supplier",
    "timestamp",
    "status",
    "decision_role",
]

ACTIVITY_COLUMNS = [
    "timestamp",
    "activity",
    "product_id",
    "request_id",
    "details",
    "user_role",
]

ALLOWED_REQUEST_STATUSES = (
    "Pending",
    "Approved",
    "Rejected",
    "Submitted to Simulated Procurement",
)


# --------------------------------------------------
# GENERAL HELPERS
# --------------------------------------------------


def now_string() -> str:
    """Return the current local time with timezone information."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _require_text(value: object, field_name: str) -> str:
    """Validate a required text field."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required.")

    return value.strip()


def _atomic_write_csv(
    frame: pd.DataFrame,
    path: Path,
    columns: list[str],
) -> None:
    """Write a CSV through a temporary file before replacing the original."""
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            suffix=".tmp",
            prefix=f".{path.name}.",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            frame.reindex(columns=columns).to_csv(handle, index=False)

        os.replace(temporary_path, path)

    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


# --------------------------------------------------
# INVENTORY AND CSV INITIALISATION
# --------------------------------------------------


def _read_inventory_details() -> pd.DataFrame:
    """Read inventory fields needed to complete replenishment requests."""
    if not INVENTORY_FILE.exists():
        raise FileNotFoundError(f"Inventory file not found: {INVENTORY_FILE}")

    inventory = pd.read_csv(
        INVENTORY_FILE,
        dtype={"product_id": "string"},
        keep_default_na=False,
    )

    required = {"product_id", "unit", "supplier"}
    missing = sorted(required.difference(inventory.columns))

    if missing:
        raise ValueError(
            "Missing inventory columns needed by replenishment requests: "
            + ", ".join(missing)
        )

    details = inventory[["product_id", "unit", "supplier"]].copy()

    details["product_id"] = details["product_id"].astype(str).str.strip()

    details = details[details["product_id"] != ""]

    return details.drop_duplicates("product_id", keep="first")


def _complete_request_fields(frame: pd.DataFrame) -> pd.DataFrame:
    """Ensure requests contain all required columns and preserve valid values."""
    requests = frame.copy()

    for column in REQUEST_COLUMNS:
        if column not in requests.columns:
            requests[column] = ""

    requests["product_id"] = requests["product_id"].fillna("").astype(str).str.strip()

    requests["status"] = requests["status"].fillna("").astype(str).str.strip()

    requests.loc[requests["status"] == "", "status"] = "Pending"

    inventory_details = _read_inventory_details().set_index("product_id")

    for column in ("unit", "supplier"):
        existing = requests[column].fillna("").astype(str)
        inventory_value = requests["product_id"].map(inventory_details[column])

        has_inventory_value = inventory_value.notna() & inventory_value.astype(
            str
        ).str.strip().ne("")

        requests[column] = inventory_value.where(
            has_inventory_value,
            existing,
        )

        requests[column] = requests[column].fillna("").astype(str)

    return requests[REQUEST_COLUMNS]


def _read_requests_unchecked() -> pd.DataFrame:
    """Read requests without performing status validation."""
    if not REQUESTS_FILE.exists():
        return pd.DataFrame(columns=REQUEST_COLUMNS)

    return pd.read_csv(
        REQUESTS_FILE,
        dtype={"request_id": "string", "product_id": "string"},
        keep_default_na=False,
    )


def _read_activity_unchecked() -> pd.DataFrame:
    """Read activity records and ensure the expected columns exist."""
    if not ACTIVITY_FILE.exists():
        return pd.DataFrame(columns=ACTIVITY_COLUMNS)

    activity = pd.read_csv(
        ACTIVITY_FILE,
        keep_default_na=False,
    )

    for column in ACTIVITY_COLUMNS:
        if column not in activity.columns:
            activity[column] = ""

    return activity[ACTIVITY_COLUMNS]


def ensure_workflow_files() -> None:
    """Create or migrate the request and activity CSV files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not INVENTORY_FILE.exists():
        raise FileNotFoundError(f"Inventory file not found: {INVENTORY_FILE}")

    raw_requests = _read_requests_unchecked()
    requests = _complete_request_fields(raw_requests)

    if not REQUESTS_FILE.exists() or list(raw_requests.columns) != REQUEST_COLUMNS:
        _atomic_write_csv(
            requests,
            REQUESTS_FILE,
            REQUEST_COLUMNS,
        )

    if not ACTIVITY_FILE.exists():
        _atomic_write_csv(
            pd.DataFrame(columns=ACTIVITY_COLUMNS),
            ACTIVITY_FILE,
            ACTIVITY_COLUMNS,
        )
    else:
        activity = _read_activity_unchecked()
        actual_columns = list(
            pd.read_csv(
                ACTIVITY_FILE,
                nrows=0,
                keep_default_na=False,
            ).columns
        )

        if actual_columns != ACTIVITY_COLUMNS:
            _atomic_write_csv(
                activity,
                ACTIVITY_FILE,
                ACTIVITY_COLUMNS,
            )


# --------------------------------------------------
# PUBLIC LOAD AND SAVE FUNCTIONS
# --------------------------------------------------


def load_requests() -> pd.DataFrame:
    """Load and validate replenishment requests."""
    ensure_workflow_files()

    requests = _complete_request_fields(_read_requests_unchecked())

    invalid_statuses = sorted(
        set(requests["status"].astype(str)) - set(ALLOWED_REQUEST_STATUSES)
    )

    if invalid_statuses:
        raise ValueError("Unsupported request status: " + ", ".join(invalid_statuses))

    request_ids = requests["request_id"].fillna("").astype(str).str.strip()

    duplicate_ids = request_ids[
        (request_ids != "") & request_ids.duplicated(keep=False)
    ]

    if not duplicate_ids.empty:
        raise ValueError(
            "Duplicate request IDs detected. Please correct "
            "replenishment_request.csv before continuing."
        )

    return requests


def load_activity() -> pd.DataFrame:
    """Load the activity log."""
    ensure_workflow_files()
    return _read_activity_unchecked()


def save_requests(frame: pd.DataFrame) -> None:
    """Validate and save replenishment requests."""
    ensure_workflow_files()

    if not isinstance(frame, pd.DataFrame):
        raise ValueError("Requests must be provided as a DataFrame.")

    requests = _complete_request_fields(frame)

    invalid_statuses = sorted(
        set(requests["status"].astype(str)) - set(ALLOWED_REQUEST_STATUSES)
    )

    if invalid_statuses:
        raise ValueError("Unsupported request status: " + ", ".join(invalid_statuses))

    request_ids = requests["request_id"].fillna("").astype(str).str.strip()

    if (request_ids == "").any():
        raise ValueError("Every request must have a request ID.")

    if request_ids.duplicated().any():
        raise ValueError("Request IDs must be unique.")

    _atomic_write_csv(
        requests,
        REQUESTS_FILE,
        REQUEST_COLUMNS,
    )


def log_activity(
    activity: str,
    product_id: str = "",
    request_id: str = "",
    details: str = "",
    user_role: str = "Inventory Manager",
) -> None:
    """Append a validated entry to the activity log."""
    ensure_workflow_files()

    activity_name = _require_text(activity, "Activity")
    role = _require_text(user_role, "User role")

    if not isinstance(product_id, str):
        raise ValueError("Product ID must be text.")

    if not isinstance(request_id, str):
        raise ValueError("Request ID must be text.")

    if not isinstance(details, str):
        raise ValueError("Activity details must be text.")

    records = load_activity()

    record = {
        "timestamp": now_string(),
        "activity": activity_name,
        "product_id": product_id.strip(),
        "request_id": request_id.strip(),
        "details": details.strip(),
        "user_role": role,
    }

    records = pd.concat(
        [records, pd.DataFrame([record])],
        ignore_index=True,
    )

    _atomic_write_csv(
        records,
        ACTIVITY_FILE,
        ACTIVITY_COLUMNS,
    )


# --------------------------------------------------
# VALIDATION HELPERS
# --------------------------------------------------


def _validated_quantity(value: object) -> int | float:
    """Return a positive finite quantity or raise a validation error."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("Quantity must be a number greater than zero.")

    try:
        quantity = float(value.strip() if isinstance(value, str) else value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Quantity must be a number greater than zero.") from exc

    if not math.isfinite(quantity) or quantity <= 0:
        raise ValueError("Quantity must be a finite number greater than zero.")

    return int(quantity) if quantity.is_integer() else quantity


def _request_index(
    requests: pd.DataFrame,
    request_id: str,
) -> int:
    """Find exactly one request by ID."""
    request_id = _require_text(request_id, "Request ID")

    ids = requests["request_id"].fillna("").astype(str).str.strip()
    matches = requests.index[ids == request_id]

    if len(matches) == 0:
        raise ValueError("Request not found.")

    if len(matches) > 1:
        raise ValueError(
            "Request ID is duplicated; refusing to update multiple requests."
        )

    return int(matches[0])


def _append_record(
    activity: pd.DataFrame,
    *,
    activity_name: str,
    product_id: str,
    request_id: str,
    details: str,
    user_role: str,
) -> pd.DataFrame:
    """Return an activity DataFrame with one additional record."""
    record = {
        "timestamp": now_string(),
        "activity": activity_name,
        "product_id": product_id,
        "request_id": request_id,
        "details": details,
        "user_role": user_role,
    }

    return pd.concat(
        [activity, pd.DataFrame([record])],
        ignore_index=True,
    )


def _persist_decision_state(
    requests: pd.DataFrame,
    activity: pd.DataFrame,
) -> None:
    """
    Persist both CSV files using atomic replacement for each file.

    Note: the two files are not a single database transaction. A process
    failure between replacements could leave the files out of sync.
    """
    _atomic_write_csv(
        requests,
        REQUESTS_FILE,
        REQUEST_COLUMNS,
    )

    _atomic_write_csv(
        activity,
        ACTIVITY_FILE,
        ACTIVITY_COLUMNS,
    )


# --------------------------------------------------
# QUANTITY ADJUSTMENT
# --------------------------------------------------


def adjust_request_quantity(
    request_id: str,
    quantity: object,
    user_role: str = "Inventory Manager",
    adjustment_reason: str = "",
) -> bool:
    """Adjust a pending request and record the reason."""
    role = _require_text(user_role, "User role")
    reason = _require_text(
        adjustment_reason,
        "Quantity adjustment reason",
    )

    adjusted_quantity = _validated_quantity(quantity)

    requests = load_requests()
    index = _request_index(requests, request_id)

    status = str(requests.at[index, "status"]).strip()

    if status != "Pending":
        raise ValueError("Only pending requests can be adjusted.")

    old_value = pd.to_numeric(
        pd.Series([requests.at[index, "proposed_quantity"]]),
        errors="coerce",
    ).iloc[0]

    if pd.notna(old_value) and float(old_value) == float(adjusted_quantity):
        return False

    old_text = str(requests.at[index, "proposed_quantity"])

    requests["proposed_quantity"] = pd.to_numeric(
        requests["proposed_quantity"],
        errors="coerce",
    )

    requests.at[index, "proposed_quantity"] = adjusted_quantity
    requests.at[index, "timestamp"] = now_string()

    unit = str(requests.at[index, "unit"]).strip()
    unit_suffix = f" {unit}" if unit else ""

    details = (
        f"Previous quantity: {old_text}{unit_suffix}; "
        f"new quantity: {adjusted_quantity}{unit_suffix}; "
        f"reason: {reason}"
    )

    activity = load_activity()

    activity = _append_record(
        activity,
        activity_name="Replenishment quantity adjusted",
        product_id=str(requests.at[index, "product_id"]),
        request_id=str(request_id),
        details=details,
        user_role=role,
    )

    _persist_decision_state(requests, activity)

    return True


# --------------------------------------------------
# APPROVAL AND REJECTION
# --------------------------------------------------


def decide_request(
    request_id: str,
    decision: str,
    user_role: str = "Inventory Manager",
    rejection_reason: str = "",
    decision_reason: str = "",
) -> str:
    """Approve or reject a pending replenishment request."""
    if not isinstance(decision, str):
        raise ValueError("Decision must be Approved or Rejected.")

    decision = decision.strip().title()

    if decision not in ("Approved", "Rejected"):
        raise ValueError("Decision must be Approved or Rejected.")

    role = _require_text(user_role, "Decision role")

    if not isinstance(rejection_reason, str):
        raise ValueError("Rejection reason must be text.")

    if not isinstance(decision_reason, str):
        raise ValueError("Decision notes must be text.")

    rejection_reason = rejection_reason.strip()
    decision_reason = decision_reason.strip()

    if decision == "Rejected" and not rejection_reason:
        raise ValueError("Please provide a reason for rejecting the request.")

    requests = load_requests()
    index = _request_index(requests, request_id)

    status = str(requests.at[index, "status"]).strip()

    if status != "Pending":
        raise ValueError("This request has already been processed.")

    quantity = _validated_quantity(requests.at[index, "proposed_quantity"])

    product_id = str(requests.at[index, "product_id"])
    unit = str(requests.at[index, "unit"]).strip()
    unit_suffix = f" {unit}" if unit else ""

    requests.at[index, "proposed_quantity"] = quantity
    requests.at[index, "status"] = decision
    requests.at[index, "decision_role"] = role
    requests.at[index, "timestamp"] = now_string()

    activity = load_activity()

    if decision == "Approved":
        activity_name = "Replenishment request approved"
        details = f"Approved quantity: {quantity}{unit_suffix}"

        if decision_reason:
            details += f"; Notes: {decision_reason}"

    else:
        activity_name = "Replenishment request rejected"
        details = f"Reason: {rejection_reason}"

    activity = _append_record(
        activity,
        activity_name=activity_name,
        product_id=product_id,
        request_id=str(request_id),
        details=details,
        user_role=role,
    )

    _persist_decision_state(requests, activity)

    return decision


# --------------------------------------------------
# SIMULATED PROCUREMENT
# --------------------------------------------------


def submit_to_simulated_procurement(
    request_id: str,
    user_role: str = "Inventory Manager",
) -> None:
    """
    Mark an approved request as submitted to simulated procurement.

    This function does not place a real order or contact a supplier.
    """
    role = _require_text(user_role, "Decision role")

    allowed_roles = {
        "Inventory Manager",
        "Business Owner",
        "Procurement Manager",
    }

    if role not in allowed_roles:
        raise ValueError(
            "You are not authorised to approve or reject replenishment requests."
        )
    requests = load_requests()
    index = _request_index(requests, request_id)

    status = str(requests.at[index, "status"]).strip()

    if status != "Approved":
        raise ValueError(
            "Only approved requests can be submitted to simulated procurement."
        )

    requests.at[index, "status"] = "Submitted to Simulated Procurement"
    requests.at[index, "decision_role"] = role
    requests.at[index, "timestamp"] = now_string()

    activity = _append_record(
        load_activity(),
        activity_name="Request submitted to simulated procurement",
        product_id=str(requests.at[index, "product_id"]),
        request_id=str(request_id),
        details=(
            "Status changed to Submitted to Simulated Procurement; "
            "no real order was placed."
        ),
        user_role=role,
    )

    _persist_decision_state(requests, activity)
