"""Activity Log page for StockSense AI."""

import streamlit as st

from utils.app_theme import apply_app_theme
from utils.workflow_pages import render_activity_log


st.set_page_config(
    page_title="Activity Log · StockSense AI",
    page_icon="📦",
    layout="wide",
)

apply_app_theme()

render_activity_log()
