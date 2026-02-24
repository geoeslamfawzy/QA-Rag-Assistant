"""
Cross-Dependency Checker Module

Detects cross-module dependencies and integration risks in stories.
"""

import re
from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass, field

from .base_validator import BaseValidator, ValidationResult, Severity


@dataclass
class ModuleDependency:
    """A dependency between modules."""
    from_module: str
    to_module: str
    dependency_type: str  # data, event, api, state
    description: str
    risk_level: str
    source: str


@dataclass
class IntegrationPoint:
    """An integration point detected in the story."""
    name: str
    point_type: str  # api, webhook, event, queue, database
    modules_involved: List[str]
    description: str


@dataclass
class DependencyRisk:
    """A dependency risk identified."""
    from_module: str
    to_module: str
    risk_description: str
    impact: str
    mitigation: str


class CrossDepChecker(BaseValidator):
    """
    Checks for cross-module dependencies and integration risks.

    Features:
    - Module dependency detection
    - Integration point identification
    - Risk chain analysis
    - Impact assessment
    - Mitigation suggestions
    """

    # Module detection patterns
    MODULE_PATTERNS = {
        "user_management": [
            "user", "account", "profile", "authentication", "login",
            "registration", "password", "session"
        ],
        "subscription": [
            "subscription", "plan", "tier", "billing", "renewal",
            "upgrade", "downgrade"
        ],
        "payment_processing": [
            "payment", "charge", "transaction", "card", "wallet",
            "payout", "refund"
        ],
        "invoicing": [
            "invoice", "receipt", "billing", "tax", "vat"
        ],
        "notification": [
            "notification", "email", "sms", "push", "alert"
        ],
        "referral_system": [
            "referral", "invite", "referrer", "referee", "bonus"
        ],
        "gift_cards": [
            "gift card", "voucher", "coupon", "promo", "redeem"
        ],
        "reporting": [
            "report", "analytics", "dashboard", "metrics", "export"
        ],
        "audit_logging": [
            "audit", "log", "track", "history", "event"
        ],
        "access_control": [
            "role", "permission", "access", "privilege", "authorization"
        ]
    }

    # Integration point patterns
    INTEGRATION_PATTERNS = {
        "api": [
            r'\bapi\b', r'\bendpoint\b', r'\brest\b', r'\bhttp\b',
            r'\brequest\b', r'\bresponse\b'
        ],
        "webhook": [
            r'\bwebhook\b', r'\bcallback\b', r'\bnotify\b'
        ],
        "event": [
            r'\bevent\b', r'\bpublish\b', r'\bsubscribe\b',
            r'\btrigger\b', r'\blisten\b'
        ],
        "queue": [
            r'\bqueue\b', r'\basync\b', r'\bjob\b', r'\bworker\b'
        ],
        "database": [
            r'\bdatabase\b', r'\bdb\b', r'\btable\b', r'\bquery\b',
            r'\btransaction\b'
        ]
    }

    # Known risky dependency patterns
    RISKY_DEPENDENCIES = [
        {
            "from": "subscription",
            "to": "payment_processing",
            "risk": "Payment must complete before subscription state change",
            "mitigation": "Use transaction or saga pattern"
        },
        {
            "from": "user_management",
            "to": "subscription",
            "risk": "User deletion must handle active subscriptions",
            "mitigation": "Define cascade behavior"
        },
        {
            "from": "payment_processing",
            "to": "notification",
            "risk": "Payment confirmation must be sent atomically",
            "mitigation": "Use outbox pattern or idempotent notifications"
        },
        {
            "from": "referral_system",
            "to": "payment_processing",
            "risk": "Referral bonus calculation depends on payment success",
            "mitigation": "Process bonus after payment confirmation"
        },
        {
            "from": "gift_cards",
            "to": "payment_processing",
            "risk": "Gift card redemption must be atomic with payment",
            "mitigation": "Use distributed transaction or compensation"
        }
    ]

    def __init__(self):
        """Initialize the cross-dependency checker."""
        super().__init__("CrossDepChecker")
        self._compiled_integration_patterns = {
            point_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for point_type, patterns in self.INTEGRATION_PATTERNS.items()
        }

    def validate(
        self,
        story: Dict[str, Any],
        knowledge_context: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Check for cross-module dependencies.

        Args:
            story: Story dictionary.
            knowledge_context: Retrieved knowledge chunks.

        Returns:
            ValidationResult with dependency findings.
        """
        result = self._create_result(
            passed=True,
            summary="Cross-dependency check completed"
        )

        story_text = self._extract_story_text(story)

        # Detect affected modules
        affected_modules = self._detect_modules(story_text)

        # Load dependency definitions
        dependencies = self._load_dependencies(knowledge_context)

        # Detect integration points
        integration_points = self._detect_integration_points(story_text)

        # Identify dependency risks
        risks = self._identify_risks(
            affected_modules,
            dependencies,
            story_text
        )

        # Populate result
        result.details["affected_modules"] = list(affected_modules)
        result.details["integration_points"] = [
            {"name": p.name, "type": p.point_type, "modules": p.modules_involved}
            for p in integration_points
        ]
        result.details["dependency_risks"] = [
            {
                "from": r.from_module,
                "to": r.to_module,
                "risk": r.risk_description,
                "mitigation": r.mitigation
            }
            for r in risks
        ]
        result.details["dependencies_loaded"] = len(dependencies)

        # Add findings
        if len(affected_modules) > 1:
            result.add_info(
                f"Multiple modules affected: {', '.join(affected_modules)}",
                suggestion="Consider cross-module testing"
            )

        for point in integration_points:
            result.add_info(
                f"Integration point: {point.point_type.upper()} - {point.name}",
                location=point.point_type
            )

        for risk in risks:
            result.add_warning(
                f"Dependency risk: {risk.from_module} -> {risk.to_module}",
                suggestion=risk.mitigation,
                risk=risk.risk_description
            )

        # Check for missing dependency handling
        self._check_missing_handling(
            affected_modules,
            story_text,
            result
        )

        # Calculate score
        risk_count = len(risks)
        result.score = max(0, 1 - (risk_count * 0.15))
        result.passed = risk_count <= 2
        result.summary = f"Found {len(affected_modules)} modules, {len(integration_points)} integration points, {len(risks)} risks"

        return result

    def _detect_modules(self, text: str) -> Set[str]:
        """Detect modules mentioned in the text."""
        text_lower = text.lower()
        detected = set()

        for module, keywords in self.MODULE_PATTERNS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected.add(module)
                    break

        return detected

    def _load_dependencies(
        self,
        knowledge_context: List[Dict[str, Any]]
    ) -> List[ModuleDependency]:
        """Load dependency definitions from knowledge."""
        dependencies = []

        for chunk in knowledge_context:
            metadata = chunk.get("metadata", {})
            content = chunk.get("content", "")

            if metadata.get("rule_type") != "cross_dependency":
                continue

            parsed = self._parse_dependencies(
                content,
                chunk.get("id", "unknown")
            )
            dependencies.extend(parsed)

        return dependencies

    def _parse_dependencies(
        self,
        content: str,
        source: str
    ) -> List[ModuleDependency]:
        """Parse dependencies from markdown content."""
        dependencies = []

        # Look for dependency definitions in tables
        # Format: | From | To | Type | Description |
        table_pattern = r'\|\s*(\w+)\s*\|\s*(\w+)\s*\|\s*(\w+)\s*\|\s*(.+?)\s*\|'
        matches = re.findall(table_pattern, content)

        for from_mod, to_mod, dep_type, desc in matches:
            if from_mod.lower() not in ['from', 'module', 'source']:
                dependencies.append(ModuleDependency(
                    from_module=from_mod.lower(),
                    to_module=to_mod.lower(),
                    dependency_type=dep_type.lower(),
                    description=desc,
                    risk_level="medium",
                    source=source
                ))

        # Also look for prose descriptions
        prose_pattern = r'(\w+)\s+depends?\s+on\s+(\w+)'
        prose_matches = re.findall(prose_pattern, content, re.IGNORECASE)

        for from_mod, to_mod in prose_matches:
            dependencies.append(ModuleDependency(
                from_module=from_mod.lower(),
                to_module=to_mod.lower(),
                dependency_type="unknown",
                description="Dependency detected from text",
                risk_level="medium",
                source=source
            ))

        return dependencies

    def _detect_integration_points(self, text: str) -> List[IntegrationPoint]:
        """Detect integration points in the story."""
        points = []
        text_lower = text.lower()

        for point_type, patterns in self._compiled_integration_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    # Find modules involved
                    modules = list(self._detect_modules(text))

                    points.append(IntegrationPoint(
                        name=matches[0] if matches else point_type,
                        point_type=point_type,
                        modules_involved=modules,
                        description=f"Detected {point_type} integration"
                    ))
                    break  # One per type

        return points

    def _identify_risks(
        self,
        affected_modules: Set[str],
        dependencies: List[ModuleDependency],
        story_text: str
    ) -> List[DependencyRisk]:
        """Identify dependency risks based on affected modules."""
        risks = []

        # Check known risky patterns
        for risky in self.RISKY_DEPENDENCIES:
            from_mod = risky["from"]
            to_mod = risky["to"]

            if from_mod in affected_modules and to_mod in affected_modules:
                risks.append(DependencyRisk(
                    from_module=from_mod,
                    to_module=to_mod,
                    risk_description=risky["risk"],
                    impact="Data consistency or timing issues",
                    mitigation=risky["mitigation"]
                ))

        # Check loaded dependencies
        for dep in dependencies:
            if dep.from_module in affected_modules and dep.to_module in affected_modules:
                if dep.risk_level in ["high", "critical"]:
                    risks.append(DependencyRisk(
                        from_module=dep.from_module,
                        to_module=dep.to_module,
                        risk_description=dep.description,
                        impact="See knowledge base",
                        mitigation="Review dependency documentation"
                    ))

        return risks

    def _check_missing_handling(
        self,
        affected_modules: Set[str],
        story_text: str,
        result: ValidationResult
    ):
        """Check for missing dependency handling."""
        story_lower = story_text.lower()

        # If multiple modules, check for transaction handling
        if len(affected_modules) > 1:
            transaction_keywords = [
                "transaction", "atomic", "rollback", "compensat"
            ]
            has_transaction_handling = any(
                kw in story_lower for kw in transaction_keywords
            )

            if not has_transaction_handling:
                result.add_info(
                    "Multi-module operation without explicit transaction handling",
                    suggestion="Consider defining rollback/compensation behavior"
                )

        # Check for error propagation
        if "notification" in affected_modules or "email" in story_lower:
            error_keywords = ["fail", "error", "retry"]
            has_error_handling = any(kw in story_lower for kw in error_keywords)

            if not has_error_handling:
                result.add_info(
                    "Notification integration without error handling",
                    suggestion="Define behavior when notification fails"
                )

        # Check for async handling
        if "payment" in story_lower or "payment_processing" in affected_modules:
            async_keywords = ["async", "queue", "background", "webhook", "callback"]
            has_async = any(kw in story_lower for kw in async_keywords)

            if not has_async:
                result.add_info(
                    "Payment operation appears synchronous",
                    suggestion="Consider async payment processing for reliability"
                )

    def check(self, story: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check dependencies (convenience method).

        Args:
            story: Story dictionary.

        Returns:
            Dictionary with check results.
        """
        result = self.validate(story, [])
        return result.to_dict()


if __name__ == "__main__":
    # Quick test
    checker = CrossDepChecker()

    test_story = {
        "title": "Subscription Upgrade with Payment",
        "description": """
        When a user upgrades their subscription plan:
        1. Calculate the prorated amount
        2. Process payment via payment gateway
        3. Update subscription status
        4. Send confirmation email
        5. Update user dashboard

        The system should handle payment failures gracefully.
        """,
        "acceptance_criteria": [
            "Given user has active subscription",
            "When they request upgrade",
            "Then payment should be processed",
            "And subscription should be updated",
            "And confirmation email should be sent"
        ]
    }

    result = checker.validate(test_story, [])
    print(result.format())
