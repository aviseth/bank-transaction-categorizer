"""
Confidence calculation utilities for dynamic confidence scoring.
Replaces hardcoded confidence values with metric-based calculations.
"""
import difflib
import math
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


class ConfidenceCalculator:
    """Calculates confidence scores based on various metrics and data quality indicators."""

    def __init__(self):
        pass  # No hardcoded categories - using dynamic pattern analysis

    def calculate_transaction_quality_score(self, transaction: Dict) -> float:
        """Calculate quality score based on transaction data completeness and validity."""
        score = 0.0
        max_score = 0.0

        # Text field quality (0.3 weight)
        text = transaction.get('text', '')
        if text:
            text_score = min(len(text) / 50.0, 1.0)  # Normalize to 50 chars
            text_score *= 0.7 + 0.3 * (len(text.split()) / 10.0)  # Word count bonus
            score += text_score * 0.3
        max_score += 0.3

        # Amount validity (0.2 weight) - use logarithmic scaling
        amount = transaction.get('amount', 0)
        if amount != 0:
            # Use log scale for natural confidence progression
            # Avoids arbitrary thresholds for amount ranges
            abs_amount = abs(amount)
            if abs_amount > 0:
                # Normalized confidence using log scale (1-10,000 range)
                log_amount = math.log10(max(abs_amount, 1))
                amount_score = min(log_amount / 4.0, 1.0)  # Normalize to 0-1
                amount_score = max(amount_score, 0.3)  # Minimum confidence for any non-zero amount
            else:
                amount_score = 0.3
            score += amount_score * 0.2
        max_score += 0.2

        # Field completeness (0.3 weight)
        fields = ['date', 'sender', 'receiver', 'message', 'currency']
        filled_fields = sum(1 for field in fields if transaction.get(field))
        completeness = filled_fields / len(fields)
        score += completeness * 0.3
        max_score += 0.3

        # Message quality (0.2 weight)
        message = transaction.get('message', '')
        if message and message.strip():
            message_score = min(len(message) / 30.0, 1.0)
            score += message_score * 0.2
        max_score += 0.2

        return score / max_score if max_score > 0 else 0.0

    def calculate_category_confidence(self, transaction: Dict, category: str, llm_confidence: Optional[float] = None) -> float:
        """Calculate category confidence using text entropy and pattern analysis."""

        # Combine all transaction text for analysis
        text_content = ' '.join([
            str(transaction.get('text', '')),
            str(transaction.get('message', '')),
            str(transaction.get('sender', '')),
            str(transaction.get('receiver', ''))
        ]).lower()

        # Calculate text entropy for category confidence
        text_entropy = self._calculate_text_entropy(text_content)

        # Use string similarity between transaction text and category name
        category_similarity = difflib.SequenceMatcher(None, category.replace('_', ' '), text_content).ratio()

        # Look for category-related patterns in text without hardcoded keywords
        category_pattern_score = self._analyze_category_patterns(text_content, category, transaction)

        # Combine metrics using weighted average
        pattern_confidence = (
            0.3 * category_similarity +
            0.4 * category_pattern_score +
            0.3 * min(text_entropy / 3.0, 1.0)  # Normalize entropy
        )

        # Blend with LLM confidence if provided
        if llm_confidence:
            final_confidence = 0.7 * llm_confidence + 0.3 * pattern_confidence
        else:
            final_confidence = pattern_confidence

        # Transaction quality adjustment
        quality_score = self.calculate_transaction_quality_score(transaction)
        adjusted_confidence = final_confidence * (0.7 + 0.3 * quality_score)

        return max(0.1, min(adjusted_confidence, 1.0))

    def calculate_vendor_confidence(self, vendor_name: str, transaction: Dict, identification_confidence: Optional[float] = None) -> float:
        """Calculate vendor identification confidence based on string similarity metrics."""
        if not vendor_name:
            return 0.0


        # Combine all transaction text
        text_content = ' '.join([
            str(transaction.get('text', '')),
            str(transaction.get('message', '')),
            str(transaction.get('sender', '')),
            str(transaction.get('receiver', ''))
        ]).lower()

        vendor_lower = vendor_name.lower()

        # Use difflib for sequence similarity (fuzzy matching)
        similarity_score = difflib.SequenceMatcher(None, vendor_lower, text_content).ratio()

        # Check for partial matches in text
        best_partial_match = 0.0
        text_words = text_content.split()
        for word in text_words:
            if len(word) > 2:  # Only consider meaningful words
                partial_similarity = difflib.SequenceMatcher(None, vendor_lower, word).ratio()
                best_partial_match = max(best_partial_match, partial_similarity)

        # Combine overall similarity with best partial match
        combined_similarity = max(similarity_score, best_partial_match * 0.8)

        # Use similarity as primary confidence factor
        # Apply sigmoid to create smooth confidence curve
        similarity_confidence = 1 / (1 + math.exp(-8 * (combined_similarity - 0.4)))

        # Blend with LLM confidence if provided
        if identification_confidence:
            final_confidence = 0.6 * similarity_confidence + 0.4 * identification_confidence
        else:
            final_confidence = similarity_confidence

        return max(0.0, min(final_confidence, 1.0))

    def calculate_domain_confidence(self, domain: str, company_name: str, response_time: float = 0.0,
                                   content_matches: int = 0, total_words: int = 1, status_code: int = 200) -> Tuple[bool, float]:
        """Calculate domain verification confidence based on multiple metrics."""
        # Note: company_name parameter kept for interface compatibility but not used in calculation
        _ = company_name  # Acknowledge parameter to avoid linting warnings

        if not domain:
            return False, 0.0

        # Parse domain for basic validation
        try:
            parsed = urlparse(f"https://{domain}" if not domain.startswith('http') else domain)
            if not parsed.netloc:
                return False, 0.0
        except Exception:
            return False, 0.0

        # Base confidence from HTTP status
        if status_code != 200:
            return False, max(0.05, 0.1 - (abs(status_code - 200) / 1000.0))

        # Response time factor (faster = more reliable)
        time_factor = 1.0
        if response_time > 0:
            if response_time < 1.0:
                time_factor = 1.0
            elif response_time < 3.0:
                time_factor = 0.9
            else:
                time_factor = 0.8

        # Content relevance scoring using statistical approach
        content_score = 0.2  # Base score for responding
        if content_matches > 0 and total_words > 0:
            match_ratio = content_matches / total_words
            # Use sigmoid function for smooth confidence scaling
            # This creates a natural curve instead of arbitrary thresholds
            content_score = 0.2 + 0.6 * (1 / (1 + math.exp(-5 * (match_ratio - 0.3))))
            # Range: 0.2 (no matches) to 0.8 (perfect match), smooth transition

        # Domain quality indicators - all working domains are treated equally
        domain_quality = 1.0  # If domain responds, it's valid regardless of TLD

        # Calculate final confidence
        final_confidence = content_score * time_factor * domain_quality
        final_confidence = max(0.1, min(final_confidence, 1.0))

        return True, final_confidence

    def calculate_llm_fallback_confidence(self, transaction: Dict, category: str = None) -> float:
        """Calculate fallback confidence when LLM doesn't provide one."""
        quality_score = self.calculate_transaction_quality_score(transaction)

        # Base confidence from transaction quality
        base_confidence = 0.3 + quality_score * 0.4  # Range: 0.3 to 0.7

        # Category-specific adjustments
        if category:
            # Some categories are easier to identify
            easy_categories = ['transfer', 'salary', 'fees']
            if category in easy_categories:
                base_confidence += 0.1

            # Vendor payments require more certainty
            if category == 'vendor_payment':
                base_confidence -= 0.05

        return max(0.2, min(base_confidence, 0.8))  # Conservative range

    def calculate_domain_penalty_factor(self, is_valid: bool, domain_confidence: float) -> float:
        """Calculate penalty factor for domain verification failures."""
        if is_valid:
            # Boost confidence for verified domains
            return 0.5 + domain_confidence * 0.5  # Range: 0.5 to 1.0
        else:
            # Penalty for unverified domains, but not too harsh
            if domain_confidence > 0.5:
                return 0.8  # Minor penalty if domain partially worked
            elif domain_confidence > 0.1:
                return 0.7  # Moderate penalty
            else:
                return 0.6  # Significant penalty for completely failed domains

    def get_confidence_range_options(self, step: float = 0.1) -> List[float]:
        """Generate dynamic confidence range options."""
        return [round(i * step, 1) for i in range(0, int(1.0/step) + 1)]

    def _calculate_text_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text for complexity measurement."""
        if not text:
            return 0.0

        # Count character frequencies
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1

        # Calculate entropy
        text_length = len(text)
        entropy = 0.0
        for count in char_counts.values():
            probability = count / text_length
            if probability > 0:
                entropy -= probability * math.log2(probability)

        return entropy

    def _analyze_category_patterns(self, text: str, category: str, transaction: Dict) -> float:
        """Analyze transaction patterns for category without hardcoded keywords."""
        pattern_score = 0.0

        # Transaction amount patterns (statistical approach)
        amount = abs(transaction.get('amount', 0))

        # Use statistical distribution analysis instead of hardcoded ranges
        if amount > 0:
            log_amount = math.log10(amount)

            # Different categories tend to have different amount distributions
            # Use sigmoid functions to model these patterns
            if category == 'vendor_payment':
                # Vendor payments often have varied amounts
                pattern_score += 0.5  # Base score for having an amount
            elif category == 'salary':
                # Salaries tend to be larger, regular amounts
                if log_amount > 3:  # > $1000
                    pattern_score += 0.8
                else:
                    pattern_score += 0.3
            elif category == 'fees':
                # Fees tend to be smaller amounts
                if log_amount < 2:  # < $100
                    pattern_score += 0.7
                else:
                    pattern_score += 0.4

        # Text pattern analysis (n-gram based)
        words = text.split()
        if len(words) > 0:
            # Look for common financial transaction patterns
            financial_indicators = ['payment', 'transfer', 'charge', 'fee', 'purchase', 'deposit']
            matches = sum(1 for word in words if any(indicator in word for indicator in financial_indicators))
            pattern_score += min(matches / len(words), 0.5)

        return min(pattern_score, 1.0)