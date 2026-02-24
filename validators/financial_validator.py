"""
Financial Validator Module

Validates financial logic and calculations mentioned in stories
against defined financial rules.
"""

import re
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass

from .base_validator import BaseValidator, ValidationResult, Severity


@dataclass
class FinancialOperation:
    """A financial operation detected in the story."""
    operation_type: str
    amounts: List[str]
    context: str
    location: Optional[str] = None


@dataclass
class FinancialRule:
    """A financial rule from the knowledge base."""
    rule_id: str
    rule_type: str
    description: str
    constraints: List[str]
    source: str


class FinancialValidator(BaseValidator):
    """
    Validates financial logic in stories.

    Checks:
    - Financial calculations are mentioned
    - Pricing rules are followed
    - Discount logic is properly defined
    - Refund policies are clear
    - Tax handling is specified
    - Currency handling is addressed
    - Rounding rules are defined
    """

    # Financial operation patterns (including Yassir Mobility specific)
    OPERATION_PATTERNS = {
        "payment": [
            r'\b(charge|payment|pay|bill|invoice)\b',
            r'\b(process(?:ing)?\s+payment)\b',
            r'\b(collect(?:ing)?\s+payment)\b',
        ],
        "refund": [
            r'\b(refund|reimburse|return)\b',
            r'\b(credit\s+back)\b',
            r'\b(money\s+back)\b',
            r'\b(revert\s+balance)\b',
        ],
        "discount": [
            r'\b(discount|coupon|promo(?:tion)?|voucher)\b',
            r'\b(\d+%?\s+off)\b',
            r'\b(price\s+reduction)\b',
            r'\b(challenge\s+discount)\b',
            r'\b(referral\s+discount)\b',
        ],
        "proration": [
            r'\b(prorate|prorat(?:ed|ion))\b',
            r'\b(partial\s+(?:charge|credit))\b',
            r'\b(pro-rata)\b',
        ],
        "prepaid_billing": [
            r'\b(prepaid|wallet\s+balance|top-up|topup)\b',
            r'\b(deduct(?:ion)?)\b',
            r'\b(wallet\s+(?:charge|deduction))\b',
        ],
        "postpaid_billing": [
            r'\b(postpaid|budget\s+limit|credit\s+limit)\b',
            r'\b(accrual|accrue)\b',
            r'\b(invoice\s+(?:total|amount|due))\b',
        ],
        "commission": [
            r'\b(commission|service\s+fee)\b',
            r'\b(\d+%?\s+commission)\b',
            r'\b(b2b\s+price)\b',
            r'\b(platform\s+fee)\b',
        ],
        "gift_card": [
            r'\b(gift\s+card|voucher\s+(?:value|balance))\b',
            r'\b(remaining\s+balance)\b',
            r'\b(card\s+(?:value|amount))\b',
        ],
        "referral_reward": [
            r'\b(free\s+trips?|referral\s+reward)\b',
            r'\b(invoice\s+discount)\b',
            r'\b(reward\s+(?:value|amount))\b',
        ],
        "tax": [
            r'\b(tax|vat|tva|gst|sales\s+tax)\b',
            r'\b(tax\s+(?:calculation|rate|exempt))\b',
            r'\b(HT|TTC)\b',
        ],
        "currency": [
            r'\b(currency|exchange\s+rate|forex)\b',
            r'\b(USD|EUR|GBP|DZD|TND|MAD|XOF)\b',
            r'[\$\u20ac\u00a3]\d+',
            r'\d+\s*(?:DZD|TND|MAD|XOF)\b',
        ],
    }

    # Amount patterns (including Yassir Mobility currencies)
    AMOUNT_PATTERNS = [
        r'[\$\u20ac\u00a3][\d,]+(?:\.\d{2})?',  # $100.00, 100.00, etc.
        r'\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|AED|SAR)',  # 100 USD
        r'\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:DZD|TND|MAD|XOF)',  # Yassir currencies
        r'\d+(?:\.\d+)?%',  # Percentages
        r'\d+K?\s*DZD',  # Common Yassir format like "500K DZD" or "5000 DZD"
    ]

    # Required considerations for financial operations
    REQUIRED_CONSIDERATIONS = {
        "payment": [
            "failure handling",
            "retry logic",
            "receipt/confirmation",
        ],
        "refund": [
            "refund amount calculation",
            "refund timeline",
            "partial refund",
        ],
        "discount": [
            "discount stacking",
            "discount expiry",
            "minimum order",
        ],
        "proration": [
            "calculation method",
            "billing cycle",
            "credit vs charge",
        ],
        "subscription_billing": [
            "billing cycle",
            "grace period",
            "failed payment handling",
        ],
        "tax": [
            "tax rate source",
            "tax exemptions",
            "tax display",
        ],
        "currency": [
            "exchange rate source",
            "rounding rules",
            "display format",
        ],
    }

    def __init__(self):
        """Initialize the financial validator."""
        super().__init__("FinancialValidator")
        self._compiled_patterns = {
            op_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for op_type, patterns in self.OPERATION_PATTERNS.items()
        }
        self._amount_patterns = [
            re.compile(p) for p in self.AMOUNT_PATTERNS
        ]

    def validate(
        self,
        story: Dict[str, Any],
        knowledge_context: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate financial logic in the story.

        Args:
            story: Story dictionary.
            knowledge_context: Retrieved knowledge chunks.

        Returns:
            ValidationResult with financial-related findings.
        """
        result = self._create_result(
            passed=True,
            summary="Financial validation completed"
        )

        story_text = self._extract_story_text(story)

        # Detect financial operations
        operations = self._detect_operations(story_text)

        # Extract amounts
        amounts = self._extract_amounts(story_text)

        # Load financial rules
        financial_rules = self._load_financial_rules(knowledge_context)

        result.details["detected_operations"] = [
            {"type": op.operation_type, "amounts": op.amounts}
            for op in operations
        ]
        result.details["detected_amounts"] = amounts
        result.details["financial_rules_loaded"] = len(financial_rules)

        if not operations:
            result.add_info(
                "No financial operations detected in story",
                suggestion="Verify if financial logic is relevant for this feature"
            )
            return result

        # Validate each operation
        for operation in operations:
            self._validate_operation(operation, story_text, financial_rules, result)

        # Check for missing financial considerations
        self._check_missing_considerations(operations, story_text, result)

        # Validate amounts
        self._validate_amounts(amounts, story_text, result)

        # Check financial rules coverage
        self._check_rule_coverage(operations, financial_rules, result)

        # Calculate score
        total_ops = len(operations)
        errors = result.error_count
        warnings = result.warning_count
        result.score = max(0, 1 - (errors * 0.2) - (warnings * 0.05))
        result.passed = errors == 0

        return result

    def _detect_operations(self, text: str) -> List[FinancialOperation]:
        """Detect financial operations in text."""
        operations = []

        for op_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    # Extract amounts near the match
                    amounts = self._extract_amounts(text)

                    operations.append(FinancialOperation(
                        operation_type=op_type,
                        amounts=amounts,
                        context=text[:200]
                    ))
                    break  # One match per operation type is enough

        return operations

    def _extract_amounts(self, text: str) -> List[str]:
        """Extract monetary amounts from text."""
        amounts = []
        for pattern in self._amount_patterns:
            matches = pattern.findall(text)
            amounts.extend(matches)
        return list(set(amounts))

    def _load_financial_rules(
        self,
        knowledge_context: List[Dict[str, Any]]
    ) -> List[FinancialRule]:
        """Load financial rules from knowledge context."""
        rules = []

        for chunk in knowledge_context:
            metadata = chunk.get("metadata", {})
            content = chunk.get("content", "")

            if metadata.get("rule_type") != "financial_logic":
                continue

            # Parse rules from content
            parsed_rules = self._parse_financial_rules(
                content,
                chunk.get("id", "unknown")
            )
            rules.extend(parsed_rules)

        return rules

    def _parse_financial_rules(
        self,
        content: str,
        source: str
    ) -> List[FinancialRule]:
        """Parse financial rules from markdown content."""
        rules = []

        # Look for rule patterns
        rule_pattern = r'(?:RULE|FIN)-(\d+):\s*(.+?)(?:\n|$)'
        matches = re.findall(rule_pattern, content)

        for rule_num, description in matches:
            rules.append(FinancialRule(
                rule_id=f"FIN-{rule_num}",
                rule_type="financial",
                description=description.strip(),
                constraints=[],
                source=source
            ))

        # Extract constraints
        constraint_pattern = r'(?:constraint|requirement|must):\s*(.+?)(?:\n|$)'
        constraints = re.findall(constraint_pattern, content, re.IGNORECASE)

        if constraints and rules:
            rules[0].constraints.extend(constraints)

        return rules

    def _validate_operation(
        self,
        operation: FinancialOperation,
        story_text: str,
        financial_rules: List[FinancialRule],
        result: ValidationResult
    ):
        """Validate a specific financial operation."""
        op_type = operation.operation_type
        story_lower = story_text.lower()

        # Check for error handling
        error_keywords = ["fail", "error", "invalid", "declined", "rejected"]
        has_error_handling = any(kw in story_lower for kw in error_keywords)

        if not has_error_handling:
            result.add_warning(
                f"No error handling mentioned for {op_type} operation",
                suggestion=f"Define what happens when {op_type} fails"
            )

        # Operation-specific validations
        if op_type == "payment":
            self._validate_payment_operation(story_text, result)
        elif op_type == "refund":
            self._validate_refund_operation(story_text, result)
        elif op_type == "discount":
            self._validate_discount_operation(story_text, result)
        elif op_type == "proration":
            self._validate_proration_operation(story_text, result)
        elif op_type == "tax":
            self._validate_tax_operation(story_text, result)

    def _validate_payment_operation(self, text: str, result: ValidationResult):
        """Validate payment-specific requirements."""
        text_lower = text.lower()

        # Check for payment method handling
        if "payment method" not in text_lower and "card" not in text_lower:
            result.add_info(
                "Payment method handling not specified",
                suggestion="Define supported payment methods"
            )

        # Check for receipt/confirmation
        confirmation_keywords = ["receipt", "confirmation", "invoice", "email"]
        if not any(kw in text_lower for kw in confirmation_keywords):
            result.add_warning(
                "Payment confirmation/receipt not mentioned",
                suggestion="Define how payment confirmation is sent"
            )

    def _validate_refund_operation(self, text: str, result: ValidationResult):
        """Validate refund-specific requirements."""
        text_lower = text.lower()

        # Check refund conditions
        if "condition" not in text_lower and "eligib" not in text_lower:
            result.add_warning(
                "Refund eligibility conditions not specified",
                suggestion="Define when refunds are allowed"
            )

        # Check refund timeline
        time_keywords = ["day", "hour", "week", "immediately", "instant"]
        if not any(kw in text_lower for kw in time_keywords):
            result.add_info(
                "Refund timeline not specified",
                suggestion="Define how long refunds take to process"
            )

    def _validate_discount_operation(self, text: str, result: ValidationResult):
        """Validate discount-specific requirements."""
        text_lower = text.lower()

        # Check discount limits
        limit_keywords = ["maximum", "minimum", "limit", "cap", "floor"]
        if not any(kw in text_lower for kw in limit_keywords):
            result.add_info(
                "Discount limits not specified",
                suggestion="Define maximum/minimum discount amounts"
            )

        # Check stacking rules
        if "stack" not in text_lower and "combine" not in text_lower:
            result.add_info(
                "Discount stacking rules not specified",
                suggestion="Define if discounts can be combined"
            )

    def _validate_proration_operation(self, text: str, result: ValidationResult):
        """Validate proration-specific requirements."""
        text_lower = text.lower()

        # Check calculation method
        calc_keywords = ["daily", "monthly", "calculate", "formula"]
        if not any(kw in text_lower for kw in calc_keywords):
            result.add_warning(
                "Proration calculation method not specified",
                suggestion="Define how prorated amount is calculated"
            )

    def _validate_tax_operation(self, text: str, result: ValidationResult):
        """Validate tax-specific requirements."""
        text_lower = text.lower()

        # Check tax rate source
        if "rate" not in text_lower:
            result.add_warning(
                "Tax rate source not specified",
                suggestion="Define where tax rates come from"
            )

        # Check tax display
        display_keywords = ["display", "show", "include", "separate"]
        if not any(kw in text_lower for kw in display_keywords):
            result.add_info(
                "Tax display format not specified",
                suggestion="Define how taxes are shown to users"
            )

    def _check_missing_considerations(
        self,
        operations: List[FinancialOperation],
        story_text: str,
        result: ValidationResult
    ):
        """Check for missing financial considerations."""
        story_lower = story_text.lower()

        for operation in operations:
            op_type = operation.operation_type
            required = self.REQUIRED_CONSIDERATIONS.get(op_type, [])

            for consideration in required:
                # Simple keyword check
                keywords = consideration.split()
                if not any(kw in story_lower for kw in keywords):
                    result.add_info(
                        f"'{consideration}' not addressed for {op_type}",
                        suggestion=f"Consider defining {consideration}"
                    )

    def _validate_amounts(
        self,
        amounts: List[str],
        story_text: str,
        result: ValidationResult
    ):
        """Validate monetary amounts in the story."""
        if not amounts:
            return

        # Check for mixed currencies
        currencies_found = set()
        for amount in amounts:
            if "USD" in amount or "$" in amount:
                currencies_found.add("USD")
            if "EUR" in amount or "\u20ac" in amount:
                currencies_found.add("EUR")
            if "GBP" in amount or "\u00a3" in amount:
                currencies_found.add("GBP")

        if len(currencies_found) > 1:
            result.add_warning(
                f"Multiple currencies detected: {currencies_found}",
                suggestion="Clarify currency handling and conversion"
            )

        # Check for rounding
        story_lower = story_text.lower()
        if "round" not in story_lower and amounts:
            result.add_info(
                "Rounding rules not specified",
                suggestion="Define how amounts should be rounded"
            )

    def _check_rule_coverage(
        self,
        operations: List[FinancialOperation],
        financial_rules: List[FinancialRule],
        result: ValidationResult
    ):
        """Check if relevant financial rules are covered."""
        if not financial_rules:
            if operations:
                result.add_warning(
                    "Financial operations found but no financial rules in knowledge base",
                    suggestion="Add financial rules to knowledge base for validation"
                )
            return

        # Report matched rules
        result.details["matched_rules"] = [
            {"id": rule.rule_id, "description": rule.description[:100]}
            for rule in financial_rules
        ]


if __name__ == "__main__":
    # Quick test
    validator = FinancialValidator()

    test_story = {
        "title": "Subscription Upgrade with Proration",
        "description": """
        When a user upgrades from Basic ($10/month) to Premium ($25/month),
        calculate the prorated amount based on remaining days in billing cycle.

        The system should charge the difference immediately via their saved payment method.
        """,
        "acceptance_criteria": [
            "Given user is on Basic plan",
            "When they upgrade to Premium mid-cycle",
            "Then prorated amount should be calculated",
            "And payment should be processed immediately"
        ]
    }

    result = validator.validate(test_story, [])
    print(result.format())
