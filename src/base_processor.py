# Base processor class with common functionality to eliminate code duplication
from typing import Callable, Dict, List, Optional, Tuple

from src.models import Transaction, Vendor, get_db_session
from src.utils import CSVUtils, DatabaseService, DuplicateDetector
from src.vendor_matcher import VendorMatcher


class BaseTransactionProcessor:
    """Base class containing common transaction processing functionality."""

    def __init__(self, openai_api_key: str = None):
        self.db_session = get_db_session()
        self.vendor_matcher = VendorMatcher(self.db_session)
        self.db_service = DatabaseService(self.db_session)
        self.duplicate_detector = DuplicateDetector()

    def read_csv_file(self, csv_path: str) -> List[Dict]:
        """Read CSV file and extract all transaction data."""
        print(f"📄 Reading CSV file: {csv_path}")

        # Use shared CSV reading utility
        df = CSVUtils.read_csv_with_encoding_detection(csv_path)

        # Extract all transactions using shared utility
        all_transactions = [
            CSVUtils.create_transaction_data(row) for _, row in df.iterrows()
        ]

        print(f"✓ Extracted {len(all_transactions)} transactions")
        return all_transactions

    def find_duplicate_transactions(
        self, new_transactions: List[Dict], days_lookback: int = 7
    ) -> List[Tuple[Dict, Transaction, float]]:
        """Find potential duplicate transactions using fuzzy matching."""
        return self.duplicate_detector.find_duplicate_transactions(
            new_transactions, self.db_session, days_lookback
        )

    def process_vendor_for_transaction(
        self, vendor_name: str, category: str, vendor_cache: Dict = None
    ) -> Tuple[Optional[Vendor], float, str]:
        """Process vendor identification and creation with caching."""
        if not vendor_name or category != "vendor_payment":
            return None, 0.0, "none"

        vendor_cache = vendor_cache or {}
        vendor_key = vendor_name.lower()

        # Check cache first
        if vendor_key in vendor_cache:
            cached_vendor, cached_confidence = vendor_cache[vendor_key]
            return cached_vendor, cached_confidence, "cache"

        # Check for existing vendor
        existing = self.vendor_matcher.find_existing_vendor(vendor_name)
        if existing:
            vendor_cache[vendor_key] = (existing[0], existing[1])
            return existing[0], existing[1], "database"

        # Create new vendor - this will be implemented by subclasses
        # as they may use different enrichment strategies
        return None, 0.0, "none"

    def create_transaction_record(
        self,
        transaction_data: Dict,
        category: str,
        confidence: float,
        vendor: Optional[Vendor] = None,
        vendor_confidence: float = 0.0,
    ) -> Transaction:
        """Create a transaction record with the given data."""
        return Transaction(
            **{k: v for k, v in transaction_data.items() if k != "raw_line"},
            category=category,
            category_confidence=confidence,
            vendor_id=vendor.id if vendor else None,
            vendor_confidence=vendor_confidence,
            raw_line=transaction_data["raw_line"],
        )

    def save_transactions(self, transactions: List[Transaction]) -> None:
        """Save multiple transactions to database in a single commit."""
        for transaction in transactions:
            self.db_session.add(transaction)

        self.db_session.commit()
        print(f"💾 Saved {len(transactions)} transactions to database")

    def format_transaction_result(
        self,
        transaction_data: Dict,
        category: str,
        confidence: float,
        vendor: Optional[Vendor] = None,
        vendor_confidence: float = 0.0,
        reasoning: str = "Processed",
    ) -> Dict:
        """Format transaction data for result display."""
        return {
            "transaction_id": 0,  # Will be updated after database save
            "date": transaction_data["date"].strftime("%Y-%m-%d"),
            "text": transaction_data["text"],
            "amount": transaction_data["amount"],
            "category": category,
            "category_confidence": confidence,
            "vendor_name": vendor.name if vendor else None,
            "vendor_confidence": vendor_confidence,
            "reasoning": reasoning,
        }

    def process_transactions_batch(
        self,
        transactions: List[Dict],
        batch_results: List,
        vendor_cache: Dict = None,
        progress_callback: Optional[Callable] = None,
        batch_id: str = None,
    ) -> List[Dict]:
        """Process a batch of transactions with AI results and vendor handling."""
        results = []
        vendor_cache = vendor_cache or {}

        for i, (transaction_data, batch_result) in enumerate(
            zip(transactions, batch_results)
        ):
            # Create transaction record
            transaction = self.create_transaction_record(
                transaction_data, batch_result.category, batch_result.confidence
            )

            # Set batch ID for tracking latest processing
            if batch_id:
                transaction.batch_id = batch_id

            # Handle vendor processing
            vendor, vendor_confidence, match_source = self.process_vendor_for_transaction(
                batch_result.vendor_name, batch_result.category, vendor_cache
            )

            if vendor:
                transaction.vendor_id = vendor.id
                transaction.vendor_confidence = (
                    vendor_confidence * batch_result.vendor_confidence
                )
                transaction.vendor_match_source = match_source
            else:
                transaction.vendor_match_source = match_source

            # Add to session
            self.db_session.add(transaction)

            # Format result
            result = self.format_transaction_result(
                transaction_data,
                batch_result.category,
                batch_result.confidence,
                vendor,
                vendor_confidence,
                "Batch processed",
            )
            results.append(result)

            # Update progress if callback provided
            if progress_callback and i % 5 == 0:
                progress_callback(
                    i + 1,
                    len(transactions),
                    f"Processing transaction {i + 1}/{len(transactions)}",
                )

        return results

    # Database service methods (delegated to avoid duplication)
    def get_vendor_payments(self) -> List[Dict]:
        """Get all vendor payments from database."""
        return self.db_service.get_vendor_payments()

    def get_all_vendors(self) -> List[Dict]:
        """Get all vendors from database."""
        return self.db_service.get_all_vendors()

    def get_database_stats(self) -> Dict:
        """Get database statistics."""
        return self.db_service.get_database_stats()

    def update_vendor(self, vendor_id: int, updated_data: Dict) -> bool:
        """Update vendor information with user corrections."""
        return self.db_service.update_vendor(vendor_id, updated_data)

    def reset_database(self):
        """Reset the entire database - delete all transactions and vendors."""
        return self.db_service.reset_database()

    def delete_transactions(self, transaction_ids: List[int]):
        """Delete specific transactions by their IDs."""
        return self.db_service.delete_transactions(transaction_ids)

    def delete_vendors(self, vendor_ids: List[int]):
        """Delete specific vendors by their IDs."""
        return self.db_service.delete_vendors(vendor_ids)

    def close(self):
        """Close database session."""
        self.db_service.close()
