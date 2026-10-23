"""Approval centre and activity-log pages for StockSense AI."""

import pandas as pd
import streamlit as st

from utils.workflow_storage import (
    REQUEST_COLUMNS,
    ACTIVITY_COLUMNS,
    ALLOWED_REQUEST_STATUSES,
    load_requests,
    load_activity,
    adjust_request_quantity,
    decide_request,
    submit_to_simulated_procurement,
)


# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------

DECISION_ROLES = [
    "Inventory Manager",
    "Business Owner",
    "Procurement Manager",
]

REQUEST_STATUSES = [
    "All",
    "Pending",
    "Approved",
    "Rejected",
    "Submitted to Simulated Procurement",
]


# --------------------------------------------------
# SHARED HELPERS
# --------------------------------------------------


def _page_header(title: str, description: str) -> None:
    """Display a consistent page heading."""
    st.title(title)
    st.caption(description)


def _show_notice() -> None:
    """Display a notice saved after a workflow action."""
    notice = st.session_state.pop("workflow_notice", None)

    if not notice:
        return

    level, message = notice

    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    elif level == "error":
        st.error(message)
    else:
        st.info(message)


def _handle_action(action, success_message: str) -> None:
    """Execute a workflow action and report its result."""
    try:
        result = action()

        if result is False:
            st.session_state["workflow_notice"] = (
                "info",
                "No changes were needed.",
            )
        else:
            st.session_state["workflow_notice"] = (
                "success",
                success_message,
            )

    except (ValueError, KeyError, TypeError, OSError, pd.errors.ParserError) as exc:
        st.session_state["workflow_notice"] = (
            "error",
            str(exc),
        )

    st.rerun()


def _format_request_label(row: pd.Series) -> str:
    """Create a readable label for a request selection."""
    request_id = str(row.get("request_id", "")).strip()
    product_name = str(row.get("product_name", "")).strip()
    product_id = str(row.get("product_id", "")).strip()
    quantity = row.get("proposed_quantity", "")
    unit = str(row.get("unit", "")).strip()

    quantity_text = f"{quantity} {unit}".strip()

    return f"{request_id} | {product_name} ({product_id}) | {quantity_text}"


def _valid_positive_quantity(value) -> bool:
    """Check whether a quantity is a positive finite number."""
    try:
        quantity = float(value)
        return (
            quantity > 0
            and pd.notna(quantity)
            and quantity != float("inf")
            and quantity != float("-inf")
        )
    except (TypeError, ValueError):
        return False


def _request_status_counts(requests: pd.DataFrame) -> dict:
    """Return counts for the available request statuses."""
    statuses = requests["status"].fillna("").astype(str).str.strip()

    return {
        status: int(statuses.eq(status).sum())
        for status in REQUEST_STATUSES
        if status != "All"
    }


# --------------------------------------------------
# APPROVAL CENTRE
# --------------------------------------------------


