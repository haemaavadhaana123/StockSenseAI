"""Approval Centre page for StockSense AI."""

import streamlit as st

from utils.app_theme import apply_app_theme
from utils.workflow_pages import render_approval_centre


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Approval Centre · StockSense AI",
    page_icon="📦",
    layout="wide",
)


# --------------------------------------------------
# APPLY SHARED THEME
# --------------------------------------------------

apply_app_theme()


# --------------------------------------------------
# RENDER APPROVAL CENTRE
# --------------------------------------------------


def main() -> None:
    """Display the shared approval workflow."""
    try:
        render_approval_centre()

    except Exception as error:
        st.error("The Approval Centre could not be loaded.")

        st.info(
            "Please check the inventory data, replenishment request "
            "CSV, and shared workflow modules."
        )

        with st.expander("Technical details"):
            st.code(str(error))


if __name__ == "__main__":
    main()
