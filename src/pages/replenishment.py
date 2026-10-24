"""Replenishment Recommendations page for StockSense AI."""

import streamlit as st

from utils.app_theme import apply_app_theme
from utils.replenishment_page import render_replenishment_page


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Replenishment Recommendations · StockSense AI",
    page_icon="📦",
    layout="wide",
)


# --------------------------------------------------
# APPLY SHARED THEME
# --------------------------------------------------

apply_app_theme()


# --------------------------------------------------
# RENDER PAGE
# --------------------------------------------------

def main() -> None:
    """Display the replenishment recommendations page."""
    render_replenishment_page()


if __name__ == "__main__":
    main()