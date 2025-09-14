"""Database page module.

Provides database management interface with stats, deletion, reset, and export functionality.
"""

import time
from typing import Dict, List, Any

import pandas as pd
import streamlit as st

from src.models import Transaction
from src.ui.components.navigation import show_page_header


class DatabasePage:
    """Database management page with stats and operations."""

    def __init__(self, processor):
        self.processor = processor

    def render(self):
        """Render the Database page."""
        show_page_header(
            "Database",
            "View database statistics and manage data"
        )

        # Render database statistics
        self._render_database_stats()

        st.divider()

        # Render transaction categories breakdown
        self._render_transaction_categories()

        st.divider()

        # Render database operations
        self._render_database_operations()

    def _render_database_stats(self):
        """Render database statistics section."""
        stats = self.processor.get_database_stats()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Transactions", stats["total_transactions"])

        with col2:
            st.metric("Total Vendors", stats["total_vendors"])

        with col3:
            st.metric("Vendor Payments", stats["vendor_payments"])

        # Date range as a separate row to give it more space
        st.markdown("### Database Date Range")
        self._render_date_range_info(stats["date_range"])

    def _render_date_range_info(self, date_range: Dict):
        """Render date range information with full space."""
        if date_range["earliest"] and date_range["latest"]:
            earliest = (
                date_range["earliest"].strftime("%Y-%m-%d")
                if date_range["earliest"]
                else "N/A"
            )
            latest = (
                date_range["latest"].strftime("%Y-%m-%d")
                if date_range["latest"]
                else "N/A"
            )
            st.info(f"**Data spans from {earliest} to {latest}**")
        else:
            st.warning("No transaction data found in database")

    def _render_date_range_metric(self, date_range: Dict):
        """Render date range metric."""
        if date_range["earliest"] and date_range["latest"]:
            earliest = (
                date_range["earliest"].strftime("%Y-%m-%d")
                if date_range["earliest"]
                else "N/A"
            )
            latest = (
                date_range["latest"].strftime("%Y-%m-%d")
                if date_range["latest"]
                else "N/A"
            )
            st.metric("Date Range", f"{earliest} to {latest}")
        else:
            st.metric("Date Range", "No data")

    def _render_transaction_categories(self):
        """Render transaction categories breakdown."""
        st.markdown("### Transaction Categories")

        try:
            from src.models import Transaction, get_db_session
            from sqlalchemy import func
            import pandas as pd

            session = get_db_session()

            # Get category distribution
            categories = session.query(
                Transaction.category,
                func.count(Transaction.id).label('count'),
                func.sum(func.abs(Transaction.amount)).label('total_amount')
            ).group_by(Transaction.category).all()

            if categories:
                # Create DataFrame for better display
                category_data = []
                for cat, count, amount in categories:
                    category_data.append({
                        'Category': cat or 'Unknown',
                        'Count': count,
                        'Total Amount': f"{amount:,.2f} DKK" if amount else "0 DKK"
                    })

                df = pd.DataFrame(category_data)
                df = df.sort_values('Count', ascending=False)

                # Display summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_categories = len(categories)
                    st.metric("Total Categories", total_categories)

                with col2:
                    vendor_payments = next((count for cat, count, _ in categories if cat == 'vendor_payment'), 0)
                    total_transactions = sum(count for _, count, _ in categories)
                    vendor_percentage = (vendor_payments / total_transactions * 100) if total_transactions > 0 else 0
                    st.metric("Vendor Payments", f"{vendor_payments} ({vendor_percentage:.1f}%)")

                with col3:
                    other_payments = total_transactions - vendor_payments
                    st.metric("Other Transaction Types", other_payments)

                # Display category breakdown table
                st.markdown("#### Category Breakdown")
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Show all non-vendor transactions
                st.markdown("#### All Non-Vendor Transactions")

                # Add category filter
                all_non_vendor_categories = [cat for cat, _, _ in categories if cat != 'vendor_payment']
                if all_non_vendor_categories:
                    selected_categories = st.multiselect(
                        "Filter by categories:",
                        options=['All'] + all_non_vendor_categories,
                        default=['All']
                    )

                    # Build filter condition
                    if 'All' in selected_categories or not selected_categories:
                        category_filter = Transaction.category != 'vendor_payment'
                    else:
                        category_filter = Transaction.category.in_(selected_categories)

                    # Get all non-vendor transactions with optional filtering
                    non_vendor_transactions = session.query(Transaction).filter(
                        category_filter
                    ).order_by(Transaction.date.desc()).all()

                    if non_vendor_transactions:
                        all_data = []
                        for t in non_vendor_transactions:
                            all_data.append({
                                'Date': t.date.strftime('%Y-%m-%d') if t.date else 'N/A',
                                'Amount': f"{t.amount:,.2f} DKK",
                                'Category': t.category or 'Unknown',
                                'Confidence': f"{t.category_confidence:.2f}" if t.category_confidence else 'N/A',
                                'Description': t.text,
                                'Vendor': getattr(t.vendor, 'name', 'N/A') if t.vendor else 'N/A'
                            })

                        all_df = pd.DataFrame(all_data)

                        # Show count info
                        st.info(f"Showing {len(all_df)} non-vendor transactions")

                        # Display the full table
                        st.dataframe(
                            all_df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Amount": st.column_config.TextColumn(width="small"),
                                "Category": st.column_config.TextColumn(width="medium"),
                                "Confidence": st.column_config.TextColumn(width="small"),
                                "Description": st.column_config.TextColumn(width="large"),
                            }
                        )

                        # Export option
                        if st.button("📥 Export Non-Vendor Transactions to CSV"):
                            csv = all_df.to_csv(index=False)
                            st.download_button(
                                label="Download CSV",
                                data=csv,
                                file_name="non_vendor_transactions.csv",
                                mime="text/csv"
                            )
                    else:
                        st.info("No non-vendor transactions found for selected categories")
                else:
                    st.info("No non-vendor transactions found")
            else:
                st.info("No transaction categories found in database")

            session.close()

        except Exception as e:
            st.error(f"Error loading transaction categories: {e}")
            import traceback
            st.code(traceback.format_exc())

    def _render_database_operations(self):
        """Render database operations section."""
        tab1, tab2, tab3 = st.tabs(["Delete Data", "Reset Database", "Export Data"])

        with tab1:
            self._render_delete_data_tab()

        with tab2:
            self._render_reset_database_tab()

        with tab3:
            self._render_export_data_tab()

    def _render_delete_data_tab(self):
        """Render delete data tab."""
        st.markdown("#### Delete Specific Data")
        st.warning("Deletion is permanent and cannot be undone!")

        col1, col2 = st.columns(2)

        with col1:
            self._render_delete_transactions_section()

        with col2:
            self._render_delete_vendors_section()

    def _render_delete_transactions_section(self):
        """Render delete transactions section."""
        st.markdown("##### Delete Transactions")

        # Get transactions for selection
        transactions = (
            self.processor.db_session.query(Transaction)
            .order_by(Transaction.date.desc())
            .limit(100)
            .all()
        )

        if transactions:
            # Create selection interface
            trans_data = []
            for t in transactions:
                trans_data.append(
                    {
                        "ID": t.id,
                        "Date": t.date.strftime("%Y-%m-%d") if t.date else "",
                        "Amount": f"{t.amount:.2f}",
                        "Text": t.text[:50] + "..." if len(t.text) > 50 else t.text,
                        "Category": t.category,
                    }
                )

            trans_df = pd.DataFrame(trans_data)

            # Multi-select for transactions
            selected_trans_ids = st.multiselect(
                "Select transactions to delete:",
                options=trans_df["ID"].tolist(),
                format_func=lambda x: f"ID {x}: {trans_df[trans_df['ID'] == x]['Text'].values[0][:30]}...",
            )

            if selected_trans_ids:
                st.info(f"Selected {len(selected_trans_ids)} transaction(s) for deletion")

                if st.button(
                    "Delete Selected Transactions",
                    type="secondary",
                    use_container_width=True,
                ):
                    self._handle_delete_transactions(selected_trans_ids)
        else:
            st.info("No transactions found")

    def _render_delete_vendors_section(self):
        """Render delete vendors section."""
        st.markdown("##### Delete Vendors")

        # Get vendors for selection
        vendors = self.processor.get_all_vendors()

        if vendors:
            vendor_data = []
            for v in vendors:
                vendor_data.append(
                    {
                        "ID": v["id"],
                        "Name": v["name"],
                        "Domain": v["domain"] or "N/A",
                        "Country": v["country"] or "N/A",
                    }
                )

            vendor_df = pd.DataFrame(vendor_data)

            # Multi-select for vendors
            selected_vendor_ids = st.multiselect(
                "Select vendors to delete:",
                options=vendor_df["ID"].tolist(),
                format_func=lambda x: vendor_df[vendor_df["ID"] == x]["Name"].values[0],
            )

            if selected_vendor_ids:
                st.info(f"Selected {len(selected_vendor_ids)} vendor(s) for deletion")

                if st.button(
                    "Delete Selected Vendors",
                    type="secondary",
                    use_container_width=True,
                ):
                    self._handle_delete_vendors(selected_vendor_ids)
        else:
            st.info("No vendors found")

    def _render_reset_database_tab(self):
        """Render reset database tab."""
        st.markdown("#### Complete Database Reset")
        st.error("**DANGER ZONE**: This will delete ALL data in the database!")

        st.markdown("""
        This action will:
        - Delete all transactions
        - Delete all vendors
        - Delete all enrichment data
        - Cannot be undone!
        """)

        # Two-step confirmation
        col1, col2, col3 = st.columns([2, 1, 2])

        with col2:
            confirm_text = st.text_input(
                "Type 'DELETE ALL' to confirm:",
                placeholder="DELETE ALL",
                label_visibility="collapsed",
            )

        if confirm_text == "DELETE ALL":
            st.error("Final warning: This will permanently delete ALL data!")

            if st.button("RESET DATABASE", type="primary", use_container_width=True):
                self._handle_database_reset()

    def _render_export_data_tab(self):
        """Render export data tab."""
        st.markdown("#### Export Database")
        st.markdown("Export your data to CSV files for backup or analysis.")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("##### Export Transactions")
            # Generate CSV data
            transactions_csv = self._generate_transactions_csv()
            if transactions_csv:
                st.download_button(
                    label="Download Transactions CSV",
                    data=transactions_csv,
                    file_name=f"transactions_export_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("No transactions available for export")

        with col2:
            st.markdown("##### Export Vendors")
            # Generate CSV data
            vendors_csv = self._generate_vendors_csv()
            if vendors_csv:
                st.download_button(
                    label="Download Vendors CSV",
                    data=vendors_csv,
                    file_name=f"vendors_export_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("No vendors available for export")

    def _handle_delete_transactions(self, transaction_ids: List[int]):
        """Handle transaction deletion."""
        success, message = self.processor.delete_transactions(transaction_ids)
        if success:
            st.success(message)
            time.sleep(1)
            st.rerun()
        else:
            st.error(message)

    def _handle_delete_vendors(self, vendor_ids: List[int]):
        """Handle vendor deletion."""
        success, message = self.processor.delete_vendors(vendor_ids)
        if success:
            st.success(message)
            time.sleep(1)
            st.rerun()
        else:
            st.error(message)

    def _handle_database_reset(self):
        """Handle complete database reset."""
        try:
            self.processor.reset_database()
            st.success("Database reset successfully!")
            st.balloons()
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.error(f"Error resetting database: {str(e)}")

    def _generate_transactions_csv(self):
        """Generate CSV data for transactions export."""
        try:
            # Get all transactions data with vendor relationship
            transactions = self.processor.db_session.query(Transaction).all()

            if not transactions:
                return None

            # Convert to DataFrame
            trans_data = []
            for t in transactions:
                trans_data.append({
                    'id': t.id,
                    'date': t.date.strftime("%Y-%m-%d") if t.date else None,
                    'posting_date': t.posting_date.strftime("%Y-%m-%d") if t.posting_date else None,
                    'amount': t.amount,
                    'currency': t.currency,
                    'text': t.text,
                    'message': t.message,
                    'transaction_type': t.transaction_type,
                    'sender': t.sender,
                    'receiver': t.receiver,
                    'category': t.category,
                    'category_confidence': t.category_confidence,
                    'vendor_id': t.vendor_id,
                    'vendor_name': t.vendor.name if t.vendor else None,
                    'vendor_confidence': t.vendor_confidence,
                    'balance': t.balance,
                    'created_at': t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else None,
                })

            df = pd.DataFrame(trans_data)
            return df.to_csv(index=False)

        except Exception as e:
            st.error(f"Error preparing transactions export: {str(e)}")
            return None

    def _generate_vendors_csv(self):
        """Generate CSV data for vendors export."""
        try:
            # Get all vendors data
            vendors = self.processor.get_all_vendors()

            if not vendors:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(vendors)
            return df.to_csv(index=False)

        except Exception as e:
            st.error(f"Error preparing vendors export: {str(e)}")
            return None


def render_database_page(processor):
    """Entry point for rendering the Database page."""
    page = DatabasePage(processor)
    page.render()