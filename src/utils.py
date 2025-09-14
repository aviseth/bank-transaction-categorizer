# Shared utility functions to eliminate code duplication
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

import pandas as pd

from src.models import Transaction, Vendor, get_db_session


class CSVUtils:
    """Utility functions for CSV parsing and data extraction."""

    @staticmethod
    def parse_csv_date(date_str: str, time_str: str = None) -> datetime:
        """Parse CSV date/time into datetime object with fallback to current time."""
        try:
            format_str = "%Y-%m-%d %H:%M:%S" if time_str else "%Y-%m-%d"
            date_input = f"{date_str} {time_str}" if time_str else date_str
            return datetime.strptime(date_input, format_str)
        except (ValueError, TypeError):
            return datetime.now()

    @staticmethod
    def parse_amount(amount_str: str) -> float:
        """Parse Danish number format (1.234,56) to float with robust error handling.

        Expected format: Danish/European number format where:
        - Thousands separator: . (dot)
        - Decimal separator: , (comma)
        - Examples: "1.234,56" -> 1234.56, "123,45" -> 123.45, "1000" -> 1000.0

        Args:
            amount_str: String representation of amount in Danish format

        Returns:
            float: Parsed amount or 0.0 if parsing fails
        """
        if not amount_str or pd.isna(amount_str):
            return 0.0

        try:
            # Convert to string and strip whitespace
            clean_str = str(amount_str).strip()

            # Handle empty or invalid strings
            if not clean_str or clean_str.lower() in ['nan', 'null', 'none']:
                return 0.0

            # Remove thousands separators (dots) and replace decimal comma with dot
            # This handles: "1.234,56" -> "1234.56", "123,45" -> "123.45", "1000" -> "1000"
            if ',' in clean_str:
                # Has decimal separator
                parts = clean_str.split(',')
                if len(parts) != 2:
                    raise ValueError(f"Invalid decimal format: {clean_str}")
                integer_part = parts[0].replace('.', '')  # Remove thousands separators
                decimal_part = parts[1]
                clean_str = f"{integer_part}.{decimal_part}"
            else:
                # No decimal separator, just remove thousands separators
                clean_str = clean_str.replace('.', '')

            return float(clean_str)

        except (ValueError, TypeError, AttributeError) as e:
            print(f"Warning: Failed to parse amount '{amount_str}': {e}")
            return 0.0

    @staticmethod
    def read_csv_with_encoding_detection(csv_path: str) -> pd.DataFrame:
        """Read CSV file with automatic encoding detection for Danish characters."""
        encodings = ["utf-8", "iso-8859-1", "cp1252", "latin-1"]

        for encoding in encodings:
            try:
                df = pd.read_csv(csv_path, sep=";", encoding=encoding)
                print(f"✓ Read CSV with {encoding} encoding")
                return df
            except UnicodeDecodeError:
                continue

        raise ValueError("Could not read CSV file with any supported encoding")

    @staticmethod
    def create_transaction_data(row) -> Dict:
        """Extract and parse transaction data from CSV row."""
        return {
            "date": CSVUtils.parse_csv_date(str(row.get("Date", ""))),
            "posting_date": CSVUtils.parse_csv_date(
                str(row.get("Date of posting", "")), str(row.get("Time of posting", ""))
            ),
            "text": str(row.get("Text", "")),
            "message": str(row.get("Message", "")),
            "transaction_type": str(row.get("Transaction type", "")),
            "card_info": str(row.get("Card info", "")),
            "amount": CSVUtils.parse_amount(row.get("Amount", "0")),
            "currency": str(row.get("Currency", "")),
            "sender": str(row.get("Sender", "")),
            "receiver": str(row.get("Receiver", "")),
            "note": str(row.get("Note", "")),
            "balance": CSVUtils.parse_amount(row.get("Balance", "0")),
            "raw_line": str(row.to_dict()),
        }


