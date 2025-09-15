# Compact processor with maximum code reduction
from typing import Callable, Dict, List, Optional, Tuple

from src.base_processor import BaseTransactionProcessor
from src.streamlined_categorizer import StreamlinedCategorizer


class CompactTransactionProcessor(BaseTransactionProcessor):
    """Compact processor with minimal code duplication."""

    def __init__(self, openai_api_key: str = None, verify_domains: bool = True):
        super().__init__(openai_api_key)
        self.categorizer = StreamlinedCategorizer(openai_api_key, verify_domains)

    def process_vendor_for_transaction(
        self, vendor_name: str, category: str, vendor_cache: Dict = None, transaction_data: Dict = None
    ) -> Tuple[Optional[object], float, str]:
        """Process vendor with caching."""
        if not vendor_name or category != "vendor_payment":
            return None, 0.0, "none"

        vendor_cache = vendor_cache or {}
        vendor_key = vendor_name.lower()

        if vendor_key in vendor_cache:
            cached_vendor, cached_confidence = vendor_cache[vendor_key]
            return cached_vendor, cached_confidence, "cache"

        existing = self.vendor_matcher.find_existing_vendor(vendor_name)
        if existing:
            # Recalculate confidence using dynamic scoring if transaction data available
            confidence = existing[1]
            if transaction_data:
                confidence = self.confidence_calc.calculate_vendor_confidence(
                    vendor_name, transaction_data, existing[1]
                )
            vendor_cache[vendor_key] = (existing[0], confidence)
            return existing[0], confidence, "database"

        vendor_info = self.categorizer.enrich_vendor(vendor_name)
        vendor = self.vendor_matcher.create_or_get_vendor(
            vendor_name,
            {
                "name": vendor_info.name,
                "nicknames": vendor_info.nicknames,
                "domain": vendor_info.domain,
                "default_description": vendor_info.default_description,
                "invoicing_country": vendor_info.invoicing_country,
                "default_currency": vendor_info.default_currency,
                "default_product_type": vendor_info.default_product_type,
            },
        )
        vendor_cache[vendor_key] = (vendor, vendor_info.confidence)
        return vendor, vendor_info.confidence, "llm"

    def process_csv_with_duplicate_check(
        self,
        csv_path: str,
        excluded_indices: List[int] = None,
        batch_size: int = 20,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        """Process CSV with duplicate detection."""
        all_transactions = self.read_csv_file(csv_path)
        duplicates = self.find_duplicate_transactions(all_transactions)

        excluded_indices = excluded_indices or []
        transactions_to_process = []
        duplicate_info = []

        def _transactions_match(trans1: Dict, trans2: Dict) -> bool:
            """Compare transactions with robust handling of datetime and float precision."""
            # Compare essential fields that identify a transaction
            date1 = trans1.get("date")
            date2 = trans2.get("date")
            if not date1 or not date2:
                return False
            return (
                abs(trans1.get("amount", 0) - trans2.get("amount", 0)) < 0.01  # Float precision
                and trans1.get("text", "") == trans2.get("text", "")  # Text match
                and abs((date1 - date2).total_seconds()) < 86400  # Same day
            )
        for i, trans in enumerate(all_transactions):
            is_duplicate = any(
                _transactions_match(dup_trans, trans) and i not in excluded_indices
                for dup_trans, _, _ in duplicates
            )

            if is_duplicate:
                dup_trans, existing, score = next(
                    (d for d in duplicates if _transactions_match(d[0], trans)), (None, None, 0)
                )
                duplicate_info.append(
                    {
                        "index": i,
                        "date": trans["date"].strftime("%Y-%m-%d"),
                        "amount": trans["amount"],
                        "text": trans["text"],
                        "existing_id": existing.id,
                        "existing_date": existing.date.strftime("%Y-%m-%d")
                        if existing.date
                        else "",
                        "existing_text": existing.text,
                        "similarity": f"{score * 100:.1f}%",
                    }
                )
            else:
                transactions_to_process.append(trans)

        if duplicate_info:
            print(f"⚠️ Found {len(duplicate_info)} potential duplicates")
            return [], duplicate_info

        return self._process_transactions(
            transactions_to_process, batch_size, progress_callback
        ), []

    def _process_transactions(
        self,
        transactions: List[Dict],
        batch_size: int = 20,
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """Process transactions with minimal code."""
        if not transactions:
            return []

        batch_results = self.categorizer.categorize_batch_ultra_fast(
            transactions, batch_size=batch_size, progress_callback=progress_callback
        )

        results = []
        vendor_cache = {}

        for i, (transaction_data, batch_result) in enumerate(
            zip(transactions, batch_results)
        ):
            transaction = self.create_transaction_record(
                transaction_data, batch_result.category, batch_result.confidence
            )

            vendor, vendor_confidence = self.process_vendor_for_transaction(
                batch_result.vendor_name, batch_result.category, vendor_cache, transaction_data
            )

            if vendor:
                transaction.vendor_id = vendor.id
                transaction.vendor_confidence = (
                    vendor_confidence * batch_result.vendor_confidence
                )

            self.db_session.add(transaction)
            results.append(
                self.format_transaction_result(
                    transaction_data,
                    batch_result.category,
                    batch_result.confidence,
                    vendor,
                    vendor_confidence,
                    "Fast batch processed",
                )
            )

        self.db_session.commit()
        print(
            f"⚡ Processed {len(results)} transactions with {len(vendor_cache)} vendors!"
        )
        return results

    def process_csv_ultra_fast(
        self,
        csv_path: str,
        batch_size: int = 20,
        progress_callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """Ultra-fast processing with minimal code."""
        all_transactions = self.read_csv_file(csv_path)
        batch_results = self.categorizer.categorize_batch_ultra_fast(
            all_transactions, batch_size=batch_size, progress_callback=progress_callback
        )

        results = []
        vendor_cache = {}

        for i, (transaction_data, batch_result) in enumerate(
            zip(all_transactions, batch_results)
        ):
            transaction = self.create_transaction_record(
                transaction_data, batch_result.category, batch_result.confidence
            )

            vendor, vendor_confidence = self.process_vendor_for_transaction(
                batch_result.vendor_name, batch_result.category, vendor_cache, transaction_data
            )

            if vendor:
                transaction.vendor_id = vendor.id
                transaction.vendor_confidence = (
                    vendor_confidence * batch_result.vendor_confidence
                )

            self.db_session.add(transaction)
            results.append(
                self.format_transaction_result(
                    transaction_data,
                    batch_result.category,
                    batch_result.confidence,
                    vendor,
                    vendor_confidence,
                    "Fast batch processed",
                )
            )

        self.db_session.commit()
        print(
            f"⚡ ULTRA-FAST: Processed {len(results)} transactions with {len(vendor_cache)} vendors!"
        )
        return results
