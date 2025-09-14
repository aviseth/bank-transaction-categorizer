"""Consolidated CSS styles for the Bank Transaction Categorizer.

This module consolidates all styling from the original 689-line CSS block
into a clean, maintainable structure with no duplication.
"""

import streamlit as st


@st.cache_data
def get_app_styles() -> str:
    """Get consolidated application styles with dark monochrome theme."""
    return """
<style>
    /* Import Inclusive Sans font */
    @import url('https://fonts.googleapis.com/css2?family=Inclusive+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&display=swap');

    /* Global dark theme */
    .stApp {
        background: #0a0a0a !important;
        font-family: 'Inclusive Sans', sans-serif !important;
    }

    /* Main content container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    /* Headers with consistent styling */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inclusive Sans', sans-serif !important;
        color: #ffffff !important;
        font-weight: 600;
    }

    /* Navigation container styling */
    .nav-container {
        position: relative;
        margin-bottom: 2rem;
        padding-bottom: 0.5rem;
        display: block;
        width: 100%;
    }

    /* Force no gaps in Streamlit columns */
    .nav-container .row-widget.stHorizontalBlock {
        gap: 0rem !important;
    }

    .nav-container .row-widget > div {
        gap: 0rem !important;
    }

    .nav-container [data-testid="column"] {
        gap: 0rem !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }

    /* Navigation columns with no gaps */
    .nav-container [data-testid="column"] {
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        flex: 1 !important;
        min-width: 0 !important;
    }

    /* Remove all spacing between columns */
    .nav-container [data-testid="column"]:not(:last-child) {
        margin-right: 0 !important;
        border-right: none !important;
    }

    /* Navigation buttons - transparent with sliding border */
    .nav-container .stButton > button {
        background: transparent !important;
        border: 2px solid transparent !important;
        color: #ffffff !important;
        border-radius: 0px !important;
        padding: 0.75rem 1rem !important;
        transition: all 0.3s ease !important;
        font-weight: 500 !important;
        width: 100% !important;
        position: relative;
        z-index: 2;
        font-family: 'Inclusive Sans', sans-serif !important;
        margin: 0 !important;
    }

    /* Button containers with no spacing */
    .nav-container .stButton {
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* First and last buttons rounded corners */
    .nav-container [data-testid="column"]:first-child .stButton > button {
        border-radius: 8px 0 0 8px !important;
    }

    .nav-container [data-testid="column"]:last-child .stButton > button {
        border-radius: 0 8px 8px 0 !important;
    }

    /* Sliding border element */
    .nav-container .sliding-border {
        position: absolute;
        top: 0;
        left: 0;
        width: 20%;
        height: 100%;
        border: 3px solid #ffffff;
        border-radius: 8px;
        transition: transform 0.3s ease, opacity 0.3s ease;
        opacity: 1;
        z-index: 1;
        pointer-events: none;
        box-shadow: 0 0 20px rgba(255, 255, 255, 0.3);
        background: rgba(255, 255, 255, 0.05);
    }


    /* Regular button styling for non-navigation buttons */
    .stButton > button:not(.nav-container .stButton > button) {
        background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%) !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        font-family: 'Inclusive Sans', sans-serif !important;
        font-weight: 500 !important;
        padding: 0.75rem 1.5rem !important;
        transition: all 0.2s ease !important;
        min-height: 3rem !important;
    }

    .stButton > button:not(.nav-container .stButton > button):hover {
        background: linear-gradient(135deg, #2a2a2a 0%, #3a3a3a 100%) !important;
        border-color: #555 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    }

    /* Primary button variant for regular buttons */
    .stButton > button[kind="primary"]:not(.nav-container .stButton > button) {
        background: linear-gradient(135deg, #4a9eff 0%, #357abd 100%) !important;
        border-color: #4a9eff !important;
    }

    .stButton > button[kind="primary"]:not(.nav-container .stButton > button):hover {
        background: linear-gradient(135deg, #357abd 0%, #2c5f8f 100%) !important;
        border-color: #357abd !important;
    }

    /* Unified input styling */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input {
        background-color: #1a1a1a !important;
        border: 1px solid #333 !important;
        border-radius: 6px !important;
        color: #ffffff !important;
        font-family: 'Inclusive Sans', sans-serif !important;
        padding: 0.75rem !important;
    }

    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #4a9eff !important;
        box-shadow: 0 0 0 2px rgba(74, 158, 255, 0.2) !important;
    }

    /* File uploader styling */
    .stFileUploader > div > div {
        background-color: #1a1a1a !important;
        border: 2px dashed #333 !important;
        border-radius: 8px !important;
        padding: 2rem !important;
    }

    .stFileUploader > div > div:hover {
        border-color: #4a9eff !important;
        background-color: #1e1e1e !important;
    }

    /* Progress bars */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #4a9eff 0%, #357abd 100%) !important;
        border-radius: 10px !important;
    }

    .stProgress > div > div {
        background-color: #333 !important;
        border-radius: 10px !important;
    }

    /* Metrics and KPI cards */
    .metric-container {
        background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%) !important;
        border: 1px solid #333 !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        margin: 0.5rem 0 !important;
    }

    /* Data tables */
    .stDataFrame {
        background-color: #1a1a1a !important;
        border-radius: 8px !important;
        border: 1px solid #333 !important;
    }

    .stDataFrame tbody tr {
        background-color: #1a1a1a !important;
        border-bottom: 1px solid #333 !important;
    }

    .stDataFrame tbody tr:hover {
        background-color: #2a2a2a !important;
    }

    .stDataFrame thead tr {
        background-color: #0f0f0f !important;
        border-bottom: 2px solid #4a9eff !important;
    }

    /* Charts and plots */
    .stPlotlyChart {
        background-color: transparent !important;
        border-radius: 8px !important;
    }

    /* Sidebar styling */
    .css-1d391kg {
        background-color: #0f0f0f !important;
        border-right: 1px solid #333 !important;
    }

    /* Navigation */
    .css-1544g2n {
        background-color: #1a1a1a !important;
        border-radius: 6px !important;
        padding: 0.5rem !important;
    }

    /* Alerts and messages */
    .stAlert {
        border-radius: 8px !important;
        border-left: 4px solid #4a9eff !important;
        background-color: rgba(74, 158, 255, 0.1) !important;
    }

    .stSuccess {
        border-left-color: #28a745 !important;
        background-color: rgba(40, 167, 69, 0.1) !important;
    }

    .stError {
        border-left-color: #dc3545 !important;
        background-color: rgba(220, 53, 69, 0.1) !important;
    }

    .stWarning {
        border-left-color: #ffc107 !important;
        background-color: rgba(255, 193, 7, 0.1) !important;
    }

    /* Checkbox and radio styling */
    .stCheckbox, .stRadio {
        color: #ffffff !important;
    }

    /* Expander styling */
    .stExpander {
        background-color: #1a1a1a !important;
        border: 1px solid #333 !important;
        border-radius: 8px !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1a1a1a !important;
        border-radius: 8px !important;
        padding: 0.25rem !important;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        border-radius: 6px !important;
        color: #ffffff !important;
        padding: 0.75rem 1.5rem !important;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #4a9eff !important;
        color: #ffffff !important;
    }

    /* Caption and small text */
    .css-1629p8f, .css-16huue1 {
        color: #888 !important;
        font-size: 0.875rem !important;
    }

    /* Custom utility classes */
    .status-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 0.5rem;
    }

    .status-success { background-color: #28a745; }
    .status-warning { background-color: #ffc107; }
    .status-error { background-color: #dc3545; }
    .status-info { background-color: #4a9eff; }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""


def apply_styles():
    """Apply the consolidated styles to the Streamlit app."""
    st.markdown(get_app_styles(), unsafe_allow_html=True)


def create_metric_card(
    title: str, value: str, delta: str = None, delta_color: str = "normal"
):
    """Create a styled metric card with consistent formatting."""
    delta_html = ""
    if delta:
        color = (
            "#28a745"
            if delta_color == "normal"
            else "#dc3545"
            if delta_color == "inverse"
            else "#888"
        )
        delta_html = f'<div style="color: {color}; font-size: 0.875rem; margin-top: 0.25rem;">{delta}</div>'

    return f"""
    <div class="metric-container">
        <div style="color: #888; font-size: 0.875rem; margin-bottom: 0.25rem;">{title}</div>
        <div style="font-size: 2rem; font-weight: 600; color: #ffffff;">{value}</div>
        {delta_html}
    </div>
    """


def status_indicator(status: str) -> str:
    """Create a colored status indicator."""
    status_map = {
        "success": "status-success",
        "completed": "status-success",
        "warning": "status-warning",
        "pending": "status-warning",
        "error": "status-error",
        "failed": "status-error",
        "info": "status-info",
        "processing": "status-info",
    }

    css_class = status_map.get(status.lower(), "status-info")
    return f'<span class="status-indicator {css_class}"></span>'