class DuplicateDetector:
    """Utility functions for detecting duplicate transactions."""

    @staticmethod
    def find_duplicate_transactions(
        new_transactions: List[Dict], db_session, days_lookback: int = 7
    ) -> List[Tuple[Dict, Transaction, float]]:
        """Find potential duplicate transactions using fuzzy matching.

        Returns list of (new_transaction, existing_transaction, similarity_score) tuples.
        """
        duplicates = []

        # Get existing transactions from the specified lookback period
        cutoff_date = datetime.now() - timedelta(days=days_lookback)
        existing_transactions = (
            db_session.query(Transaction).filter(Transaction.date >= cutoff_date).all()
        )

        for new_trans in new_transactions:
            for existing in existing_transactions:
                # Check date proximity (within 1 day)
                date_diff = (
                    abs((new_trans["date"] - existing.date).days)
                    if existing.date
                    else 999
                )
                if date_diff > 1:
                    continue

                # Check amount match (exact)
                if abs(new_trans["amount"] - existing.amount) > 0.01:
                    continue

                # Check text similarity (fuzzy match)
                text_similarity = SequenceMatcher(
                    None, new_trans["text"].lower(), (existing.text or "").lower()
                ).ratio()

                # If text is at least 85% similar, consider it a potential duplicate
                if text_similarity >= 0.85:
                    # Calculate overall similarity score
                    similarity_score = (
                        (1.0 if date_diff == 0 else 0.8) * 0.3  # Date weight: 30%
                        + 1.0 * 0.3  # Amount weight: 30% (already matched)
                        + text_similarity * 0.4  # Text weight: 40%
                    )
                    duplicates.append((new_trans, existing, similarity_score))
                    break  # Only match with first duplicate found

        return duplicates


