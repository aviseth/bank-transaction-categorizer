"""Vendors page module.

Provides vendor management interface with search, edit, and metrics functionality.
"""

import ast
import time
from typing import Dict, List, Any

import pandas as pd
import streamlit as st

from src.ui.components.navigation import show_page_header


class VendorsPage:
    """Vendors page with search, edit capabilities, and metrics."""

    def __init__(self, processor):
        self.processor = processor

    def render(self):
        """Render the Vendors page."""
        show_page_header(
            "Vendors",
            "Manage vendor information and view vendor metrics"
        )

        try:
            vendors = self.processor.get_all_vendors()

            if vendors:
                df = pd.DataFrame(vendors)

                # Render search and metrics section
                search = self._render_search_and_metrics(df)

                # Apply search filter
                if search:
                    mask = df["name"].str.contains(search, case=False, na=False)
                    df = df[mask]

                # Render vendor editing interface
                self._render_vendor_editing_interface(df)
            else:
                st.info("No vendors found.")
        except Exception as e:
            st.error(f"Error loading vendors: {str(e)}")
            st.info("Process transactions first.")

    def _render_search_and_metrics(self, df: pd.DataFrame) -> str:
        """Render search and metrics section. Returns search term."""
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        with col1:
            search = st.text_input("Search vendors:")

        with col2:
            st.metric("Total Vendors", len(df))

        with col3:
            with_domains = len(df[df["domain"].notna()])
            st.metric("With Domains", with_domains)

        with col4:
            services = len(df[df["product_type"] == "services"])
            st.metric("Services", services)

        return search

    def _render_vendor_editing_interface(self, df: pd.DataFrame):
        """Render vendor editing interface."""
        st.markdown("### Edit Vendor Information")
        st.markdown(
            "*Edit vendor information directly in the table. Click 'Save' to update any changes.*"
        )

        # Initialize editing state
        if "vendor_edits" not in st.session_state:
            st.session_state.vendor_edits = {}

        # Prepare editable vendor data
        edited_vendors = self._prepare_vendor_data(df)

        # Display editable form
        if edited_vendors:
            self._render_vendor_form(edited_vendors)

    def _prepare_vendor_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare vendor data for editing interface."""
        edited_vendors = []

        for _, vendor in df.iterrows():
            vendor_id = vendor["id"]

            # Fix nicknames display - ensure it's a proper list
            nicknames = vendor.get("nicknames", [])
            if isinstance(nicknames, str):
                # If it's stored as a string, try to parse it properly
                try:
                    nicknames = (
                        ast.literal_eval(nicknames)
                        if nicknames.startswith("[")
                        else nicknames.split(",")
                    )
                except:
                    nicknames = [nicknames] if nicknames else []
            elif not isinstance(nicknames, list):
                nicknames = []

            nicknames_str = ", ".join(
                [nick.strip() for nick in nicknames if nick and nick.strip()]
            )

            edited_vendor = {
                "id": vendor_id,
                "name": vendor["name"] or "",
                "domain": vendor["domain"] or "",
                "description": vendor["description"] or "",
                "country": vendor["country"] or "",
                "currency": vendor["currency"] or "",
                "product_type": vendor["product_type"] or "services",
                "nicknames": nicknames_str,
                "transactions": vendor["transaction_count"],
            }
            edited_vendors.append(edited_vendor)

        return edited_vendors

    def _render_vendor_form(self, edited_vendors: List[Dict[str, Any]]):
        """Render the vendor editing form."""
        with st.form("vendor_editing_form"):
            st.markdown("**Edit vendors below and click 'Save All Changes' when done:**")

            # Render table headers
            self._render_table_headers()
            st.markdown("---")

            # Collect updated data
            updated_data = self._render_vendor_rows(edited_vendors)

            # Render action buttons
            self._render_action_buttons(updated_data)

    def _render_table_headers(self):
        """Render table column headers."""
        col_headers = st.columns([1.8, 1.2, 2.5, 0.8, 0.8, 0.8, 1.5, 0.6])
        headers = ["Company", "Domain", "Description", "Country", "Currency", "Type", "Nicknames", "#"]

        for col, header in zip(col_headers, headers):
            with col:
                st.markdown(f"**{header}**")

    def _render_vendor_rows(self, edited_vendors: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """Render vendor editing rows and collect updated data."""
        updated_data = {}

        for vendor in edited_vendors:
            cols = st.columns([1.8, 1.2, 2.5, 0.8, 0.8, 0.8, 1.5, 0.6])

            # Company name
            with cols[0]:
                new_name = st.text_input(
                    "Company Name",
                    value=vendor["name"],
                    key=f"name_{vendor['id']}",
                    label_visibility="collapsed",
                    help=vendor["name"],
                )

            # Domain
            with cols[1]:
                new_domain = st.text_input(
                    "Domain",
                    value=vendor["domain"],
                    key=f"domain_{vendor['id']}",
                    label_visibility="collapsed",
                    help=vendor["domain"],
                )

            # Description
            with cols[2]:
                new_description = st.text_area(
                    "Description",
                    value=vendor["description"],
                    height=60,
                    key=f"desc_{vendor['id']}",
                    label_visibility="collapsed",
                    help=vendor["description"],
                )

            # Country
            with cols[3]:
                new_country = st.text_input(
                    "Country",
                    value=vendor["country"],
                    key=f"country_{vendor['id']}",
                    label_visibility="collapsed",
                    max_chars=3,
                    help=vendor["country"],
                )

            # Currency
            with cols[4]:
                new_currency = st.text_input(
                    "Currency",
                    value=vendor["currency"],
                    key=f"currency_{vendor['id']}",
                    label_visibility="collapsed",
                    max_chars=3,
                    help=vendor["currency"],
                )

            # Product type
            with cols[5]:
                new_product_type = st.selectbox(
                    "Product Type",
                    options=["services", "goods"],
                    index=0 if vendor["product_type"] == "services" else 1,
                    key=f"type_{vendor['id']}",
                    label_visibility="collapsed",
                )

            # Nicknames
            with cols[6]:
                new_nicknames = st.text_input(
                    "Nicknames",
                    value=vendor["nicknames"],
                    key=f"nicknames_{vendor['id']}",
                    label_visibility="collapsed",
                    help=vendor["nicknames"],
                )

            # Transaction count
            with cols[7]:
                st.markdown(
                    f"<center><small><b>{vendor['transactions']}</b></small></center>",
                    unsafe_allow_html=True,
                )

            # Store the updated data
            updated_data[vendor["id"]] = {
                "name": new_name.strip(),
                "domain": new_domain.strip() if new_domain.strip() else None,
                "default_description": new_description.strip() if new_description.strip() else None,
                "invoicing_country": new_country.strip().upper() if new_country.strip() else None,
                "default_currency": new_currency.strip().upper() if new_currency.strip() else None,
                "default_product_type": new_product_type,
                "nicknames": new_nicknames.strip(),
            }

        return updated_data

    def _render_action_buttons(self, updated_data: Dict[int, Dict[str, Any]]):
        """Render action buttons and handle save/refresh."""
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 4])

        with col1:
            save_all = st.form_submit_button("Save All Changes", type="primary")

        with col2:
            refresh_data = st.form_submit_button("Refresh Data")

        # Handle button actions
        if save_all:
            self._handle_save_all(updated_data)

        if refresh_data:
            st.rerun()

    def _handle_save_all(self, updated_data: Dict[int, Dict[str, Any]]):
        """Handle saving all vendor updates."""
        success_count = 0
        error_count = 0

        for vendor_id, data in updated_data.items():
            if self.processor.update_vendor(vendor_id, data):
                success_count += 1
            else:
                error_count += 1

        if success_count > 0:
            st.success(f"Successfully updated {success_count} vendor(s)!")

        if error_count > 0:
            st.error(f"Failed to update {error_count} vendor(s).")

        if success_count > 0:
            time.sleep(1)
            st.rerun()


def render_vendors_page(processor):
    """Entry point for rendering the Vendors page."""
    page = VendorsPage(processor)
    page.render()