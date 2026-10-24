"""Inventory Management page for StockSense AI."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.app_theme import apply_app_theme
from utils.workflow_storage import (
    INVENTORY_FILE,
    ensure_workflow_files,
    log_activity,
)


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Inventory Management · StockSense AI",
    page_icon="📦",
    layout="wide",
)

apply_app_theme()


# =========================================================
# INVENTORY CONFIGURATION
# =========================================================

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

TEXT_COLUMNS = [
    "product_id",
    "product_name",
    "category",
    "unit",
    "supplier",
]

STOCK_STATUSES = [
    "Normal",
    "Low Stock",
    "Out of Stock",
    "Invalid Data",
]


# =========================================================
# INVENTORY LOADING
# =========================================================


def load_inventory() -> pd.DataFrame:
    """Load inventory data while preserving product IDs as text."""

    ensure_workflow_files()

    inventory_path = Path(INVENTORY_FILE)

    if not inventory_path.exists():
        raise FileNotFoundError(f"Inventory file not found: {inventory_path}")

    df = pd.read_csv(
        inventory_path,
        dtype={"product_id": "string"},
        keep_default_na=False,
    )

    # Standardise column names.
    df.columns = df.columns.astype(str).str.strip()

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "The inventory CSV is missing required columns: "
            + ", ".join(missing_columns)
        )

    # Preserve text fields and trim surrounding whitespace.
    for column in TEXT_COLUMNS:
        df[column] = df[column].astype("string").str.strip()

    # Convert stock fields to numeric values.
    # Invalid values become NaN and are identified by validation.
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # Prevent infinite values from being treated as valid stock.
    for column in NUMERIC_COLUMNS:
        df.loc[
            ~df[column].isin([float("inf"), float("-inf")]) & df[column].notna(),
            column,
        ] = df.loc[
            ~df[column].isin([float("inf"), float("-inf")]) & df[column].notna(),
            column,
        ]

        df.loc[
            df[column].isin([float("inf"), float("-inf")]),
            column,
        ] = float("nan")

    if "last_updated" not in df.columns:
        df["last_updated"] = ""

    return df


# =========================================================
# DATA VALIDATION
# =========================================================


def get_validation_errors(row: pd.Series) -> list[str]:
    """Return validation issues for one inventory record."""

    errors = []

    # Required text fields.
    for column in [
        "product_id",
        "product_name",
        "unit",
        "supplier",
    ]:
        value = row.get(column)

        if pd.isna(value) or not str(value).strip():
            errors.append(f"Missing {column.replace('_', ' ')}")

    # Required numeric fields.
    for column in NUMERIC_COLUMNS:
        value = row.get(column)

        if pd.isna(value):
            errors.append(f"Missing or invalid {column.replace('_', ' ')}")
            continue

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            errors.append(f"Invalid {column.replace('_', ' ')}")
            continue

        if numeric_value < 0:
            errors.append(f"Negative {column.replace('_', ' ')}")

        if numeric_value in (float("inf"), float("-inf")):
            errors.append(f"Invalid {column.replace('_', ' ')}")

    # Threshold consistency.
    current = row.get("current_stock")
    minimum = row.get("minimum_stock")
    target = row.get("target_stock")

    values_are_valid = all(
        pd.notna(value)
        and isinstance(value, (int, float))
        and value >= 0
        and value not in (float("inf"), float("-inf"))
        for value in [current, minimum, target]
    )

    if values_are_valid and target < minimum:
        errors.append("Target stock is below minimum stock")

    return errors


# =========================================================
# STOCK STATUS
# =========================================================


def get_stock_status(row: pd.Series) -> str:
    """Determine stock status using transparent business rules."""

    errors = get_validation_errors(row)

    if errors:
        return "Invalid Data"

    current = row["current_stock"]
    minimum = row["minimum_stock"]

    if current == 0:
        return "Out of Stock"

    if current < minimum:
        return "Low Stock"

    return "Normal"


# =========================================================
# INVENTORY SAVING
# =========================================================


def save_inventory(df: pd.DataFrame) -> None:
    """Save inventory using an atomic file replacement."""

    inventory_path = Path(INVENTORY_FILE)
    inventory_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Cannot save inventory because required columns are missing: "
            + ", ".join(missing_columns)
        )

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            suffix=".tmp",
            prefix=f".{inventory_path.name}.",
            dir=inventory_path.parent,
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)

            df.to_csv(
                handle,
                index=False,
            )

        os.replace(
            temporary_path,
            inventory_path,
        )

    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


# =========================================================
# INVENTORY PAGE
# =========================================================


def render_inventory_page() -> None:
    """Render the StockSense AI inventory dashboard."""

    st.title("📦 Inventory Management")

    st.caption(
        "Monitor stock levels, identify data issues, "
        "and record verified inventory updates."
    )

    st.info(
        "StockSense AI uses demonstration inventory data. "
        "Inventory updates are saved to the project CSV file. "
        "Replenishment requests remain subject to human approval."
    )

    # -----------------------------------------------------
    # LOAD DATA
    # -----------------------------------------------------

    try:
        inventory = load_inventory()

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        pd.errors.ParserError,
    ) as error:
        st.error("Unable to load inventory data. Please check the inventory CSV file.")

        with st.expander("Technical details"):
            st.code(str(error))

        return

    if inventory.empty:
        st.warning("No inventory records are available.")
        return

    # -----------------------------------------------------
    # DUPLICATE PRODUCT ID CHECK
    # -----------------------------------------------------

    product_ids = inventory["product_id"].fillna("").astype(str).str.strip()

    duplicate_mask = product_ids.ne("") & product_ids.duplicated(keep=False)

    if duplicate_mask.any():
        st.error(
            "Duplicate product IDs were found. "
            "Correct the IDs in the inventory CSV before "
            "updating stock or creating replenishment requests."
        )

        st.dataframe(
            inventory.loc[duplicate_mask],
            hide_index=True,
            width="stretch",
        )

        # Viewing remains available, but updates are blocked.
        duplicate_ids_found = True
    else:
        duplicate_ids_found = False

    # -----------------------------------------------------
    # CALCULATE STOCK STATUS
    # -----------------------------------------------------

    inventory["validation_errors"] = inventory.apply(
        get_validation_errors,
        axis=1,
    )

    inventory["stock_status"] = inventory.apply(
        get_stock_status,
        axis=1,
    )

    # -----------------------------------------------------
    # SUMMARY METRICS
    # -----------------------------------------------------

    total_products = len(inventory)

    normal_count = int((inventory["stock_status"] == "Normal").sum())

    low_stock_count = int((inventory["stock_status"] == "Low Stock").sum())

    out_of_stock_count = int((inventory["stock_status"] == "Out of Stock").sum())

    invalid_count = int((inventory["stock_status"] == "Invalid Data").sum())

    columns = st.columns(5)

    columns[0].metric(
        "Total Products",
        total_products,
    )

    columns[1].metric(
        "Normal",
        normal_count,
    )

    columns[2].metric(
        "Low Stock",
        low_stock_count,
    )

    columns[3].metric(
        "Out of Stock",
        out_of_stock_count,
    )

    columns[4].metric(
        "Invalid Records",
        invalid_count,
    )

    st.divider()

    # -----------------------------------------------------
    # SEARCH AND FILTERS
    # -----------------------------------------------------

    st.subheader("Inventory Overview")

    search_col, category_col, status_col = st.columns(3)

    with search_col:
        search_term = st.text_input(
            "🔍 Search products",
            placeholder="Product name, ID or supplier",
            key="inventory_search",
        )

    with category_col:
        categories = sorted(
            value
            for value in (inventory["category"].dropna().astype(str).unique())
            if value.strip()
        )

        selected_category = st.selectbox(
            "Category",
            ["All Categories"] + categories,
            key="inventory_category_filter",
        )

    with status_col:
        selected_status = st.selectbox(
            "Stock Status",
            ["All Statuses"] + STOCK_STATUSES,
            key="inventory_status_filter",
        )

    filtered = inventory.copy()

    if search_term.strip():
        search_text = search_term.strip()

        search_mask = pd.Series(
            False,
            index=filtered.index,
        )

        for column in [
            "product_id",
            "product_name",
            "supplier",
        ]:
            search_mask |= (
                filtered[column]
                .fillna("")
                .astype(str)
                .str.contains(
                    search_text,
                    case=False,
                    regex=False,
                )
            )

        filtered = filtered.loc[search_mask]

    if selected_category != "All Categories":
        filtered = filtered.loc[filtered["category"] == selected_category]

    if selected_status != "All Statuses":
        filtered = filtered.loc[filtered["stock_status"] == selected_status]

    display_columns = [
        "product_id",
        "product_name",
        "category",
        "current_stock",
        "minimum_stock",
        "target_stock",
        "unit",
        "supplier",
        "stock_status",
    ]

    st.dataframe(
        filtered[display_columns],
        hide_index=True,
        width="stretch",
    )

    st.caption(f"Showing {len(filtered)} of {total_products} products.")

    # -----------------------------------------------------
    # STOCK STATUS EXPLANATION
    # -----------------------------------------------------

    with st.expander("How StockSense AI determines stock status"):
        st.markdown(
            """
            - **Normal:** Current stock is at or above the minimum.
            - **Low Stock:** Current stock is below the minimum.
            - **Out of Stock:** Current stock is zero and the
              required data is valid.
            - **Invalid Data:** Required values are missing,
              negative, or inconsistent.

            StockSense AI uses transparent rules so that invalid
            records are not mistakenly treated as reliable stock alerts.
            """
        )

    st.divider()

    # -----------------------------------------------------
    # DATA QUALITY REVIEW
    # -----------------------------------------------------

    st.subheader("Data Quality Review")

    invalid_records = inventory.loc[inventory["stock_status"] == "Invalid Data"]

    if invalid_records.empty:
        st.success("All inventory records passed the current validation checks.")

    else:
        st.warning(f"{len(invalid_records)} record(s) need attention.")

        for _, row in invalid_records.iterrows():
            product_name = row.get("product_name", "")
            product_id = row.get("product_id", "")

            if pd.isna(product_name) or not str(product_name).strip():
                label = str(product_id).strip() or "Unknown product"
            else:
                label = str(product_name).strip()

            errors = get_validation_errors(row)

            st.markdown(f"**{label}** — " + "; ".join(errors))

    st.divider()

    # -----------------------------------------------------
    # UPDATE STOCK
    # -----------------------------------------------------

    st.subheader("Update Stock Quantity")

    st.write(
        "Select a product, enter its verified stock quantity, "
        "and explain why the quantity is changing."
    )

    if duplicate_ids_found:
        st.warning(
            "Stock updates are disabled until duplicate product IDs "
            "have been corrected in the inventory CSV."
        )
        return

    product_options = inventory.loc[
        inventory["product_id"].notna()
        & inventory["product_id"].astype(str).str.strip().ne("")
    ].copy()

    if product_options.empty:
        st.warning("No valid product IDs are available for stock updates.")
        return

    product_options["selection_label"] = (
        product_options["product_id"].astype(str)
        + " — "
        + product_options["product_name"].fillna("Unnamed product").astype(str)
    )

    selected_label = st.selectbox(
        "Select Product",
        product_options["selection_label"].tolist(),
        key="inventory_update_product",
    )

    selected_product = product_options.loc[
        product_options["selection_label"] == selected_label
    ].iloc[0]

    product_id = str(selected_product["product_id"]).strip()

    current_stock = selected_product["current_stock"]

    if pd.isna(current_stock):
        current_stock_display = "Unknown — invalid or missing value"
        default_quantity = 0
    else:
        current_stock_display = str(current_stock)
        default_quantity = max(
            0,
            int(current_stock),
        )

    st.write(f"**Current recorded stock:** {current_stock_display}")

    with st.form("inventory_update_form"):
        new_quantity = st.number_input(
            "Verified New Stock Quantity",
            min_value=0,
            value=default_quantity,
            step=1,
            help=(
                "Enter the physical stock quantity you have verified. "
                "Negative quantities are not allowed."
            ),
        )

        reason = st.text_area(
            "Reason for Update",
            placeholder=(
                "Example: Physical stock count completed after today's delivery."
            ),
            max_chars=500,
        )

        confirm_update = st.checkbox(
            "I have verified this quantity and want to save the update."
        )

        submitted = st.form_submit_button(
            "Save Inventory Update",
            type="primary",
            width="stretch",
        )

    if not submitted:
        return

    if not reason.strip():
        st.error("Please provide a reason for the stock update.")
        return

    if not confirm_update:
        st.error("Please confirm that you have verified the quantity.")
        return

    # -----------------------------------------------------
    # VALIDATE AND SAVE THE UPDATE
    # -----------------------------------------------------

    try:
        # Reload the latest saved file to avoid relying solely
        # on the data originally loaded when the page opened.
        latest_inventory = load_inventory()

        latest_ids = latest_inventory["product_id"].fillna("").astype(str).str.strip()

        matching_rows = latest_ids == product_id

        if int(matching_rows.sum()) != 1:
            st.error("The product ID is missing or ambiguous. No changes were saved.")
            return

        row_index = latest_inventory.index[matching_rows][0]

        old_quantity = latest_inventory.at[
            row_index,
            "current_stock",
        ]

        if pd.isna(old_quantity):
            old_quantity_display = "Missing or invalid"
        else:
            old_quantity_display = str(old_quantity)

        updated_inventory = latest_inventory.copy()

        updated_inventory.at[
            row_index,
            "current_stock",
        ] = int(new_quantity)

        updated_inventory.at[
            row_index,
            "last_updated",
        ] = datetime.now().astimezone().isoformat(timespec="seconds")

        # Revalidate the updated record before saving.
        updated_row = updated_inventory.loc[row_index]
        updated_errors = get_validation_errors(updated_row)

        if updated_errors:
            st.error(
                "The updated inventory record is invalid: " + "; ".join(updated_errors)
            )
            return

        # Save the inventory first.
        save_inventory(updated_inventory)

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        pd.errors.ParserError,
    ) as error:
        st.error("The inventory update could not be saved.")

        with st.expander("Technical details"):
            st.code(str(error))

        return

    # -----------------------------------------------------
    # RECORD ACTIVITY
    # -----------------------------------------------------

    try:
        log_activity(
            activity="Inventory stock updated",
            product_id=product_id,
            request_id="",
            details=(
                f"Previous quantity: {old_quantity_display}; "
                f"new quantity: {int(new_quantity)}; "
                f"reason: {reason.strip()}"
            ),
            user_role="Inventory Manager",
        )

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        pd.errors.ParserError,
    ) as error:
        st.error(
            "The inventory quantity was saved, but its activity "
            "record could not be written. The stock update was not "
            "rolled back. Please resolve this issue before relying "
            "on the activity log."
        )

        with st.expander("Technical details"):
            st.code(str(error))

        return

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    st.session_state["inventory_update_notice"] = (
        f"Stock for {selected_product['product_name']} "
        "was updated successfully and recorded in the activity log."
    )

    st.rerun()


# =========================================================
# PAGE ENTRY POINT
# =========================================================


def main() -> None:
    """Run the inventory page."""

    notice = st.session_state.pop(
        "inventory_update_notice",
        None,
    )

    if notice:
        st.success(notice)

    render_inventory_page()


if __name__ == "__main__":
    main()
