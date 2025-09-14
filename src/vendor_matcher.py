from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from src.models import Vendor
from difflib import SequenceMatcher
import re


class VendorMatcher:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def find_existing_vendor(self, vendor_name: str) -> Optional[Tuple[Vendor, float]]:
        """Find existing vendor using optimized fuzzy matching."""
        if not vendor_name:
            return None

        normalized_input = self._normalize_name(vendor_name)
        if not normalized_input:
            return None

        # First try exact matches (fastest)
        exact_vendor = self._find_exact_match(vendor_name, normalized_input)
        if exact_vendor:
            return exact_vendor, 1.0

        # Then try fuzzy matching with limited candidates
        return self._find_fuzzy_match(normalized_input)

    def _find_exact_match(self, original_name: str, normalized_name: str) -> Optional[Vendor]:
        """Find exact matches using database queries."""
        # Try exact name match (case-insensitive)
        exact_match = self.db_session.query(Vendor).filter(
            Vendor.name.ilike(original_name)
        ).first()
        if exact_match:
            return exact_match

        # Try normalized name match
        vendors = self.db_session.query(Vendor).all()
        for vendor in vendors:
            if self._normalize_name(vendor.name) == normalized_name:
                return vendor

        return None

    def _find_fuzzy_match(self, normalized_input: str) -> Optional[Tuple[Vendor, float]]:
        """Find fuzzy matches with optimized scoring."""
        vendors = self.db_session.query(Vendor).all()
        best_match, best_score = None, 0.0
        threshold = 0.8  # Minimum similarity threshold

        for vendor in vendors:
            # Check canonical name
            score = self._calculate_similarity(normalized_input, self._normalize_name(vendor.name))
            if score > best_score and score >= threshold:
                best_match, best_score = vendor, score

            # Check nicknames if they exist
            if vendor.nicknames and score < 0.95:  # Skip if we already have a very good match
                nickname_score = self._check_nicknames(normalized_input, vendor.nicknames)
                if nickname_score > best_score and nickname_score >= threshold:
                    best_match, best_score = vendor, nickname_score

            # Check domain if it exists and we don't have a perfect match
            if vendor.domain and best_score < 1.0:
                domain_score = self._check_domain(normalized_input, vendor.domain)
                if domain_score > best_score and domain_score >= threshold:
                    best_match, best_score = vendor, domain_score

        return (best_match, best_score) if best_match else None

    def _check_nicknames(self, normalized_input: str, nicknames_str: str) -> float:
        """Check similarity against vendor nicknames."""
        best_score = 0.0
        for nickname in nicknames_str.split(','):
            nickname = nickname.strip()
            if nickname:
                score = self._calculate_similarity(normalized_input, self._normalize_name(nickname))
                best_score = max(best_score, score)
        return best_score

    def _check_domain(self, normalized_input: str, domain: str) -> float:
        """Check similarity against vendor domain."""
        # Extract domain name by removing all TLDs and subdomains
        domain_parts = domain.lower().split('.')
        if len(domain_parts) > 1:
            # Take the main domain part (second-to-last for most cases)
            # e.g., "example.com" -> "example", "sub.example.co.uk" -> "example"
            domain_name = domain_parts[-2] if len(domain_parts) >= 2 else domain_parts[0]
        else:
            domain_name = domain.lower()

        return self._calculate_similarity(normalized_input, domain_name)

    def create_or_get_vendor(self, vendor_name: str, vendor_info: dict) -> Vendor:
        """Return existing vendor or create new one with optimized lookup."""
        # Check if vendor already exists using optimized matching
        existing_match = self.find_existing_vendor(vendor_name)
        if existing_match:
            return existing_match[0]

        # Check if vendor info contains a different name that might match
        enriched_name = vendor_info.get('name', vendor_name)
        if enriched_name != vendor_name:
            enriched_match = self.find_existing_vendor(enriched_name)
            if enriched_match:
                return enriched_match[0]

        # Create new vendor with simplified error handling
        return self._create_new_vendor(vendor_name, vendor_info)

    def _create_new_vendor(self, vendor_name: str, vendor_info: dict) -> Vendor:
        """Create a new vendor with race condition handling."""
        vendor = Vendor(
            name=vendor_info.get('name', vendor_name),
            nicknames=self._format_nicknames(vendor_info.get('nicknames', [])),
            domain=vendor_info.get('domain'),
            default_description=vendor_info.get('default_description'),
            invoicing_country=vendor_info.get('invoicing_country'),
            default_currency=vendor_info.get('default_currency'),
            default_product_type=vendor_info.get('default_product_type', 'services')
        )

        try:
            self.db_session.add(vendor)
            self.db_session.commit()
            return vendor
        except Exception:
            # Handle race condition
            self.db_session.rollback()
            # Try to find the vendor that may have been created by another process
            existing = self.db_session.query(Vendor).filter(
                Vendor.name.ilike(vendor_info.get('name', vendor_name))
            ).first()
            return existing if existing else vendor  # Return original if not found

    def _format_nicknames(self, nicknames) -> str:
        """Format nicknames into a comma-separated string."""
        if not nicknames:
            return ''
        if isinstance(nicknames, str):
            return nicknames
        return ','.join(str(nick).strip() for nick in nicknames if nick)

    def _normalize_name(self, name: str) -> str:
        """Normalize vendor name with improved pattern matching."""
        if not name:
            return ""

        # Convert to lowercase and remove common business suffixes
        name = name.lower().strip()

        # Remove business suffixes (more comprehensive list)
        suffixes_pattern = r'\b(?:inc|llc|ltd|corp|corporation|company|co|aps|a/s|as|bv|gmbh|sarl|srl|ab|oy|plc)\b\.?'
        name = re.sub(suffixes_pattern, '', name)

        # Remove special characters and normalize whitespace
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()

        return name

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate optimized string similarity with early exit for performance."""
        if not str1 or not str2:
            return 0.0

        # Quick length check for performance
        if abs(len(str1) - len(str2)) > max(len(str1), len(str2)) * 0.5:
            return 0.0  # Too different in length

        # Check for substring matches first (faster)
        if str1 in str2 or str2 in str1:
            return 0.9  # High score for substring matches

        return SequenceMatcher(None, str1, str2).ratio()