class DatabaseService:
    """Shared database operations to eliminate duplicate query methods."""

    def __init__(self, db_session=None):
        self.db_session = db_session or get_db_session()

    def _format_transaction_result(self, transaction: Transaction) -> Dict:
        """Helper method to format transaction data."""
        return {
            "id": transaction.id,
            "date": transaction.date.strftime("%Y-%m-%d") if transaction.date else "",
            "text": transaction.text,
            "amount": transaction.amount,
            "vendor_name": transaction.vendor.name if transaction.vendor else "Unknown",
            "vendor_confidence": transaction.vendor_confidence or 0.0,
            "category_confidence": transaction.category_confidence or 0.0,
        }

    def _format_vendor_result(self, vendor: Vendor) -> Dict:
        """Helper method to format vendor data."""
        return {
            "id": vendor.id,
            "name": vendor.name,
            "nicknames": vendor.nicknames,
            "domain": vendor.domain,
            "description": vendor.default_description,
            "country": vendor.invoicing_country,
            "currency": vendor.default_currency,
            "product_type": vendor.default_product_type,
            "transaction_count": len(vendor.transactions),
        }

    def _format_vendor_result_optimized(self, vendor: Vendor, transaction_count: int) -> Dict:
        """Helper method to format vendor data with pre-computed transaction count."""
        return {
            "id": vendor.id,
            "name": vendor.name,
            "nicknames": vendor.nicknames,
            "domain": vendor.domain,
            "description": vendor.default_description,
            "country": vendor.invoicing_country,
            "currency": vendor.default_currency,
            "product_type": vendor.default_product_type,
            "transaction_count": transaction_count,
        }

    def get_vendor_payments(self) -> List[Dict]:
        """Get all vendor payments from database with eager loading."""
        from sqlalchemy.orm import joinedload

        vendor_payments = (
            self.db_session.query(Transaction)
            .options(joinedload(Transaction.vendor))
            .filter(Transaction.category == "vendor_payment")
            .all()
        )
        return [self._format_transaction_result(t) for t in vendor_payments]

    def get_all_vendors(self) -> List[Dict]:
        """Get all vendors from database with transaction counts."""
        from sqlalchemy import func

        vendors_with_counts = (
            self.db_session.query(Vendor, func.count(Transaction.id).label('transaction_count'))
            .outerjoin(Transaction)
            .group_by(Vendor.id)
            .all()
        )

        result = []
        for vendor, transaction_count in vendors_with_counts:
            vendor_dict = self._format_vendor_result_optimized(vendor, transaction_count)
            result.append(vendor_dict)

        return result

    def get_database_stats(self) -> Dict:
        """Get database statistics with optimized queries."""
        from sqlalchemy import func

        # Get all statistics in fewer queries
        stats_query = (
            self.db_session.query(
                func.count(Transaction.id).label('total_transactions'),
                func.count(func.distinct(Transaction.vendor_id)).label('unique_vendors_with_transactions'),
                func.count(Transaction.id).filter(Transaction.category == 'vendor_payment').label('vendor_payments'),
                func.min(Transaction.date).label('earliest_date'),
                func.max(Transaction.date).label('latest_date')
            )
            .first()
        )

        vendor_count = self.db_session.query(Vendor).count()

        return {
            "total_transactions": stats_query.total_transactions or 0,
            "total_vendors": vendor_count,
            "vendor_payments": stats_query.vendor_payments or 0,
            "date_range": {
                "earliest": stats_query.earliest_date if stats_query.earliest_date else None,
                "latest": stats_query.latest_date if stats_query.latest_date else None,
            },
        }

    def update_vendor(self, vendor_id: int, updated_data: Dict) -> bool:
        """Update vendor information with user corrections."""
        try:
            vendor = (
                self.db_session.query(Vendor).filter(Vendor.id == vendor_id).first()
            )
            if not vendor:
                return False

            # Update vendor properties
            if "name" in updated_data:
                vendor.name = updated_data["name"]
            if "nicknames" in updated_data:
                # Ensure nicknames is stored as a comma-separated string for SQLite
                if isinstance(updated_data["nicknames"], list):
                    vendor.nicknames = ",".join(
                        [
                            nick.strip()
                            for nick in updated_data["nicknames"]
                            if nick and nick.strip()
                        ]
                    )
                elif isinstance(updated_data["nicknames"], str):
                    # Clean up the string and ensure it's properly formatted
                    vendor.nicknames = ",".join(
                        [
                            nick.strip()
                            for nick in updated_data["nicknames"].split(",")
                            if nick.strip()
                        ]
                    )
                else:
                    vendor.nicknames = ""
            if "domain" in updated_data:
                vendor.domain = updated_data["domain"]
            if "default_description" in updated_data:
                vendor.default_description = updated_data["default_description"]
            if "invoicing_country" in updated_data:
                vendor.invoicing_country = updated_data["invoicing_country"]
            if "default_currency" in updated_data:
                vendor.default_currency = updated_data["default_currency"]
            if "default_product_type" in updated_data:
                # Ensure product_type is valid
                if updated_data["default_product_type"] in ["services", "goods"]:
                    vendor.default_product_type = updated_data["default_product_type"]

            self.db_session.commit()
            return True
        except Exception as e:
            print(f"Error updating vendor: {e}")
            self.db_session.rollback()
            return False

    def reset_database(self):
        """Reset the entire database - delete all transactions and vendors."""
        try:
            # Delete all transactions first (due to foreign key constraints)
            self.db_session.query(Transaction).delete()
            # Delete all vendors
            self.db_session.query(Vendor).delete()
            self.db_session.commit()
            return True, "Database reset successfully"
        except Exception as e:
            self.db_session.rollback()
            return False, f"Error resetting database: {str(e)}"

    def delete_transactions(self, transaction_ids: List[int]):
        """Delete specific transactions by their IDs."""
        try:
            deleted_count = (
                self.db_session.query(Transaction)
                .filter(Transaction.id.in_(transaction_ids))
                .delete(synchronize_session=False)
            )
            self.db_session.commit()
            return True, f"Deleted {deleted_count} transactions"
        except Exception as e:
            self.db_session.rollback()
            return False, f"Error deleting transactions: {str(e)}"

    def delete_vendors(self, vendor_ids: List[int]):
        """Delete specific vendors by their IDs."""
        try:
            # First, unlink transactions from these vendors
            self.db_session.query(Transaction).filter(
                Transaction.vendor_id.in_(vendor_ids)
            ).update({"vendor_id": None}, synchronize_session=False)

            # Then delete the vendors
            deleted_count = (
                self.db_session.query(Vendor)
                .filter(Vendor.id.in_(vendor_ids))
                .delete(synchronize_session=False)
            )

            self.db_session.commit()
            return True, f"Deleted {deleted_count} vendors"
        except Exception as e:
            self.db_session.rollback()
            return False, f"Error deleting vendors: {str(e)}"

    def close(self):
        """Close database session."""
        self.db_session.close()
