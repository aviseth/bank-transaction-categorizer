"""Vendor Payments page module.

Displays vendor payment transactions with filtering and metrics.
"""

import pandas as pd
import streamlit as st
from typing import Dict, List, Any

from src.ui.components.navigation import show_page_header


class VendorPaymentsPage:
    """Vendor Payments page with filtering and metrics."""

    def __init__(self, processor):
        self.processor = processor

    def render(self):
        """Render the Vendor Payments page."""
        show_page_header(
            "Vendor Payments",
            "View and filter vendor payment transactions"
        )

        try:
            vendor_payments = self.processor.get_vendor_payments()

            if vendor_payments:
                df = pd.DataFrame(vendor_payments)

                # Render latest batch section
                self._render_latest_batch_section()

                st.divider()

                # Render filters section
                min_confidence, selected_vendors = self._render_filters(df)

                # Apply filters
                filtered_df = self._apply_filters(df, min_confidence, selected_vendors)

                # Render metrics
                self._render_metrics(filtered_df)

                # Display data table
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.info("No vendor payments found.")
        except Exception as e:
            st.error(f"Error loading vendor payments: {e}")
            st.info("Process transactions first.")

    def _render_filters(self, df: pd.DataFrame) -> tuple:
        """Render filters section and return filter values."""
        col1, col2 = st.columns([0.6, 2.4])

        with col1:
            # Import confidence calculator to get dynamic options
            from src.confidence_calculator import ConfidenceCalculator
            calc = ConfidenceCalculator()
            confidence_options = calc.get_confidence_range_options(0.1)
            min_confidence = st.selectbox(
                "Minimum Confidence",
                options=confidence_options,
                index=0,  # Default to 0%
                format_func=lambda x: f"{x:.0%}",
                help="Filter transactions by minimum confidence level",
            )

        with col2:
            vendors = df["vendor_name"].unique()
            selected_vendors = st.multiselect(
                "Filter by Vendor",
                vendors,
                default=vendors,
                help="Select vendors to display in the table below",
            )

        return min_confidence, selected_vendors

    def _apply_filters(self, df: pd.DataFrame, min_confidence: float, selected_vendors: List[str]) -> pd.DataFrame:
        """Apply filters to the dataframe."""
        return df[
            (df["vendor_confidence"] >= min_confidence)
            & (df["vendor_name"].isin(selected_vendors))
        ]

    def _render_metrics(self, filtered_df: pd.DataFrame):
        """Render metrics section."""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Payments", len(filtered_df))

        with col2:
            total = filtered_df["amount"].sum()
            st.metric("Total", f"{total:,.0f} DKK")

        with col3:
            unique = filtered_df["vendor_name"].nunique()
            st.metric("Vendors", unique)

        with col4:
            avg_conf = filtered_df["vendor_confidence"].mean()
            st.metric("Confidence", f"{avg_conf:.1%}")

    def _render_latest_batch_section(self):
        """Render section showing transactions from the latest processing batch."""
        st.markdown("### Latest Processing Batch")

        try:
            from src.models import Transaction, get_db_session

            session = get_db_session()

            # Get the most recent batch_id
            latest_batch = session.query(Transaction.batch_id).filter(
                Transaction.batch_id.isnot(None),
                Transaction.category == 'vendor_payment'
            ).order_by(Transaction.created_at.desc()).first()

            if not latest_batch:
                st.info("No recent processing batches found.")
                session.close()
                return

            latest_batch_id = latest_batch[0]

            # Get all vendor payments from the latest batch
            latest_transactions = session.query(Transaction).filter(
                Transaction.batch_id == latest_batch_id,
                Transaction.category == 'vendor_payment'
            ).order_by(Transaction.created_at.desc()).all()

            if not latest_transactions:
                st.info("No vendor payments found in latest batch.")
                session.close()
                return

            # Create DataFrame
            batch_data = []
            for t in latest_transactions:
                batch_data.append({
                    'Date': t.date.strftime('%Y-%m-%d') if t.date else 'N/A',
                    'Amount': f"{t.amount:,.2f} DKK",
                    'Vendor': getattr(t.vendor, 'name', 'Unknown') if t.vendor else 'Unknown',
                    'Confidence': f"{t.vendor_confidence:.2f}" if t.vendor_confidence else 'N/A',
                    'Match Source': t.vendor_match_source or 'Unknown',
                    'Description': t.text[:50] + '...' if len(t.text) > 50 else t.text
                })

            batch_df = pd.DataFrame(batch_data)

            # Show metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Latest Batch Transactions", len(batch_df))

            with col2:
                total_amount = sum(abs(t.amount) for t in latest_transactions)
                st.metric("Total Amount", f"{total_amount:,.0f} DKK")

            with col3:
                unique_vendors = batch_df['Vendor'].nunique()
                st.metric("Unique Vendors", unique_vendors)

            with col4:
                # Count match sources
                llm_count = len([t for t in latest_transactions if t.vendor_match_source == 'llm'])
                cache_count = len([t for t in latest_transactions if t.vendor_match_source == 'cache'])
                db_count = len([t for t in latest_transactions if t.vendor_match_source == 'database'])
                st.metric("New LLM Calls", llm_count)

            # Show match source breakdown
            st.markdown("#### Vendor Matching Breakdown")
            match_col1, match_col2, match_col3 = st.columns(3)

            with match_col1:
                st.metric("LLM Enriched", llm_count, help="New vendors enriched via LLM API calls")

            with match_col2:
                st.metric("Cache Hits", cache_count, help="Vendors found in processing cache")

            with match_col3:
                st.metric("Database Matches", db_count, help="Vendors matched from existing database records")

            # Display table
            st.markdown("#### Latest Batch Details")
            st.dataframe(
                batch_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Match Source": st.column_config.TextColumn(
                        help="How the vendor was matched: llm=new AI call, cache=processing cache, database=existing record"
                    )
                }
            )

            session.close()

        except Exception as e:
            st.error(f"Error loading latest batch data: {e}")
            import traceback
            st.code(traceback.format_exc())


def render_vendor_payments_page(processor):
    """Entry point for rendering the Vendor Payments page."""
    page = VendorPaymentsPage(processor)
    page.render()