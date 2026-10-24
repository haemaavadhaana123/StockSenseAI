"""StockSense AI — Main Streamlit application."""

from __future__ import annotations

import os
import tempfile
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.app_theme import apply_app_theme
from utils.inventory_data import (
    enrich_inventory,
    load_inventory,
    valid_replenishment_candidates,
)
from utils.workflow_storage import (
    INVENTORY_FILE,
    DATA_DIR,
    set_storage_context,
    ensure_workflow_files,
    load_requests,
    load_activity,
    log_activity,
)
from utils.replenishment_page import render_replenishment_page
from utils.workflow_pages import (
    render_activity_log,
    render_approval_centre,
)

# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="StockSense AI",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_app_theme()

# =========================================================
# GENERAL HELPERS
# =========================================================


def now_string() -> str:
    """Return the current local time with timezone information."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def page_header(
    eyebrow: str,
    title: str,
    description: str,
) -> None:
    """Render a consistent page heading."""
    st.markdown(
        f"""
        <div class="eyebrow">{eyebrow}</div>
        <h1 style="margin-bottom:8px">{title}</h1>
        <p style="color:#91A1B7;margin-top:0;margin-bottom:25px">
            {description}
        </p>
        """,
        unsafe_allow_html=True,
    )


def save_inventory_safely(df: pd.DataFrame, destination=None) -> None:
    """Save inventory using a temporary file and atomic replacement."""
    path = Path(destination) if destination is not None else Path(INVENTORY_FILE)
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
            df.to_csv(handle, index=False)

        os.replace(temporary_path, path)

    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def load_app_data(inventory_source=None):
    """Initialise workflow files and load inventory and requests."""

    ensure_workflow_files()

    inventory = load_inventory(inventory_source)

    requests = load_requests()

    return inventory, requests


# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

st.sidebar.markdown(
    '<div class="brand">📦 Stock<span>Sense</span> AI</div>',
    unsafe_allow_html=True,
)

st.sidebar.caption("SMART INVENTORY INTELLIGENCE")
st.sidebar.divider()

page = st.sidebar.radio(
    "WORKSPACE",
    [
        "Dashboard",
        "Inventory Management",
        "Replenishment Recommendations",
        "Approval Centre",
        "Activity Log",
    ],
    key="main_workspace",
)

st.sidebar.divider()

st.sidebar.markdown("**SYSTEM STATUS**")

st.sidebar.markdown(
    '<span style="color:#34D399">●</span> '
    '<span style="color:#91A1B7">Demo environment</span>',
    unsafe_allow_html=True,
)

st.sidebar.caption("Purchasing actions require human approval.")

st.sidebar.divider()

st.sidebar.subheader("Company Inventory")

uploaded_inventory = st.sidebar.file_uploader(
    "Upload inventory CSV",
    type=["csv"],
    help=(
        "Upload a company inventory CSV containing the required "
        "StockSense AI inventory columns."
    ),
    key="company_inventory_upload",
)

if uploaded_inventory is not None:
    st.sidebar.success("Custom inventory selected")

else:
    st.sidebar.caption("Using the default sample inventory")

# =========================================================
# SELECT ACTIVE INVENTORY AND WORKFLOW STORAGE
# =========================================================

if uploaded_inventory is not None:
    upload_bytes = uploaded_inventory.getvalue()
    upload_hash = hashlib.sha256(upload_bytes).hexdigest()

    existing_custom_path = st.session_state.get("custom_inventory_path")
    if (
        st.session_state.get("custom_inventory_hash") != upload_hash
        or not existing_custom_path
        or not Path(existing_custom_path).exists()
    ):
        # A unique session work directory keeps custom workflow records isolated.
        work_dir = Path(tempfile.mkdtemp(prefix="stocksense_session_"))
        custom_path = work_dir / "inventory.csv"
        custom_path.write_bytes(upload_bytes)
        st.session_state["custom_inventory_hash"] = upload_hash
        st.session_state["custom_inventory_path"] = str(custom_path)
        st.session_state["custom_inventory_work_dir"] = str(work_dir)

    active_inventory_path = Path(st.session_state["custom_inventory_path"])
    active_workflow_dir = Path(st.session_state["custom_inventory_work_dir"])
else:
    active_inventory_path = Path(INVENTORY_FILE)
    active_workflow_dir = Path(DATA_DIR)

set_storage_context(active_inventory_path, active_workflow_dir)

# =========================================================
# INITIALISE AND LOAD DATA
# =========================================================

try:
    raw_inventory, requests = load_app_data(inventory_source=active_inventory_path)

    inventory = enrich_inventory(raw_inventory)

except (
    FileNotFoundError,
    ValueError,
    OSError,
    KeyError,
    TypeError,
    pd.errors.ParserError,
) as exc:
    st.error(
        "StockSense AI could not load its data. "
        "Check the inventory CSV and workflow files."
    )

    with st.expander("Technical details"):
        st.code(str(exc))

    st.stop()

# =========================================================
# STOCK STATUS GROUPS
# =========================================================

low_stock = inventory[inventory["stock_status"] == "Low Stock"]

out_of_stock = inventory[inventory["stock_status"] == "Out of Stock"]

normal_stock = inventory[inventory["stock_status"] == "Normal"]

invalid_stock = inventory[inventory["stock_status"] == "Invalid Data"]

# =========================================================
# DASHBOARD
# =========================================================

if page == "Dashboard":
    st.markdown(
        """
        <div class="hero">
            <div class="status-pill">✦ INVENTORY INTELLIGENCE</div>
            <h1>Your stock. Under control.</h1>
            <p>
                Monitor your grocery inventory, identify shortages,
                review replenishment recommendations, and keep
                purchasing decisions under human control.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="eyebrow">INVENTORY OVERVIEW</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("📦 Total Products", len(inventory))
    c2.metric("⚠️ Low Stock", len(low_stock))
    c3.metric("🚨 Out of Stock", len(out_of_stock))
    c4.metric("✓ Healthy Stock", len(normal_stock))

    st.divider()

    chart_col, summary_col = st.columns([1.25, 1])

    with chart_col:
        st.markdown(
            '<div class="panel">',
            unsafe_allow_html=True,
        )

        st.subheader("Stock health")
        st.caption("Products grouped by stock condition")

        chart = pd.DataFrame(
            {
                "Condition": [
                    "Healthy",
                    "Low stock",
                    "Out of stock",
                    "Invalid",
                ],
                "Products": [
                    len(normal_stock),
                    len(low_stock),
                    len(out_of_stock),
                    len(invalid_stock),
                ],
            }
        )

        chart = chart[chart["Products"] > 0]

        if not chart.empty:
            st.bar_chart(
                chart.set_index("Condition"),
                color="#34D399",
                height=260,
            )
        else:
            st.info("No inventory records available.")

        st.markdown("</div>", unsafe_allow_html=True)

    with summary_col:
        st.markdown(
            '<div class="panel">',
            unsafe_allow_html=True,
        )

        st.subheader("Needs your attention")

        st.markdown(
            f"""
            <div class="alert-row">
                <span style="color:#FCA5A5">● Out of stock</span>
                <div class="big-number">{len(out_of_stock)}</div>
                <span class="muted">
                    Products with zero units remaining
                </span>
            </div>

            <div class="alert-row">
                <span style="color:#FCD34D">● Low stock</span>
                <div class="big-number">{len(low_stock)}</div>
                <span class="muted">
                    Products below minimum stock
                </span>
            </div>

            <div class="good-row">
                <span style="color:#6EE7B7">● Healthy stock</span>
                <div class="big-number">{len(normal_stock)}</div>
                <span class="muted">
                    Products meeting stock requirements
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not invalid_stock.empty:
            st.warning(f"{len(invalid_stock)} record(s) have invalid data.")

        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------
    # PRIORITY REPLENISHMENT
    # -----------------------------------------------------

    st.subheader("Priority replenishment")

    try:
        attention = valid_replenishment_candidates(inventory)

    except (ValueError, KeyError, TypeError) as exc:
        st.error("Unable to calculate replenishment recommendations.")

        with st.expander("Technical details"):
            st.code(str(exc))

        attention = pd.DataFrame()

    if not attention.empty:
        attention = attention.copy()

        attention["suggested_quantity"] = (
            attention["target_stock"] - attention["current_stock"]
        ).clip(lower=0)

        display_labels = {
            "product_id": "Product ID",
            "product_name": "Product Name",
            "current_stock": "Quantity Available",
            "minimum_stock": "Minimum Required",
            "target_stock": "Desired Stock Level",
            "suggested_quantity": "Suggested Order Quantity",
            "supplier": "Supplier",
            "stock_status": "Stock Condition",
        }

        display_table = attention[list(display_labels.keys())].rename(
            columns=display_labels
        )

        st.dataframe(
            display_table,
            width="stretch",
            hide_index=True,
        )

        st.caption(
            "Suggested quantities are recommendations only. "
            "Human approval is required before simulated procurement."
        )

    else:
        st.success("No valid replenishment recommendations are currently required.")

    # -----------------------------------------------------
    # INVALID DATA REVIEW
    # -----------------------------------------------------

    if not invalid_stock.empty:
        with st.expander("Review invalid inventory records"):
            # Support the validation column used by the shared
            # inventory module without assuming an obsolete name.
            validation_column = next(
                (
                    column
                    for column in [
                        "validation_message",
                        "validation_issues",
                    ]
                    if column in invalid_stock.columns
                ),
                None,
            )

            review_columns = [
                column
                for column in [
                    "product_id",
                    "product_name",
                ]
                if column in invalid_stock.columns
            ]

            if validation_column:
                review_columns.append(validation_column)

            if review_columns:
                st.dataframe(
                    invalid_stock[review_columns],
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.warning(
                    "Invalid records exist, but no validation details are available."
                )

# =========================================================
# INVENTORY MANAGEMENT
# =========================================================

elif page == "Inventory Management":
    page_header(
        "INVENTORY WORKSPACE",
        "Inventory management",
        "Search, filter, inspect, and update your product catalogue.",
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total products", len(inventory))
    c2.metric("Low stock", len(low_stock))
    c3.metric("Out of stock", len(out_of_stock))
    c4.metric("Invalid records", len(invalid_stock))

    st.divider()

    search = st.text_input(
        "🔎 Search products",
        placeholder="Search product, ID, category, or supplier...",
        key="main_inventory_search",
    )

    status_filter = st.selectbox(
        "Filter by stock status",
        [
            "All statuses",
            "Normal",
            "Low Stock",
            "Out of Stock",
            "Invalid Data",
        ],
        key="main_inventory_status",
    )

    filtered = inventory.copy()

    if search.strip():
        mask = pd.Series(False, index=filtered.index)

        for column in [
            "product_id",
            "product_name",
            "category",
            "supplier",
        ]:
            if column in filtered.columns:
                mask |= (
                    filtered[column]
                    .fillna("")
                    .astype(str)
                    .str.contains(
                        search.strip(),
                        case=False,
                        regex=False,
                    )
                )

        filtered = filtered.loc[mask]

    if status_filter != "All statuses":
        filtered = filtered[filtered["stock_status"] == status_filter]

    st.caption(f"Showing {len(filtered)} of {len(inventory)} products")

    # Display the inventory table with user-friendly column names

    display_labels = {
        "product_id": "Product ID",
        "product_name": "Product Name",
        "category": "Category",
        "current_stock": "Quantity Available",
        "unit": "Unit",
        "minimum_stock": "Minimum Required",
        "target_stock": "Desired Stock Level",
        "supplier": "Supplier",
        "stock_status": "Stock Condition",
    }

    display_columns = list(display_labels.keys())

    display_table = filtered[display_columns].rename(columns=display_labels)

    st.dataframe(
        display_table,
        width="stretch",
        hide_index=True,
    )

    st.divider()
    st.subheader("Update stock quantity")

    product_ids = inventory["product_id"].fillna("").astype(str).str.strip()

    duplicate_mask = product_ids.ne("") & product_ids.duplicated(keep=False)

    if duplicate_mask.any():
        st.error(
            "Stock updates are disabled because duplicate product IDs "
            "were found. Correct the inventory CSV first."
        )

    else:
        product_options = inventory.loc[product_ids.ne("")].copy()

        if product_options.empty:
            st.warning("No products are available for stock updates.")

        else:
            product_options["selection_label"] = (
                product_options["product_id"].astype(str)
                + " — "
                + product_options["product_name"].fillna("").astype(str)
            )

            selected_label = st.selectbox(
                "Select product",
                product_options["selection_label"].tolist(),
                key="main_update_product",
            )

            selected_row = product_options.loc[
                product_options["selection_label"] == selected_label
            ].iloc[0]

            selected_id = str(selected_row["product_id"]).strip()
            old_quantity = selected_row["current_stock"]

            if pd.isna(old_quantity):
                old_quantity_display = "Invalid or missing"
                default_quantity = 0
            else:
                old_quantity_display = str(old_quantity)
                default_quantity = max(0, int(old_quantity))

            st.write(
                f"**{selected_row['product_name']}** — "
                f"Current quantity: {old_quantity_display}"
            )

            if "stock_update_error" not in st.session_state:
                st.session_state["stock_update_error"] = ""

            with st.form("main_stock_update_form"):
                new_quantity = st.number_input(
                    "New quantity",
                    min_value=0,
                    value=default_quantity,
                    step=1,
                )

                reason = st.text_input(
                    "Reason for stock update",
                    placeholder="e.g. Physical stock count",
                )

                confirmed = st.checkbox(
                    "I have verified this quantity and want to save it."
                )

                save_stock = st.form_submit_button(
                    "Save stock update",
                    type="primary",
                )

                if st.session_state["stock_update_error"]:
                    st.error(st.session_state["stock_update_error"])

                if save_stock:
                    if not reason.strip():
                        st.session_state["stock_update_error"] = (
                            "Please provide a reason for the stock update."
                        )

                        st.rerun()

                    elif not confirmed:
                        st.session_state["stock_update_error"] = (
                            "Please confirm that you verified the quantity before saving."
                        )

                        st.rerun()

                    else:
                        st.session_state["stock_update_error"] = ""
                        try:
                            latest = load_inventory(active_inventory_path)

                            latest_ids = (
                                latest["product_id"].fillna("").astype(str).str.strip()
                            )

                            matches = latest_ids == selected_id

                            if int(matches.sum()) != 1:
                                st.error(
                                    "The product ID is missing or ambiguous. "
                                    "No changes were saved."
                                )

                            else:
                                row_index = latest.index[matches][0]

                                previous_quantity = latest.at[
                                    row_index,
                                    "current_stock",
                                ]

                                updated = latest.copy()

                                updated.at[
                                    row_index,
                                    "current_stock",
                                ] = int(new_quantity)

                                updated.at[
                                    row_index,
                                    "last_updated",
                                ] = now_string()

                                # Verify the changed record using the
                                # shared inventory validation logic.
                                updated_enriched = enrich_inventory(updated)

                                changed_row = updated_enriched.loc[row_index]

                                if changed_row["stock_status"] == "Invalid Data":
                                    st.error(
                                        "The update would leave the product "
                                        "with invalid inventory data. "
                                        "No changes were saved."
                                    )

                                else:
                                    save_inventory_safely(
                                        updated, destination=active_inventory_path
                                    )

                                    previous_display = (
                                        "Missing or invalid"
                                        if pd.isna(previous_quantity)
                                        else str(previous_quantity)
                                    )

                                    try:
                                        log_activity(
                                            activity="Inventory stock updated",
                                            product_id=selected_id,
                                            details=(
                                                f"Previous quantity: "
                                                f"{previous_display}; "
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
                                    ) as log_error:
                                        st.error(
                                            "The inventory was saved, but its "
                                            "activity record could not be saved. "
                                            "The inventory change remains in place."
                                        )

                                        with st.expander("Logging error details"):
                                            st.code(str(log_error))

                                    else:
                                        st.session_state["main_stock_update_notice"] = (
                                            "Stock updated successfully and "
                                            "recorded in the activity log."
                                        )

                                        st.rerun()

                        except (
                            OSError,
                            ValueError,
                            KeyError,
                            TypeError,
                            pd.errors.ParserError,
                        ) as exc:
                            st.error("Unable to complete the inventory update.")

                            with st.expander("Technical details"):
                                st.code(str(exc))

# =========================================================
# REPLENISHMENT RECOMMENDATIONS
# =========================================================

elif page == "Replenishment Recommendations":
    render_replenishment_page(inventory_source=active_inventory_path)

# =========================================================
# APPROVAL CENTRE
# =========================================================

elif page == "Approval Centre":
    render_approval_centre()

# =========================================================
# ACTIVITY LOG
# =========================================================

elif page == "Activity Log":
    render_activity_log()

# =========================================================
# FOOTER
# =========================================================

st.divider()

st.markdown(
    """
    <div style="
        text-align:center;
        color:#718096;
        font-size:.8rem;
        padding:8px
    ">
        StockSense AI · Hackathon MVP · Synthetic data environment
        <br>
        Human approval required · No real purchase orders are placed
    </div>
    """,
    unsafe_allow_html=True,
)