def render_approval_centre() -> None:
    """Render the request approval and simulated procurement interface."""
    _page_header(
        "Replenishment Approval Centre",
        (
            "Review replenishment requests, adjust quantities, "
            "approve or reject requests, and simulate procurement."
        ),
    )

    st.info(
        "Demo workflow: selecting a role identifies the role recorded "
        "in the activity log. It does not authenticate the user or "
        "enforce real access permissions. No real purchase orders are placed."
    )

    _show_notice()

    try:
        requests = load_requests()
    except (OSError, ValueError, KeyError, TypeError, pd.errors.ParserError) as exc:
        st.error(f"Unable to load replenishment requests: {exc}")
        return

    if requests.empty:
        st.info(
            "There are no replenishment requests yet. "
            "Create requests from the Replenishment page first."
        )
        return

    # ----------------------------------------------
    # SUMMARY
    # ----------------------------------------------

    counts = _request_status_counts(requests)

    summary_columns = st.columns(4)

    summary_columns[0].metric(
        "Pending",
        counts.get("Pending", 0),
    )
    summary_columns[1].metric(
        "Approved",
        counts.get("Approved", 0),
    )
    summary_columns[2].metric(
        "Rejected",
        counts.get("Rejected", 0),
    )
    summary_columns[3].metric(
        "Simulated Procurement",
        counts.get("Submitted to Simulated Procurement", 0),
    )

    st.divider()

    # ----------------------------------------------
    # REQUEST SEARCH AND FILTERS
    # ----------------------------------------------

    st.subheader("Request Overview")

    search = st.text_input(
        "Search requests",
        placeholder="Search by request ID, product name, or product ID",
        key="approval_search",
    )

    status_filter = st.selectbox(
        "Filter by status",
        REQUEST_STATUSES,
        key="approval_status_filter",
    )

    visible = requests.copy()

    if status_filter != "All":
        visible = visible[
            visible["status"].fillna("").astype(str).str.strip() == status_filter
        ]

    if search.strip():
        search_text = search.strip().casefold()

        searchable_columns = [
            "request_id",
            "product_id",
            "product_name",
            "supplier",
        ]

        mask = pd.Series(False, index=visible.index)

        for column in searchable_columns:
            mask |= (
                visible[column]
                .fillna("")
                .astype(str)
                .str.casefold()
                .str.contains(search_text, regex=False)
            )

        visible = visible[mask]

    overview_columns = [
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

    st.dataframe(
        visible[overview_columns],
        hide_index=True,
        width="stretch",
    )

    # ----------------------------------------------
    # REQUEST ACTIONS
    # ----------------------------------------------

    st.divider()
    st.subheader("Review a Request")

    pending = requests[
        requests["status"].fillna("").astype(str).str.strip() == "Pending"
    ].copy()

    approved = requests[
        requests["status"].fillna("").astype(str).str.strip() == "Approved"
    ].copy()

    if pending.empty and approved.empty:
        st.info(
            "There are no pending requests to review and no approved "
            "requests awaiting simulated procurement."
        )
        return

    role = st.selectbox(
        "Acting role (demo only)",
        DECISION_ROLES,
        key="approval_decision_role",
    )

    # ----------------------------------------------
    # ADJUST PENDING QUANTITY
    # ----------------------------------------------

    if not pending.empty:
        st.markdown("### Adjust a Pending Request")

        adjustment_options = {
            _format_request_label(row): str(row["request_id"])
            for _, row in pending.iterrows()
        }

        selected_adjustment = st.selectbox(
            "Choose a pending request",
            list(adjustment_options.keys()),
            key="adjust_request_selection",
        )

        adjustment_id = adjustment_options[selected_adjustment]

        selected_row = pending[pending["request_id"].astype(str) == adjustment_id].iloc[
            0
        ]

        current_quantity = selected_row["proposed_quantity"]

        try:
            default_quantity = float(current_quantity)
            if not _valid_positive_quantity(default_quantity):
                default_quantity = 1.0
        except (TypeError, ValueError):
            default_quantity = 1.0

        with st.form("adjust_quantity_form"):
            new_quantity = st.number_input(
                "New proposed quantity",
                min_value=0.01,
                value=default_quantity,
                step=1.0,
            )

            adjustment_reason = st.text_input(
                "Reason for quantity adjustment",
                placeholder="Explain why the quantity is changing",
            )

            adjust_submitted = st.form_submit_button(
                "Save Quantity Adjustment",
                type="primary",
            )

        if adjust_submitted:
            if not _valid_positive_quantity(new_quantity):
                st.error("Enter a valid quantity greater than zero.")
            elif not adjustment_reason.strip():
                st.error("Please provide a reason for the adjustment.")
            else:
                _handle_action(
                    lambda: adjust_request_quantity(
                        request_id=adjustment_id,
                        quantity=new_quantity,
                        user_role=role,
                        adjustment_reason=adjustment_reason,
                    ),
                    "Request quantity updated and activity recorded.",
                )

    # ----------------------------------------------
    # APPROVE OR REJECT
    # ----------------------------------------------

    if not pending.empty:
        st.markdown("### Approve or Reject a Request")

        decision_options = {
            _format_request_label(row): str(row["request_id"])
            for _, row in pending.iterrows()
        }

        selected_decision = st.selectbox(
            "Choose a request to review",
            list(decision_options.keys()),
            key="decision_request_selection",
        )

        decision_id = decision_options[selected_decision]

        with st.form("decision_form"):
            decision = st.radio(
                "Decision",
                ["Approve", "Reject"],
                horizontal=True,
            )

            decision_notes = st.text_area(
                "Decision notes (optional for approval)",
                placeholder="Add any relevant notes",
            )

            rejection_reason = ""

            if decision == "Reject":
                rejection_reason = st.text_area(
                    "Reason for rejection (required)",
                    placeholder="Explain why this request is rejected",
                )

            decision_submitted = st.form_submit_button(
                "Submit Decision",
                type="primary",
            )

        if decision_submitted:
            if decision == "Reject" and not rejection_reason.strip():
                st.error("A rejection reason is required.")
            else:
                _handle_action(
                    lambda: decide_request(
                        request_id=decision_id,
                        decision=("Approved" if decision == "Approve" else "Rejected"),
                        user_role=role,
                        rejection_reason=rejection_reason,
                        decision_reason=decision_notes,
                    ),
                    (
                        "Request approved."
                        if decision == "Approve"
                        else "Request rejected and reason recorded."
                    ),
                )

    # ----------------------------------------------
    # SIMULATED PROCUREMENT
    # ----------------------------------------------

    if not approved.empty:
        st.divider()
        st.markdown("### Simulated Procurement")

        st.caption(
            "This step records a simulated procurement submission only. "
            "It does not contact suppliers or place an actual order."
        )

        procurement_options = {
            _format_request_label(row): str(row["request_id"])
            for _, row in approved.iterrows()
        }

        selected_procurement = st.selectbox(
            "Choose an approved request",
            list(procurement_options.keys()),
            key="procurement_request_selection",
        )

        procurement_id = procurement_options[selected_procurement]

        confirm_procurement = st.checkbox(
            "I confirm that this is a simulated submission only.",
            key="confirm_simulated_procurement",
        )

        if st.button(
            "Submit to Simulated Procurement",
            type="primary",
            disabled=not confirm_procurement,
        ):
            _handle_action(
                lambda: submit_to_simulated_procurement(
                    request_id=procurement_id,
                    user_role=role,
                ),
                "Request submitted to simulated procurement.",
            )


# --------------------------------------------------
# ACTIVITY LOG
# --------------------------------------------------


def render_activity_log() -> None:
    """Render a searchable and downloadable activity log."""
    _page_header(
        "Activity Log",
        (
            "Review recorded replenishment activity, including request "
            "creation, quantity adjustments, decisions, and simulated procurement."
        ),
    )

    _show_notice()

    try:
        activity = load_activity()
    except (OSError, ValueError, KeyError, TypeError, pd.errors.ParserError) as exc:
        st.error(f"Unable to load the activity log: {exc}")
        return

    if activity.empty:
        st.info(
            "No activity has been recorded yet. Actions performed in the "
            "replenishment and approval workflows will appear here."
        )
        return

    activity = activity.copy()

    for column in ACTIVITY_COLUMNS:
        if column not in activity.columns:
            activity[column] = ""

    for column in ACTIVITY_COLUMNS:
        activity[column] = activity[column].fillna("").astype(str)

    activity["timestamp_sort"] = pd.to_datetime(
        activity["timestamp"],
        errors="coerce",
    )

    activity = activity.sort_values(
        "timestamp_sort",
        ascending=False,
        na_position="last",
    )

    # ----------------------------------------------
    # FILTERS
    # ----------------------------------------------

    st.subheader("Filter Activity")

    search = st.text_input(
        "Search activity",
        placeholder="Search details, activity, product ID, or request ID",
        key="activity_search",
    )

    activity_types = sorted(
        value for value in activity["activity"].unique() if value.strip()
    )

    selected_type = st.selectbox(
        "Activity type",
        ["All"] + activity_types,
        key="activity_type_filter",
    )

    filtered = activity.copy()

    if selected_type != "All":
        filtered = filtered[filtered["activity"] == selected_type]

    if search.strip():
        search_text = search.strip().casefold()

        searchable_columns = [
            "timestamp",
            "activity",
            "product_id",
            "request_id",
            "details",
            "user_role",
        ]

        mask = pd.Series(False, index=filtered.index)

        for column in searchable_columns:
            mask |= (
                filtered[column].str.casefold().str.contains(search_text, regex=False)
            )

        filtered = filtered[mask]

    st.metric("Matching activity records", len(filtered))

    display_columns = [
        "timestamp",
        "activity",
        "product_id",
        "request_id",
        "details",
        "user_role",
    ]

    st.dataframe(
        filtered[display_columns],
        hide_index=True,
        width="stretch",
    )

    # ----------------------------------------------
    # CSV EXPORT
    # ----------------------------------------------

    st.download_button(
        label="Download Activity Log (CSV)",
        data=filtered[display_columns].to_csv(index=False).encode("utf-8"),
        file_name="stocksense_activity_log.csv",
        mime="text/csv",
    )
