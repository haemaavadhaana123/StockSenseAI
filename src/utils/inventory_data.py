from pathlib import Path

import pandas as pd


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INVENTORY_PATH = BASE_DIR / "data" / "sample_inventory.csv"

REQUIRED_COLUMNS = [
    "product_id",
    "product_name",
    "category",
    "unit",
    "current_stock",
    "minimum_stock",
    "target_stock",
    "supplier",
]

NUMERIC_COLUMNS = [
    "current_stock",
    "minimum_stock",
    "target_stock",
]


# --------------------------------------------------
# LOAD INVENTORY
# --------------------------------------------------


def load_inventory(source=None):
    """Load and validate an inventory CSV path or file-like object."""
    if source is None:
        inventory_source = DEFAULT_INVENTORY_PATH
        if not inventory_source.exists():
            raise FileNotFoundError(f"Inventory file not found: {inventory_source}")
    else:
        inventory_source = source

    try:
        df = pd.read_csv(
            inventory_source,
            dtype={"product_id": "string"},
            keep_default_na=False,
        )
    except pd.errors.EmptyDataError as exc:
        raise ValueError("The inventory CSV is empty.") from exc
    except pd.errors.ParserError as exc:
        raise ValueError("The inventory CSV could not be parsed.") from exc

    if df.empty:
        raise ValueError("The inventory CSV contains no product records.")

    df.columns = df.columns.astype(str).str.strip()
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in df.columns
    ]
    if missing_columns:
        raise ValueError(
            "Inventory CSV is missing required columns: " + ", ".join(missing_columns)
        )

    text_columns = ["product_id", "product_name", "category", "unit", "supplier"]
    for column in text_columns:
        df[column] = df[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


# --------------------------------------------------
# VALIDATE INVENTORY RECORDS
# --------------------------------------------------


def validation_errors(row):
    """
    Return a list of validation errors for one inventory record.

    An empty list means no validation errors were found.
    """

    errors = []

    # Check required text fields.
    required_text_fields = {
        "product_id": "Product ID is missing.",
        "product_name": "Product name is missing.",
        "category": "Product category is missing.",
        "unit": "Unit of measurement is missing.",
        "supplier": "Supplier is missing.",
    }

    for column, message in required_text_fields.items():
        value = row.get(column)

        if pd.isna(value) or not str(value).strip():
            errors.append(message)

    # Check numeric fields.
    numeric_values = {}

    for column in NUMERIC_COLUMNS:
        value = row.get(column)

        if pd.isna(value):
            errors.append(
                f"{column.replace('_', ' ').capitalize()} must be a valid number."
            )
        else:
            try:
                numeric_values[column] = float(value)
            except (TypeError, ValueError):
                errors.append(
                    f"{column.replace('_', ' ').capitalize()} must be a valid number."
                )

    # Perform further checks only when the relevant values are valid.
    for column, value in numeric_values.items():
        if value < 0:
            errors.append(
                f"{column.replace('_', ' ').capitalize()} cannot be negative."
            )

    current = numeric_values.get("current_stock")
    minimum = numeric_values.get("minimum_stock")
    target = numeric_values.get("target_stock")

    if minimum is not None and target is not None:
        if minimum >= 0 and target >= 0 and target < minimum:
            errors.append("Target stock cannot be lower than minimum stock.")

    # Detect an inconsistent stock configuration.
    # A target stock below the current stock is allowed:
    # it simply means replenishment may not be necessary.
    if current is not None and minimum is not None:
        if current >= 0 and minimum >= 0 and current < 0:
            errors.append("Invalid current stock value.")

    return errors


# --------------------------------------------------
# DETERMINE STOCK STATUS
# --------------------------------------------------


def stock_status(row):
    """
    Determine the stock status of one inventory record.

    Possible results:
        Invalid Data
        Out of Stock
        Low Stock
        Normal
    """

    # Invalid records must not receive normal stock statuses.
    if validation_errors(row):
        return "Invalid Data"

    current = float(row["current_stock"])
    minimum = float(row["minimum_stock"])

    if current == 0:
        return "Out of Stock"

    if current < minimum:
        return "Low Stock"

    return "Normal"


# --------------------------------------------------
# ENRICH INVENTORY DATA
# --------------------------------------------------


def enrich_inventory(df):
    """
    Add stock status and validation messages to inventory data.

    Returns a copy of the original DataFrame with:
        stock_status
        validation_message
    """

    result = df.copy()

    result["validation_message"] = result.apply(
        lambda row: "; ".join(validation_errors(row)),
        axis=1,
    )

    result["stock_status"] = result.apply(
        stock_status,
        axis=1,
    )

    return result


# --------------------------------------------------
# GET VALID REPLENISHMENT CANDIDATES
# --------------------------------------------------


def valid_replenishment_candidates(df):
    """
    Return only valid inventory records that need replenishment.

    A product qualifies when its status is:
        Low Stock
        Out of Stock

    Invalid inventory records are excluded.
    """

    enriched = enrich_inventory(df)

    candidates = enriched[
        enriched["stock_status"].isin(["Low Stock", "Out of Stock"])
    ].copy()

    return candidates


# --------------------------------------------------
# FIND DUPLICATE PRODUCT IDS
# --------------------------------------------------


def duplicate_product_ids(df):
    """
    Return product IDs that appear more than once.

    This function can be used during inventory quality checks.
    """

    if "product_id" not in df.columns:
        raise ValueError("Inventory data must contain a product_id column.")

    product_ids = df["product_id"].astype("string").str.strip()

    valid_ids = product_ids[product_ids.notna() & product_ids.ne("")]

    duplicates = valid_ids[valid_ids.duplicated(keep=False)]

    return sorted(duplicates.unique().tolist())
