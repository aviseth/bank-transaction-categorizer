# Prompt templates to eliminate duplicate prompt text
from functools import lru_cache


class PromptTemplates:
    """Centralized prompt templates to eliminate duplication."""

    CATEGORIES = [
        "vendor_payment",  # Payments to vendors/suppliers (includes subscriptions, rent, utilities, services, goods)
        "salary_payment",  # Employee salary and payroll payments
        "customer_payment_received",  # Incoming payments from customers
        "tax_payment",  # Tax payments and VAT payments
        "bank_fee",  # Bank fees and charges (not payments to vendors)
        "internal_transfer",  # Transfers between own accounts
        "not_categorized",  # Fallback for unclear transactions
    ]

    @staticmethod
    @lru_cache(maxsize=1)
    def get_categorization_rules() -> str:
        """Get categorization rules template with caching."""
        return """
Categories to choose from (MECE - Mutually Exclusive, Collectively Exhaustive):

- vendor_payment: ALL payments to external vendors/suppliers for business purposes
  * Includes: subscriptions, rent, utilities, software, services, goods, contractors
  * Examples: Office rent, LinkedIn subscription, cloud hosting, consulting fees
  * Direction: Usually DEBIT (outgoing)

- salary_payment: Employee compensation and payroll
  * Includes: Salaries, wages, bonuses, benefits
  * Direction: DEBIT (outgoing)

- customer_payment_received: Revenue from customers/clients
  * Includes: Payment for products/services sold, client invoices
  * Direction: CREDIT (incoming)

- tax_payment: All tax-related transactions
  * Includes: VAT payments, income tax, corporate tax, tax refunds
  * Direction: DEBIT (payments) or CREDIT (refunds)

- bank_fee: Bank charges and financial service fees
  * Includes: Transfer fees, account maintenance, currency conversion
  * Note: These are fees to the BANK, not payments to business vendors
  * Direction: Usually DEBIT (outgoing)

- internal_transfer: Transfers between your own accounts
  * Includes: Moving money between business accounts, savings transfers
  * Direction: Either DEBIT or CREDIT depending on account perspective

- not_categorized: Unclear transactions that don't fit above categories
  * Use only when transaction purpose cannot be determined

Analysis Rules:
1. vendor_payment is the broadest category - use for ANY business payment to external parties
2. Bank fees are NOT vendor payments - they're fees for banking services
3. If unsure between categories, use not_categorized rather than guessing
4. Consider transaction direction (debit/credit) to validate category choice"""

    @staticmethod
    @lru_cache(maxsize=1)
    def get_vendor_identification_rules() -> str:
        """Get vendor identification rules template with caching."""
        return """
Your task:
1. Look for company names, business names, or service provider names in ANY of the fields
2. Clean up the name by removing:
   - Transaction IDs, reference numbers
   - Special characters that aren't part of the company name
   - Location information unless it's part of the brand name
   - Payment processor references (unless that IS the vendor)
3. Identify the most recognizable, canonical form of the company name

Common patterns to look for:
- Well-known company names (Google, Microsoft, Stripe, etc.)
- Service provider names followed by description or ID
- Software/SaaS company names
- Professional service providers
- Subscription services

Examples:
- "STRIPE TECHNOLOGY EU" → "Stripe"
- "Google GSUITE_usetoday.i" → "Google Workspace"
- "METABASE INC" → "Metabase"
- "GitHub - GITHUB, INC." → "GitHub"
- "CLAUDE.AI SUBSCRIPTION" → "Claude AI"

Note: Return null for vendor_name only if you cannot identify any business/company name from the transaction details."""

    @staticmethod
    @lru_cache(maxsize=1)
    def get_vendor_enrichment_rules() -> str:
        """Get vendor enrichment rules template with caching."""
        return """
Return a JSON object with:
- name: canonical/official company name (e.g., "Mailchimp" not "MAILCHIMP" or "mailchimp")
- nicknames: list of alternative names, abbreviations, or trading names commonly used
- domain: primary website domain (without protocol, e.g., "mailchimp.com")
- default_description: detailed description of what the company does and their main business
- invoicing_country: 2-letter ISO country code where they typically invoice from (consider: many US companies invoice EU customers from Ireland "IE" or Luxembourg "LU" for tax reasons)
- default_currency: 3-letter ISO currency code they typically use for billing
- default_product_type: MUST be either "services" or "goods" - determine based on:
  * "services" = software, consulting, marketing, hosting, subscriptions, professional services, etc.
  * "goods" = physical products, merchandise, hardware, equipment, etc.
- confidence: float between 0 and 1 for overall accuracy of the information

Examples of classification:
- GitHub, Stripe, Google Workspace, LinkedIn = "services" (software/platforms)
- Mailchimp, Sentry, Claude.ai = "services" (SaaS platforms)
- Amazon (if for AWS/hosting) = "services", (if for products) = "goods"
- Apple (if App Store/iCloud) = "services", (if hardware) = "goods"

Important notes:
- If you're unsure about specific details, use null for optional fields
- Be especially careful about invoicing country - many tech companies use subsidiaries
- The default_product_type decision is critical for accounting categorization
- Consider the context: most software companies, platforms, and subscription services = "services"
- Physical retailers, manufacturers, distributors = "goods"

If this appears to be an unknown or very small company, still provide your best analysis based on the name and any context clues."""

    @staticmethod
    @lru_cache(maxsize=1)
    def get_batch_processing_rules() -> str:
        """Get batch processing rules template with caching."""
        return """
CATEGORIZATION RULES (MECE - Mutually Exclusive, Collectively Exhaustive):

• vendor_payment: ALL payments to external vendors/suppliers for business purposes
  - Includes: subscriptions, rent, utilities, software, services, goods, contractors
  - Examples: Office rent, LinkedIn subscription, cloud hosting, consulting fees

• salary_payment: Employee compensation and payroll payments

• customer_payment_received: Revenue from customers/clients for products/services sold

• tax_payment: All tax-related transactions (VAT, income tax, corporate tax, refunds)

• bank_fee: Bank charges and financial service fees (NOT business vendor payments)

• internal_transfer: Transfers between your own accounts

• not_categorized: Use only when transaction purpose cannot be determined

KEY RULES:
1. vendor_payment is the broadest category - use for ANY business payment to external parties
2. Bank fees are NOT vendor payments - they're fees for banking services
3. Subscriptions, rent, utilities are ALL vendor_payment
4. If unsure, use not_categorized rather than guessing

EXAMPLES:
• Stripe, PayPal (payment processors) + C = customer_payment_received
• Stripe, PayPal + D = vendor_payment (for their services)
• Google, GitHub, LinkedIn + D = vendor_payment
• Unknown company + large D = likely vendor_payment
• Government/tax authority + C = likely tax_payment

VENDOR IDENTIFICATION (for vendor_payment):
1. Extract company names from text/sender/message fields
2. Clean names by removing: transaction IDs, reference numbers, special characters, location info (unless brand name)
3. Identify canonical form:
   - "STRIPE TECHNOLOGY EU" → "Stripe"
   - "Google GSUITE_usetoday.i" → "Google Workspace"
   - "METABASE INC" → "Metabase"
   - "GitHub - GITHUB, INC." → "GitHub"
   - "CLAUDE.AI SUBSCRIPTION" → "Claude AI"
4. Set vendor_confidence 0.7-0.9 based on name clarity
5. For non-vendor categories: vendor_name=null, vendor_confidence=0.0"""
