import streamlit as st
import pandas as pd

from utils.replenishment import (
    create_replenishment_requests,
    load_recommendations,
)
from utils.workflow_storage import load_requests


SUCCESS_STATE_KEY = "replenishment_success_notice"


def _format_product(product_id, product_names):
    """Format a product ID and name for selection."""
    name = product_names.get(str(product_id), "")

    return f"{product_id} — {name}" if name else str(product_id)


def _render_replenishment_content(inventory_source=None):
    """Render the replenishment recommendation interface."""

    st.markdown(
        """
        <div class="eyebrow">SMART REPLENISHMENT</div>
        <h1 style="margin-bottom:8px">
            Replenishment recommendations
        </h1>
        <p style="color:#91A1B7;margin-top:0;margin-bottom:25px">
            Review suggested quantities before preparing simulated requests.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # Display a success message after a successful submission.
    success_notice = st.session_state.pop(
        SUCCESS_STATE_KEY,
        None,
    )

    if success_notice:
        st.success(success_notice)

    st.info(
        "Recommendations are decision support, not purchase orders. "
        "Review every quantity before creating a simulated request. "
        "A human must approve requests, and no real purchase is made."
    )

    # Load recommendations and existing requests.
    try:
        recommendations = load_recommendations(inventory_source)
        requests = load_requests()

    except Exception as error:
        import traceback

        st.error("Unable to create simulated replenishment requests.")

        st.caption("No real purchase order is placed by this action.")

        with st.expander("Technical error details", expanded=True):
            st.code(traceback.format_exc())
        return

    recommendations = recommendations.copy()
    requests = requests.copy()

    # Normalise product IDs for consistent comparisons.
    if not recommendations.empty:
        recommendations["product_id"] = (
            recommendations["product_id"].astype(str).str.strip()
        )

        # --------------------------------------------------
        # RECOMMENDATIONS
        # --------------------------------------------------

        st.subheader("Recommended for review")

        if recommendations.empty:
            st.success("No valid replenishment recommendations are currently required.")

        else:
            display_columns = [
                column
                for column in [
                    "product_id",
                    "product_name",
                    "category",
                    "current_stock",
                    "unit",
                    "minimum_stock",
                    "target_stock",
                    "proposed_quantity",
                    "supplier",
                    "stock_status",
                    "validation_message",
                ]
                if column in recommendations.columns
            ]

            # User-friendly column names
            friendly_names = {
                "product_id": "Product ID",
                "product_name": "Product Name",
                "category": "Category",
                "current_stock": "Quantity Available",
                "unit": "Unit",
                "minimum_stock": "Minimum Required",
                "target_stock": "Desired Stock Level",
                "proposed_quantity": "Suggested Order Quantity",
                "supplier": "Supplier",
                "stock_status": "Stock Condition",
                "validation_message": "Validation Result",
            }

            # Configure number formatting using the displayed column names
            column_config = {}

            if "proposed_quantity" in display_columns:
                column_config["Suggested Order Quantity"] = (
                    st.column_config.NumberColumn(
                        "Suggested Order Quantity",
                        format="%.15g",
                    )
                )

            for quantity_column, friendly_name in {
                "current_stock": "Quantity Available",
                "minimum_stock": "Minimum Required",
                "target_stock": "Desired Stock Level",
            }.items():
                if quantity_column in display_columns:
                    column_config[friendly_name] = st.column_config.NumberColumn(
                        friendly_name,
                        format="%.15g",
                    )

            if "validation_message" in display_columns:
                column_config["Validation Result"] = st.column_config.TextColumn(
                    "Validation Result",
                    width="large",
                )

            # Rename columns for display
            display_table = recommendations[display_columns].rename(
                columns=friendly_names
            )

            st.dataframe(
                display_table,
                width="stretch",
                hide_index=True,
                column_config=column_config,
            )

            st.divider()

        # --------------------------------------------------
        # PREPARE SIMULATED REQUESTS
        # --------------------------------------------------

        st.subheader("Prepare simulated requests")

        required_request_columns = {
            "status",
            "product_id",
        }

        if not required_request_columns.issubset(requests.columns):
            st.error("Request data is missing required status or product fields.")
            return

        # Identify existing pending requests consistently.
        pending_mask = (
            requests["status"]
            .astype("string")
            .str.strip()
            .str.casefold()
            .eq("pending")
            .fillna(False)
        )

        existing_pending_ids = set(
            requests.loc[
                pending_mask,
                "product_id",
            ]
            .dropna()
            .astype(str)
            .str.strip()
        )

        # Exclude products that already have pending requests.
        available = recommendations[
            ~recommendations["product_id"].isin(existing_pending_ids)
        ].copy()

        if available.empty:
            st.info("All eligible products already have pending requests.")

        else:
            product_names = dict(
                zip(
                    available["product_id"],
                    available["product_name"].astype(str),
                )
            )

            with st.form("prepare_requests_form"):
                selected_products = st.multiselect(
                    "Select products",
                    available["product_id"].tolist(),
                    format_func=lambda product_id: _format_product(
                        product_id,
                        product_names,
                    ),
                )

                create_requests = st.form_submit_button("Create simulated requests")

            if create_requests:
                if not selected_products:
                    st.warning("Select at least one product.")

                else:
                    try:
                        created_count = create_replenishment_requests(
                            [str(product_id) for product_id in selected_products],
                            user_role="Inventory Manager",
                            inventory_source=inventory_source,
                        )

                        if created_count < 1:
                            st.warning(
                                "No requests were created. Review the "
                                "selected products and their proposed "
                                "quantities."
                            )

                        else:
                            st.session_state[SUCCESS_STATE_KEY] = (
                                f"Created {created_count} simulated "
                                "request(s). They are ready for human "
                                "review in the Approval Centre."
                            )

                            st.rerun()

                    except Exception as error:
                        st.error("Unable to create simulated replenishment requests.")

                        st.caption("No real purchase order is placed by this action.")

                        st.code(str(error))

    # --------------------------------------------------
    # EXISTING REQUESTS
    # --------------------------------------------------

    st.divider()
    st.subheader("Existing requests")

    try:
        requests = load_requests()

    except Exception as error:
        st.error("Unable to load existing requests.")
        st.code(str(error))
        return

    if requests.empty:
        st.caption("No requests have been created yet.")

    else:
        # Display existing requests with user-friendly column headings

        display_requests = requests.copy()

        friendly_labels = {
            "request_id": "Request ID",
            "product_id": "Product ID",
            "product_name": "Product Name",
            "proposed_quantity": "Requested Quantity",
            "unit": "Unit",
            "supplier": "Supplier",
            "timestamp": "Request Date & Time",
            "status": "Request Status",
            "decision": "Decision Details",
            "decision_reason": "Decision Reason",
            "created_at": "Created At",
            "updated_at": "Last Updated",
        }

        display_requests = display_requests.rename(columns=friendly_labels)

        # Format timestamps so they are easier to read

        for column in ["Request Date & Time", "Created At", "Last Updated"]:
            if column in display_requests.columns:
                display_requests[column] = pd.to_datetime(
                    display_requests[column],
                    errors="coerce",
                    utc=True,
                ).dt.strftime("%d %b %Y, %I:%M %p")

        sisplay_requests = requests.copy()

        friendly_labels = {
            # Your column mappings
        }

        display_requests = display_requests.rename(columns=friendly_labels)

        for column in ["Request Date & Time", "Created At", "Last Updated"]:
            if column in display_requests.columns:
                display_requests[column] = pd.to_datetime(
                    display_requests[column],
                    errors="coerce",
                    utc=True,
                ).dt.strftime("%d %b %Y, %I:%M %p")


def render_replenishment_page(inventory_source=None):
    """Render the complete replenishment page with its styling."""

    st.markdown(
        """
        <style>
        [data-testid="stMainBlockContainer"]:has(.st-key-replenishment) {
            padding-top: 4.5rem;
        }

        .st-key-replenishment h1 {
            font-size: clamp(1.8rem, 3vw, 2.6rem);
        }

        .st-key-replenishment [data-testid="stWidgetLabel"] p,
        .st-key-replenishment [data-testid="stCaptionContainer"] {
            color: #A9B9CB;
        }

        .st-key-replenishment [data-testid="stAlert"] p {
            color: #E2E8F0;
        }

        .st-key-replenishment [data-baseweb="select"] > div {
            background-color: #111D2B;
            border-color: rgba(148, 163, 184, .3);
            color: #F1F5F9;
        }

        .st-key-replenishment [data-baseweb="select"] input {
            color: #F1F5F9;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="replenishment"):
        _render_replenishment_content(inventory_source)
