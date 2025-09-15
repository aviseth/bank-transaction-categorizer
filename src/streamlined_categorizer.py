# Streamlined categorizer with reduced code length
import hashlib
import json
import os
import time
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from src.prompt_templates import PromptTemplates
from src.confidence_calculator import ConfidenceCalculator

load_dotenv()


class TransactionCategory(BaseModel):
    category: str
    confidence: float
    reasoning: str


class VendorIdentification(BaseModel):
    vendor_name: Optional[str]
    confidence: float
    reasoning: str


class VendorInfo(BaseModel):
    name: str
    nicknames: List[str]
    domain: Optional[str]
    default_description: Optional[str]
    invoicing_country: Optional[str]
    default_currency: Optional[str]
    default_product_type: str
    confidence: float


class FastBatchResult(BaseModel):
    transaction_id: int
    category: str
    confidence: float
    vendor_name: Optional[str] = None
    vendor_confidence: float = 0.0


class StreamlinedCategorizer:
    """Streamlined categorizer with minimal code duplication and caching."""

    def __init__(self, api_key: Optional[str] = None, verify_domains: bool = True):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = None
        self.model = "gpt-4o-mini"
        self.provider = "OpenAI"
        self.verify_domains = verify_domains

        # Initialize caches for performance optimization
        self._vendor_cache = {}
        self._domain_cache = {}
        self._prompt_cache = {}
        self._cache_ttl = 3600  # 1 hour TTL for cached items

        # Initialize confidence calculator
        self.confidence_calc = ConfidenceCalculator()

        if ANTHROPIC_AVAILABLE:
            try:
                self.anthropic_client = anthropic.Anthropic(
                    api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
                )
            except Exception:
                pass

    def _get_cache_key(self, prompt: str, system_message: str = None) -> str:
        """Generate cache key for API calls."""
        content = f"{system_message or ''}||{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _is_cache_expired(self, timestamp: float) -> bool:
        """Check if cached item has expired."""
        return time.time() - timestamp > self._cache_ttl

    def _make_api_call(self, prompt: str, system_message: str = None) -> dict:
        """Unified API call method with caching to eliminate duplication and reduce API costs."""
        # Check cache first for repeated calls
        cache_key = self._get_cache_key(prompt, system_message)
        if cache_key in self._prompt_cache:
            cached_item = self._prompt_cache[cache_key]
            if not self._is_cache_expired(cached_item["timestamp"]):
                print("[CACHE HIT] Using cached result for API call")
                return cached_item["data"]
            else:
                # Clean up expired cache entry
                del self._prompt_cache[cache_key]

        try:
            if self.provider == "Anthropic" and self.anthropic_client:
                response = self.anthropic_client.messages.create(
                    model=self.model,
                    max_tokens=3000,
                    temperature=0.0,
                    messages=[
                        {
                            "role": "user",
                            "content": f"{system_message}\n\n{prompt}\n\nRespond with valid JSON only.",
                        }
                    ],
                )
                result = json.loads(response.content[0].text)
            else:
                messages = [{"role": "user", "content": prompt}]
                if system_message:
                    messages.insert(0, {"role": "system", "content": system_message})

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                result = json.loads(response.choices[0].message.content)

            # Cache the successful result
            self._prompt_cache[cache_key] = {"data": result, "timestamp": time.time()}

            return result
        except Exception as e:
            print(f"API call error: {e}")
            return {}

    def categorize_transaction(self, transaction: Dict) -> TransactionCategory:
        """Categorize a single transaction."""
        amount = transaction.get("amount", 0)
        is_debit = amount < 0

        prompt = f"""As a financial transaction analyst, categorize this bank transaction by analyzing the vendor/company and understanding what the payment represents.

Transaction details:
- Date: {transaction.get("date")}
- Text: {transaction.get("text")}
- Message: {transaction.get("message")}
- Type: {transaction.get("transaction_type")}
- Amount: {amount} {transaction.get("currency")} ({"DEBIT/Outgoing" if is_debit else "CREDIT/Incoming"})
- Sender: {transaction.get("sender")}
- Receiver: {transaction.get("receiver")}

{PromptTemplates.get_categorization_rules()}

Return a JSON object with:
- category: the most appropriate category from the list above
- confidence: float between 0 and 1 (how certain you are)
- reasoning: detailed explanation of your analysis and decision"""

        result = self._make_api_call(
            prompt, "You are a financial transaction categorization expert."
        )
        if result:
            # Use dynamic confidence calculation if LLM provided one
            llm_confidence = result.get('confidence')
            calculated_confidence = self.confidence_calc.calculate_category_confidence(
                transaction, result.get('category', 'other'), llm_confidence
            )
            result['confidence'] = calculated_confidence
            return TransactionCategory(**result)
        else:
            # Calculate fallback confidence for error cases
            fallback_confidence = self.confidence_calc.calculate_llm_fallback_confidence(
                transaction, "other"
            )
            return TransactionCategory(
                category="other",
                confidence=fallback_confidence,
                reasoning="Failed to categorize due to error",
            )

    def identify_vendor(self, transaction: Dict) -> VendorIdentification:
        """Identify vendor from transaction."""
        prompt = f"""As a financial analyst, extract the vendor/company name from this bank transaction by analyzing all available text fields.

Transaction details:
- Text: {transaction.get("text")}
- Message: {transaction.get("message")}
- Sender: {transaction.get("sender")}
- Receiver: {transaction.get("receiver")}
- Amount: {transaction.get("amount")} {transaction.get("currency")}

{PromptTemplates.get_vendor_identification_rules()}

Return a JSON object with:
- vendor_name: cleaned, canonical company name (or null if no clear vendor found)
- confidence: float between 0 and 1 (how certain you are this is correct)
- reasoning: explain what you found and how you cleaned/identified the name"""

        result = self._make_api_call(
            prompt,
            "You are an expert at identifying vendor names from bank transactions.",
        )
        if result:
            # Use dynamic vendor confidence calculation
            vendor_name = result.get('vendor_name')
            llm_confidence = result.get('confidence')
            calculated_confidence = self.confidence_calc.calculate_vendor_confidence(
                vendor_name, transaction, llm_confidence
            )
            result['confidence'] = calculated_confidence
            return VendorIdentification(**result)
        else:
            return VendorIdentification(
                vendor_name=None,
                confidence=0.0,
                reasoning="Failed to identify due to error",
            )

    def enrich_vendor(self, vendor_name: str) -> VendorInfo:
        """Enrich vendor information with caching for repeated lookups."""
        # Check vendor cache first
        cache_key = vendor_name.lower().strip()
        if cache_key in self._vendor_cache:
            cached_item = self._vendor_cache[cache_key]
            if not self._is_cache_expired(cached_item["timestamp"]):
                print(f"[CACHE HIT] Using cached vendor info for {vendor_name}")
                return cached_item["data"]
            else:
                del self._vendor_cache[cache_key]

        prompt = f"""As a business intelligence analyst, research and provide comprehensive information about this vendor/company: {vendor_name}

Analyze what type of business this is, what they sell/provide, and determine if they primarily deal in services or goods.

{PromptTemplates.get_vendor_enrichment_rules()}"""

        result = self._make_api_call(
            prompt, "You are an expert on company information and business operations."
        )

        if not result:
            # Calculate fallback confidence for failed enrichment
            fallback_confidence = self.confidence_calc.calculate_llm_fallback_confidence(
                {'text': vendor_name}, None
            )
            return VendorInfo(
                name=vendor_name,
                nicknames=[],
                domain=None,
                default_description=None,
                invoicing_country=None,
                default_currency=None,
                default_product_type="services",
                confidence=fallback_confidence,
            )

        # Validate and normalize response data
        result["nicknames"] = (
            result.get("nicknames", [])
            if isinstance(result.get("nicknames"), list)
            else []
        )
        product_type = result.get("default_product_type", "services")
        result["default_product_type"] = (
            product_type.lower()
            if product_type and product_type.lower() in ["services", "goods"]
            else "services"
        )

        # Verify domain if provided and verification is enabled
        domain = result.get("domain")
        if domain and self.verify_domains:
            is_valid, domain_confidence = self._verify_domain(domain, vendor_name)

            # Apply domain verification results to confidence
            original_confidence = result.get("confidence", self.confidence_calc.calculate_llm_fallback_confidence({'text': vendor_name}, None))
            penalty_factor = self.confidence_calc.calculate_domain_penalty_factor(is_valid, domain_confidence)
            result["confidence"] = original_confidence * penalty_factor

            if not is_valid and domain_confidence == 0.0:
                # If the provided domain failed, try to find a valid domain from cache
                # This handles cases where AI returns a single invalid domain but we have valid ones cached
                valid_domain = None

                # Check if we have any valid domains in cache for this vendor
                for cache_key, cached_item in self._domain_cache.items():
                    if (
                        cache_key.endswith(f"||{vendor_name.lower()}")
                        and not self._is_cache_expired(cached_item["timestamp"])
                        and cached_item["data"][0]
                    ):
                        # Extract domain from cache key
                        domain_from_cache = cache_key.split("||")[0]
                        valid_domain = domain_from_cache
                        break

                # If no cached domain found, try common domain variations
                if not valid_domain and domain:
                    base_domain = domain.split(".")[0] if "." in domain else domain
                    common_tlds = [".ai", ".com", ".io", ".co", ".net", ".org"]

                    for tld in common_tlds:
                        if (
                            tld != domain.split(".")[-1] if "." in domain else ".com"
                        ):  # Don't retry the same TLD
                            test_domain = f"{base_domain}{tld}"
                            test_valid, _ = self._verify_domain(
                                test_domain, vendor_name
                            )
                            if test_valid:
                                valid_domain = test_domain
                                break

                if valid_domain:
                    result["domain"] = valid_domain
                else:
                    result["domain"] = None
            elif is_valid:
                # If we have comma-separated domains, extract the first valid one
                if "," in domain:
                    domains_to_try = [d.strip() for d in domain.split(",") if d.strip()]
                    # Find the first valid domain by checking cache
                    valid_domain = None
                    for single_domain in domains_to_try:
                        # Try both original case and lowercase for cache lookup
                        cache_keys_to_try = [
                            f"{single_domain}||{vendor_name.lower()}",
                            f"{single_domain.lower()}||{vendor_name.lower()}",
                        ]
                        for cache_key in cache_keys_to_try:
                            if cache_key in self._domain_cache:
                                cached_item = self._domain_cache[cache_key]
                                if (
                                    not self._is_cache_expired(cached_item["timestamp"])
                                    and cached_item["data"][0]
                                ):
                                    valid_domain = single_domain
                                    break
                        if valid_domain:
                            break

                    # If we found a valid domain, use it; otherwise keep the original comma-separated string
                    if valid_domain:
                        result["domain"] = valid_domain

        vendor_info = VendorInfo(**result)

        # Cache the vendor info for future lookups
        self._vendor_cache[cache_key] = {"data": vendor_info, "timestamp": time.time()}

        return vendor_info

    def categorize_batch_ultra_fast(
        self, transactions: List[Dict], batch_size: int = 20, progress_callback=None
    ) -> List[FastBatchResult]:
        """Ultra-fast batch processing with minimal code."""
        results = []
        total_batches = (len(transactions) + batch_size - 1) // batch_size

        for i in range(0, len(transactions), batch_size):
            batch = transactions[i : i + batch_size]
            batch_num = i // batch_size + 1

            if progress_callback:
                progress = 20 + (batch_num / total_batches) * 60
                progress_callback(
                    int(progress),
                    f"Processing batch {batch_num}/{total_batches} ({len(batch)} transactions)",
                )

            # Create minimal data for each transaction
            minimal_data = [
                {
                    "id": i + idx,
                    "text": txn.get("text", ""),
                    "amount": f"{txn.get('amount', 0)} {'D' if txn.get('amount', 0) < 0 else 'C'}",
                    "sender": txn.get("sender", ""),
                    "message": txn.get("message", ""),
                }
                for idx, txn in enumerate(batch)
            ]

            prompt = f"""As a financial transaction analyst, categorize these {len(minimal_data)} bank transactions by analyzing the vendor/company and understanding what each payment represents.

Transaction data: {json.dumps(minimal_data)}
Note: D=DEBIT/Outgoing, C=CREDIT/Incoming

Categories: {", ".join(PromptTemplates.CATEGORIES)}

{PromptTemplates.get_batch_processing_rules()}

Return JSON: {{"results": [{{"transaction_id": 0, "category": "vendor_payment", "confidence": 0.9, "vendor_name": "Stripe", "vendor_confidence": 0.8}}]}}"""

            result = self._make_api_call(
                prompt,
                "You categorize bank transactions quickly and accurately using comprehensive analysis.",
            )
            batch_results = result.get("results", [])

            # Convert to FastBatchResult objects
            for item in batch_results:
                try:
                    # Get the original transaction for confidence calculation
                    transaction_index = item.get("transaction_id", i + len(results)) - i
                    original_transaction = batch[transaction_index] if transaction_index < len(batch) else {}

                    # Calculate dynamic confidence values
                    llm_confidence = item.get("confidence")
                    category = item.get("category", "other")
                    calculated_confidence = self.confidence_calc.calculate_category_confidence(
                        original_transaction, category, llm_confidence
                    )

                    vendor_name = item.get("vendor_name")
                    llm_vendor_confidence = item.get("vendor_confidence")
                    calculated_vendor_confidence = self.confidence_calc.calculate_vendor_confidence(
                        vendor_name, original_transaction, llm_vendor_confidence
                    ) if vendor_name else 0.0

                    results.append(
                        FastBatchResult(
                            transaction_id=item.get("transaction_id", i + len(results)),
                            category=category,
                            confidence=calculated_confidence,
                            vendor_name=vendor_name,
                            vendor_confidence=calculated_vendor_confidence,
                        )
                    )
                except Exception as e:
                    print(f"Error processing item: {e}")
                    # Calculate fallback confidence for error cases
                    fallback_transaction = batch[len(results)] if len(results) < len(batch) else {}
                    fallback_confidence = self.confidence_calc.calculate_llm_fallback_confidence(
                        fallback_transaction, "other"
                    )
                    results.append(
                        FastBatchResult(
                            transaction_id=i + len(results),
                            category="other",
                            confidence=fallback_confidence,
                        )
                    )

        return results

    def _verify_domain(self, domain: str, company_name: str) -> Tuple[bool, float]:
        """Verify if a domain belongs to the company with caching for repeated checks."""
        if not domain:
            return False, 0.0

        # Handle comma-separated domains by trying each one
        domains_to_try = [d.strip() for d in domain.split(",") if d.strip()]

        for single_domain in domains_to_try:
            # Check domain cache first for this specific domain
            cache_key = f"{single_domain}||{company_name.lower()}"
            if cache_key in self._domain_cache:
                cached_item = self._domain_cache[cache_key]
                if not self._is_cache_expired(cached_item["timestamp"]):
                    print(
                        f"[CACHE HIT] Using cached domain verification for {single_domain}"
                    )
                    result = cached_item["data"]
                    if result[0]:  # If this domain is valid, return it
                        return result
                    continue  # Try next domain if this one failed
                else:
                    del self._domain_cache[cache_key]

            try:
                test_url = (
                    f"https://{single_domain}"
                    if not single_domain.startswith(("http://", "https://"))
                    else single_domain
                )
                start_time = time.time()
                response = requests.get(
                    test_url,
                    timeout=2,  # Reduced from 5s to 2s for faster processing
                    allow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; VendorVerifier/1.0)"
                    },
                )
                response_time = time.time() - start_time

                # Calculate content matches for dynamic scoring
                content = response.text.lower()
                company_lower = company_name.lower()
                name_words = company_lower.split()
                matches = sum(
                    1 for word in name_words if len(word) > 2 and word in content
                )
                total_words = len(name_words)

                # Use dynamic confidence calculation
                result = self.confidence_calc.calculate_domain_confidence(
                    single_domain, company_name, response_time, matches, total_words, response.status_code
                )

            except Exception as e:
                print(f"Domain verification error for {single_domain}: {e}")
                result = (False, 0.0)

            # Cache the domain verification result for this specific domain
            self._domain_cache[cache_key] = {"data": result, "timestamp": time.time()}

            # If this domain is valid, return it immediately
            if result[0]:
                print(
                    f"[DOMAIN VERIFIED] Successfully verified domain: {single_domain}"
                )
                return result

        # If no domains were valid, return the last result (or False, 0.0 if no domains tried)
        return result if "result" in locals() else (False, 0.0)

    def clear_cache(self):
        """Clear all caches manually if needed."""
        self._vendor_cache.clear()
        self._domain_cache.clear()
        self._prompt_cache.clear()
        print("All caches cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring."""
        return {
            "vendor_cache_size": len(self._vendor_cache),
            "domain_cache_size": len(self._domain_cache),
            "prompt_cache_size": len(self._prompt_cache),
        }
