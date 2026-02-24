"""
Story Pre-Analyzer Module

Analyzes Jira stories to detect intents, classify domains,
and identify risk flags before retrieval.
"""

import re
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field

from .config import RAGConfig, DEFAULT_CONFIG


@dataclass
class IntentMatch:
    """A detected intent with confidence score."""
    intent: str
    confidence: float
    matched_patterns: List[str]
    text_matches: List[str]


@dataclass
class PreAnalysisResult:
    """Complete result of story pre-analysis."""
    detected_intents: List[IntentMatch]
    detected_domains: List[str]
    priority_rule_types: List[str]
    risk_flags: List[str]
    risk_level: str
    keywords: List[str]
    entities: Dict[str, List[str]]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "detected_intents": [
                {
                    "intent": m.intent,
                    "confidence": m.confidence,
                    "matched_patterns": m.matched_patterns
                }
                for m in self.detected_intents
            ],
            "detected_domains": self.detected_domains,
            "priority_rule_types": self.priority_rule_types,
            "risk_flags": self.risk_flags,
            "risk_level": self.risk_level,
            "keywords": self.keywords,
            "entities": self.entities
        }


class StoryPreAnalyzer:
    """
    Pre-analyzes stories to extract intents and context.

    Features:
    - Intent detection via pattern matching
    - Domain classification
    - Risk flag identification
    - Keyword extraction
    - Entity recognition (states, amounts, etc.)
    """

    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Initialize the story pre-analyzer.

        Args:
            config: RAG configuration. Uses default if not provided.
        """
        self.config = config or DEFAULT_CONFIG

        # Compile intent patterns for efficiency
        self._compiled_patterns = self._compile_patterns()

        # Additional domain keywords
        self._domain_keywords = {
            "user_management": [
                "user", "account", "profile", "registration", "login",
                "password", "authentication", "session", "logout"
            ],
            "subscription": [
                "subscription", "plan", "tier", "billing cycle", "renewal",
                "upgrade", "downgrade", "trial", "premium"
            ],
            "payment_processing": [
                "payment", "charge", "transaction", "card", "wallet",
                "balance", "credit", "debit", "payout"
            ],
            "invoicing": [
                "invoice", "receipt", "billing", "tax", "vat",
                "statement", "ledger"
            ],
            "referral_system": [
                "referral", "refer", "invite", "referrer", "referee",
                "bonus", "reward", "commission"
            ],
            "gift_cards": [
                "gift card", "voucher", "coupon", "promo", "redeem",
                "code", "discount"
            ],
            "notification": [
                "notification", "email", "sms", "push", "alert",
                "message", "notify"
            ],
            "reporting": [
                "report", "analytics", "dashboard", "metrics", "stats",
                "export", "csv"
            ]
        }

        # Risk indicators
        self._risk_indicators = {
            "financial_impact": [
                "payment", "charge", "refund", "balance", "credit",
                "debit", "money", "amount", "price", "cost", "fee"
            ],
            "state_transition": [
                "activate", "deactivate", "suspend", "terminate", "cancel",
                "status", "state", "transition", "lifecycle"
            ],
            "data_integrity": [
                "delete", "remove", "purge", "update", "modify",
                "change", "alter", "edit"
            ],
            "security": [
                "permission", "role", "access", "admin", "privilege",
                "authentication", "authorization", "token"
            ],
            "integration": [
                "api", "webhook", "sync", "integration", "external",
                "third-party", "callback"
            ]
        }

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for each intent."""
        compiled = {}

        for intent, patterns in self.config.INTENT_PATTERNS.items():
            compiled[intent] = [
                re.compile(
                    r'\b' + re.escape(pattern).replace(r'\ ', r'\s+') + r'\b',
                    re.IGNORECASE
                )
                for pattern in patterns
            ]

        return compiled

    def detect_intents(self, text: str) -> List[IntentMatch]:
        """
        Detect intents in the story text.

        Args:
            text: Story text (description + acceptance criteria).

        Returns:
            List of IntentMatch objects sorted by confidence.
        """
        intents = []
        text_lower = text.lower()

        for intent, patterns in self._compiled_patterns.items():
            matched_patterns = []
            text_matches = []

            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    matched_patterns.append(pattern.pattern)
                    text_matches.extend(matches)

            if matched_patterns:
                # Calculate confidence based on match count and diversity
                match_count = len(text_matches)
                pattern_diversity = len(set(text_matches))

                # Base confidence
                confidence = min(0.4 + (match_count * 0.1), 0.7)

                # Diversity bonus
                confidence += min(pattern_diversity * 0.1, 0.2)

                # Title mention bonus
                if intent.replace("_", " ") in text_lower[:200]:
                    confidence += 0.1

                confidence = min(confidence, 1.0)

                intents.append(IntentMatch(
                    intent=intent,
                    confidence=confidence,
                    matched_patterns=matched_patterns,
                    text_matches=list(set(text_matches))
                ))

        # Sort by confidence
        intents.sort(key=lambda x: x.confidence, reverse=True)

        return intents

    def classify_domains(self, text: str, detected_intents: List[IntentMatch]) -> List[str]:
        """
        Classify which domains/modules the story relates to.

        Args:
            text: Story text.
            detected_intents: Previously detected intents.

        Returns:
            List of domain names sorted by relevance.
        """
        domain_scores: Dict[str, float] = {}
        text_lower = text.lower()

        # Score based on intent mappings
        for intent_match in detected_intents:
            intent = intent_match.intent
            confidence = intent_match.confidence

            if intent in self.config.INTENT_TO_DOMAIN:
                for domain in self.config.INTENT_TO_DOMAIN[intent]:
                    current = domain_scores.get(domain, 0)
                    domain_scores[domain] = current + confidence

        # Score based on domain keywords
        for domain, keywords in self._domain_keywords.items():
            keyword_count = sum(
                1 for kw in keywords
                if kw.lower() in text_lower
            )

            if keyword_count > 0:
                score = min(keyword_count * 0.15, 0.6)
                current = domain_scores.get(domain, 0)
                domain_scores[domain] = current + score

        # Sort and filter
        sorted_domains = sorted(
            domain_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Return domains with score > 0.2
        return [domain for domain, score in sorted_domains if score > 0.2]

    def identify_risk_flags(
        self,
        text: str,
        detected_intents: List[IntentMatch]
    ) -> Tuple[List[str], str]:
        """
        Identify risk flags and determine overall risk level.

        Args:
            text: Story text.
            detected_intents: Previously detected intents.

        Returns:
            Tuple of (risk_flags list, overall risk_level).
        """
        risk_flags = []
        text_lower = text.lower()

        # Check risk indicators
        for risk_type, keywords in self._risk_indicators.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches >= 2:
                risk_flags.append(risk_type)

        # Add risks from intent-based risk levels
        for intent_match in detected_intents:
            intent = intent_match.intent
            if intent in self.config.INTENT_RISK_LEVELS:
                intent_risk = self.config.INTENT_RISK_LEVELS[intent]
                if intent_risk in ["critical", "high"] and intent_match.confidence > 0.5:
                    risk_flag = f"high_risk_intent:{intent}"
                    if risk_flag not in risk_flags:
                        risk_flags.append(risk_flag)

        # Determine overall risk level
        if "financial_impact" in risk_flags and "data_integrity" in risk_flags:
            risk_level = "critical"
        elif "financial_impact" in risk_flags or any("critical" in f for f in risk_flags):
            risk_level = "high"
        elif len(risk_flags) >= 2:
            risk_level = "high"
        elif risk_flags:
            risk_level = "medium"
        else:
            risk_level = "low"

        return risk_flags, risk_level

    def determine_priority_rule_types(
        self,
        detected_intents: List[IntentMatch],
        risk_flags: List[str]
    ) -> List[str]:
        """
        Determine which rule types should be prioritized in retrieval.

        Args:
            detected_intents: Detected intents.
            risk_flags: Identified risk flags.

        Returns:
            List of priority rule types.
        """
        priority_types = set()

        # Map intents to rule types
        intent_to_rule_types = {
            "plan_switch": ["state_machine", "financial_logic", "atomic_rule"],
            "referral": ["atomic_rule", "financial_logic"],
            "gift_card": ["atomic_rule", "financial_logic", "validation_rule"],
            "financial_update": ["financial_logic", "atomic_rule", "validation_rule"],
            "role_change": ["atomic_rule", "cross_dependency"],
            "lifecycle_change": ["state_machine", "atomic_rule"],
            "deletion": ["state_machine", "cross_dependency", "atomic_rule"],
            "activation": ["state_machine", "atomic_rule", "validation_rule"]
        }

        for intent_match in detected_intents:
            if intent_match.confidence > 0.4:
                rule_types = intent_to_rule_types.get(intent_match.intent, [])
                priority_types.update(rule_types)

        # Add based on risk flags
        if "state_transition" in risk_flags:
            priority_types.add("state_machine")

        if "financial_impact" in risk_flags:
            priority_types.add("financial_logic")

        if "integration" in risk_flags:
            priority_types.add("cross_dependency")

        # Always include atomic rules if nothing else
        if not priority_types:
            priority_types.add("atomic_rule")

        return list(priority_types)

    def extract_keywords(self, text: str, max_keywords: int = 30) -> List[str]:
        """
        Extract relevant keywords from story text.

        Args:
            text: Story text.
            max_keywords: Maximum number of keywords.

        Returns:
            List of keywords.
        """
        # Remove markdown formatting
        clean = re.sub(r'[#*`\[\](){}|]', '', text)
        clean = re.sub(r'https?://\S+', '', clean)
        clean = re.sub(r'\s+', ' ', clean)

        # Extract words (at least 3 characters)
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b', clean.lower())

        # Filter stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all',
            'can', 'had', 'her', 'was', 'one', 'our', 'out', 'has',
            'have', 'been', 'were', 'will', 'when', 'what', 'this',
            'that', 'with', 'from', 'they', 'their', 'which', 'there',
            'should', 'would', 'could', 'given', 'then', 'than', 'also'
        }

        words = [w for w in words if w not in stop_words]

        # Count occurrences
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(
            word_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [word for word, _ in sorted_words[:max_keywords]]

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from story text.

        Args:
            text: Story text.

        Returns:
            Dictionary of entity types to entity values.
        """
        entities = {
            "states": [],
            "amounts": [],
            "dates": [],
            "identifiers": [],
            "actions": []
        }

        # Extract states (capitalized status-like words)
        state_patterns = [
            r'\b(ACTIVE|INACTIVE|PENDING|SUSPENDED|CANCELLED|COMPLETED)\b',
            r'\bstatus[:\s]+["\']?(\w+)["\']?',
            r'\bstate[:\s]+["\']?(\w+)["\']?'
        ]

        for pattern in state_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities["states"].extend(matches)

        # Extract amounts (currency values)
        amount_pattern = r'[\$\u20ac\u00a3]?\d+(?:,\d{3})*(?:\.\d{2})?(?:\s*(?:USD|EUR|GBP|%|percent))?'
        amounts = re.findall(amount_pattern, text)
        entities["amounts"] = list(set(amounts))

        # Extract date-like patterns
        date_pattern = r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{2}[-/]\d{2}'
        dates = re.findall(date_pattern, text)
        entities["dates"] = list(set(dates))

        # Extract identifiers (IDs, keys)
        id_pattern = r'\b[A-Z]{2,5}-\d+\b|\b\w+_id\b|\bid_\w+\b'
        ids = re.findall(id_pattern, text, re.IGNORECASE)
        entities["identifiers"] = list(set(ids))

        # Extract action verbs
        action_words = [
            "create", "update", "delete", "remove", "add", "modify",
            "activate", "deactivate", "suspend", "cancel", "approve",
            "reject", "submit", "process", "validate", "verify"
        ]

        text_lower = text.lower()
        found_actions = [a for a in action_words if a in text_lower]
        entities["actions"] = found_actions

        # Clean up empty lists
        entities["states"] = list(set(s.upper() for s in entities["states"] if s))

        return entities

    def analyze(self, story: Dict) -> PreAnalysisResult:
        """
        Perform complete pre-analysis of a story.

        Args:
            story: Story dictionary with 'title', 'description', 'acceptance_criteria'.

        Returns:
            PreAnalysisResult with all analysis data.
        """
        # Build full text
        parts = []

        if story.get("title"):
            parts.append(story["title"])

        if story.get("description"):
            parts.append(story["description"])

        if story.get("acceptance_criteria"):
            ac = story["acceptance_criteria"]
            if isinstance(ac, list):
                parts.extend(ac)
            else:
                parts.append(str(ac))

        full_text = "\n\n".join(parts)

        # Detect intents
        detected_intents = self.detect_intents(full_text)

        # Classify domains
        detected_domains = self.classify_domains(full_text, detected_intents)

        # Identify risks
        risk_flags, risk_level = self.identify_risk_flags(full_text, detected_intents)

        # Determine priority rule types
        priority_rule_types = self.determine_priority_rule_types(
            detected_intents,
            risk_flags
        )

        # Extract keywords
        keywords = self.extract_keywords(full_text)

        # Extract entities
        entities = self.extract_entities(full_text)

        return PreAnalysisResult(
            detected_intents=detected_intents,
            detected_domains=detected_domains,
            priority_rule_types=priority_rule_types,
            risk_flags=risk_flags,
            risk_level=risk_level,
            keywords=keywords,
            entities=entities
        )

    def format_analysis(self, result: PreAnalysisResult) -> str:
        """
        Format analysis result for display.

        Args:
            result: Pre-analysis result.

        Returns:
            Formatted string.
        """
        lines = []
        lines.append("=" * 50)
        lines.append("STORY PRE-ANALYSIS")
        lines.append("=" * 50)

        # Intents
        lines.append("\nDETECTED INTENTS:")
        if result.detected_intents:
            for intent in result.detected_intents:
                lines.append(f"  - {intent.intent}: {intent.confidence:.0%}")
                lines.append(f"    Matches: {', '.join(intent.text_matches[:5])}")
        else:
            lines.append("  (none detected)")

        # Domains
        lines.append("\nDETECTED DOMAINS:")
        if result.detected_domains:
            for domain in result.detected_domains:
                lines.append(f"  - {domain}")
        else:
            lines.append("  (none detected)")

        # Priority rule types
        lines.append("\nPRIORITY RULE TYPES:")
        for rule_type in result.priority_rule_types:
            lines.append(f"  - {rule_type}")

        # Risk assessment
        lines.append(f"\nRISK LEVEL: {result.risk_level.upper()}")
        lines.append("RISK FLAGS:")
        if result.risk_flags:
            for flag in result.risk_flags:
                lines.append(f"  - {flag}")
        else:
            lines.append("  (none)")

        # Keywords
        lines.append(f"\nKEY TERMS ({len(result.keywords)}):")
        lines.append(f"  {', '.join(result.keywords[:15])}")

        # Entities
        lines.append("\nEXTRACTED ENTITIES:")
        for entity_type, values in result.entities.items():
            if values:
                lines.append(f"  {entity_type}: {', '.join(values[:5])}")

        lines.append("\n" + "=" * 50)

        return "\n".join(lines)


if __name__ == "__main__":
    # Quick test
    analyzer = StoryPreAnalyzer()

    test_story = {
        "title": "Implement subscription plan upgrade flow",
        "description": """
        As a user, I want to upgrade my subscription plan from Basic to Premium
        so that I can access more features.

        The system should:
        1. Allow users to select a new plan
        2. Calculate the prorated amount
        3. Process the payment
        4. Update the subscription status to the new plan
        5. Send confirmation email
        """,
        "acceptance_criteria": [
            "Given I am on the Basic plan",
            "When I select Premium plan and confirm",
            "Then my payment method should be charged the prorated amount",
            "And my subscription status should change to Premium"
        ]
    }

    result = analyzer.analyze(test_story)
    print(analyzer.format_analysis(result))
