#!/usr/bin/env python3
"""
Modular Bank Transaction Categorizer
===================================

A streamlined Streamlit application for categorizing bank transactions using AI.
Now fully modularized with separated concerns and optimized performance.
"""

import streamlit as st
from src.compact_processor import CompactTransactionProcessor
from src.ui.styles import get_app_styles
from src.ui.components.navigation import create_navigation

# Import page modules
from src.ui.pages.process_transactions import render_process_transactions_page
from src.ui.pages.analytics import render_analytics_page
from src.ui.pages.vendor_payments import render_vendor_payments_page
from src.ui.pages.vendors import render_vendors_page
from src.ui.pages.database import render_database_page


def main():
    """Main application entry point with modular page routing."""
    # Set page configuration
    st.set_page_config(
        page_title="Bank Transaction Categorizer",
        layout="wide",
    )

    # Load consolidated CSS styles
    st.markdown(get_app_styles(), unsafe_allow_html=True)

    # Initialize session state for processor caching
    if "processor" not in st.session_state:
        st.session_state.processor = None

    # Create navigation and get selected page
    page = create_navigation()

    # Route to appropriate page module
    if page == "Process Transactions":
        render_process_transactions_page()
    elif page == "Analytics":
        # Initialize processor if needed for analytics
        processor = _get_or_create_processor()
        render_analytics_page(processor)
    elif page == "Vendor Payments":
        processor = _get_or_create_processor()
        render_vendor_payments_page(processor)
    elif page == "Vendors":
        processor = _get_or_create_processor()
        render_vendors_page(processor)
    elif page == "Database":
        processor = _get_or_create_processor()
        render_database_page(processor)


def _get_or_create_processor():
    """Get or create processor instance with caching."""
    if st.session_state.processor is None:
        # Use default settings - processor will be configured in process_transactions page
        st.session_state.processor = CompactTransactionProcessor(
            openai_api_key=None,  # Will use environment variable
            verify_domains=True
        )
    return st.session_state.processor


if __name__ == "__main__":
    main()