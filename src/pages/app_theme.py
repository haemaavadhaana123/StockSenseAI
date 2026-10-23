"""Shared visual theme and reusable UI styles for StockSense AI."""

import streamlit as st


def apply_app_theme() -> None:
    """Apply the StockSense AI dashboard theme to the Streamlit app."""

    st.markdown(
        """
<style>
/* ==================================================
   STOCKSENSE AI — DESIGN TOKENS
   ================================================== */

:root {
    color-scheme: dark;

    --bg: #080D16;
    --panel: #101925;
    --panel-raised: #152131;
    --border: rgba(148, 163, 184, 0.18);

    --text: #F1F5F9;
    --muted: #91A1B7;

    --green: #34D399;
    --green-dark: #059669;
    --cyan: #67E8F9;

    --danger: #FCA5A5;
    --warning: #FCD34D;

    --radius: 16px;
}

/* ==================================================
   APPLICATION BACKGROUND
   ================================================== */

.stApp {
    background:
        radial-gradient(
            ellipse at 5% 0%,
            rgba(16, 185, 129, 0.10),
            transparent 32%
        ),
        radial-gradient(
            ellipse at 95% 5%,
            rgba(34, 211, 238, 0.07),
            transparent 28%
        ),
        var(--bg);

    color: var(--text);
    font-family: "DM Sans", sans-serif;
}

/* Use locally available fonts first, with fallbacks. */
.stApp,
[data-testid="stAppViewContainer"] {
    font-family:
        "DM Sans",
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

h1,
h2,
h3 {
    color: var(--text) !important;
    font-family:
        "Space Grotesk",
        "DM Sans",
        sans-serif !important;
    letter-spacing: -0.5px;
}

h1 {
    font-weight: 700 !important;
}

h2,
h3 {
    font-weight: 600 !important;
}

p,
label,
li {
    line-height: 1.6;
}

/* ==================================================
   PAGE LAYOUT
   ================================================== */

.block-container {
    max-width: 1500px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #101925 0%,
        #0B121D 100%
    );

    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: var(--muted);
}

/* ==================================================
   METRIC CARDS
   ================================================== */

div[data-testid="stMetric"] {
    background: linear-gradient(
        145deg,
        rgba(21, 33, 49, 0.96),
        rgba(13, 22, 34, 0.96)
    );

    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    min-height: 115px;

    transition:
        transform 0.2s ease,
        border-color 0.2s ease;
}

div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    border-color: rgba(52, 211, 153, 0.45);
}

div[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
}

div[data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-family:
        "Space Grotesk",
        "DM Sans",
        sans-serif !important;
    font-weight: 700;
}

/* ==================================================
   DATA TABLES
   ================================================== */

div[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
}

/* ==================================================
   BUTTONS
   ================================================== */

.stButton > button,
.stFormSubmitButton > button {
    background: linear-gradient(
        110deg,
        var(--green-dark),
        #10B981
    );

    color: #FFFFFF;
    border: 1px solid rgba(52, 211, 153, 0.4);
    border-radius: 10px;

    padding: 0.6rem 1rem;
    font-weight: 600;

    transition:
        background 0.2s ease,
        border-color 0.2s ease,
        transform 0.2s ease;
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background: linear-gradient(
        110deg,
        #10B981,
        #34D399
    );

    border-color: #6EE7B7;
    color: #06130F;
}

.stButton > button:focus-visible,
.stFormSubmitButton > button:focus-visible {
    outline: 2px solid var(--cyan);
    outline-offset: 3px;
}

.stButton > button:disabled,
.stFormSubmitButton > button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
    transform: none;
}

/* ==================================================
   INPUTS
   ================================================== */

.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
.stDateInput input,
.stTimeInput input {
    background-color: #111D2B;
    border-color: var(--border);
    border-radius: 9px;
    color: var(--text);
}

.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--green);
    box-shadow: 0 0 0 1px var(--green);
}

/* ==================================================
   SELECTBOX AND MULTISELECT
   ================================================== */

.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div {
    background-color: #111D2B;
    border-color: var(--border);
    border-radius: 9px;
}

/* ==================================================
   ALERTS AND NOTIFICATIONS
   ================================================== */

div[data-testid="stAlert"] {
    border-radius: 12px;
}

/* ==================================================
   DIVIDERS AND CAPTIONS
   ================================================== */

hr {
    border-color: var(--border);
}

[data-testid="stCaptionContainer"] {
    color: var(--muted);
}

/* ==================================================
   STOCKSENSE BRAND
   ================================================== */

.brand {
    font-family:
        "Space Grotesk",
        "DM Sans",
        sans-serif;

    font-size: 1.45rem;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: -0.8px;
}

.brand span {
    color: var(--green);
}

.eyebrow {
    color: var(--green);
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 8px;
}

/* ==================================================
   REUSABLE HERO SECTION
   ================================================== */

.hero {
    background:
        radial-gradient(
            ellipse at 100% 0%,
            rgba(52, 211, 153, 0.18),
            transparent 45%
        ),
        linear-gradient(
            135deg,
            #142333,
            #0E1926 65%,
            #10231F
        );

    border: 1px solid rgba(52, 211, 153, 0.23);
    border-radius: 22px;

    padding: 30px;
    margin-bottom: 26px;

    animation: stocksense-enter 0.45s ease-out both;
}

.hero h1 {
    font-size: clamp(1.7rem, 3vw, 2.5rem);
    margin: 0 0 8px 0;
}

.hero p {
    color: #A9B9CB;
    margin-bottom: 0;
    max-width: 680px;
    line-height: 1.7;
}

.status-pill {
    display: inline-block;

    background: rgba(52, 211, 153, 0.10);
    border: 1px solid rgba(52, 211, 153, 0.28);

    color: #6EE7B7;
    border-radius: 100px;

    padding: 7px 12px;
    font-size: 0.76rem;
    font-weight: 600;
    margin-bottom: 18px;
}

/* ==================================================
   REUSABLE PANELS
   ================================================== */

.panel {
    background: linear-gradient(
        145deg,
        #111D2B,
        #0E1723
    );

    border: 1px solid var(--border);
    border-radius: 17px;

    padding: 22px;
    margin-bottom: 16px;

    transition: border-color 0.2s ease;
}

.panel:hover {
    border-color: rgba(103, 232, 249, 0.28);
}

.muted {
    color: var(--muted);
    font-size: 0.87rem;
}

.big-number {
    font-family:
        "Space Grotesk",
        "DM Sans",
        sans-serif;

    font-size: 2rem;
    font-weight: 700;
    color: #F8FAFC;
    margin: 8px 0;
}

/* ==================================================
   STATUS ROWS
   ================================================== */

.alert-row {
    background: rgba(248, 113, 113, 0.06);
    border: 1px solid rgba(248, 113, 113, 0.20);
    border-radius: 11px;

    padding: 13px 15px;
    margin: 8px 0;
}

.good-row {
    background: rgba(52, 211, 153, 0.06);
    border: 1px solid rgba(52, 211, 153, 0.20);
    border-radius: 11px;

    padding: 13px 15px;
    margin: 8px 0;
}

/* ==================================================
   ANIMATION
   ================================================== */

@keyframes stocksense-enter {
    from {
        opacity: 0;
        transform: translateY(8px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Respect reduced-motion preferences. */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}

/* ==================================================
   RESPONSIVE LAYOUT
   ================================================== */

@media (max-width: 700px) {
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    .hero {
        padding: 22px;
        border-radius: 16px;
    }

    div[data-testid="stMetric"] {
        padding: 14px;
        min-height: 95px;
    }

    .panel {
        padding: 16px;
    }
}
</style>
""",
        unsafe_allow_html=True,
    )
