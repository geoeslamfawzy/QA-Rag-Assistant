"""
Rule Engine Module

Matches stories against atomic business rules from the knowledge base.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from .base_validator import BaseValidator, ValidationResult, Severity


@dataclass
class AtomicRule:
    """An atomic business rule."""
    rule_id: str
    name: str
    condition: str
    validation: str
    error_message: str
    priority: str  # high, medium, low
    module: str
    keywords: List[str] = field(default_factory=list)
    source: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "condition": self.condition,
            "validation": self.validation,
            "error_message": self.error_message,
            "priority": self.priority,
            "module": self.module,
            "keywords": self.keywords
        }


@dataclass
class RuleMatch:
    """A matched rule with relevance score."""
    rule: AtomicRule
    relevance: float
    matched_keywords: List[str]
    context_snippet: str


class RuleEngine(BaseValidator):
    """
    Matches stories against atomic business rules.

    Features:
    - Keyword-based rule matching
    - Relevance scoring
    - Coverage calculation
    - Critical rule identification
    - Gap analysis
    """

    # Priority weights for scoring
    PRIORITY_WEIGHTS = {
        "critical": 1.0,
        "high": 0.8,
        "medium": 0.5,
        "low": 0.3
    }

    def __init__(self):
        """Initialize the rule engine."""
        super().__init__("RuleEngine")

    def validate(
        self,
        story: Dict[str, Any],
        knowledge_context: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Match story against atomic rules.

        Args:
            story: Story dictionary.
            knowledge_context: Retrieved knowledge chunks.

        Returns:
            ValidationResult with rule matching findings.
        """
        result = self._create_result(
            passed=True,
            summary="Rule matching completed"
        )

        story_text = self._extract_story_text(story)

        # Load atomic rules from knowledge
        atomic_rules = self._load_atomic_rules(knowledge_context)

        if not atomic_rules:
            result.add_info(
                "No atomic rules found in knowledge context",
                suggestion="Add atomic rules to knowledge base for rule validation"
            )
            return result

        # Match rules against story
        matched_rules = self._match_rules(story_text, atomic_rules)

        # Calculate coverage
        coverage_score = self._calculate_coverage(
            matched_rules,
            atomic_rules,
            story_text
        )

        # Find unmatched critical rules
        unmatched_critical = self._find_unmatched_critical(
            matched_rules,
            atomic_rules,
            story_text
        )

        # Populate result
        result.details["total_rules"] = len(atomic_rules)
        result.details["matched_rules"] = len(matched_rules)
        result.details["coverage_score"] = coverage_score
        result.details["matched_rule_details"] = [
            {
                "rule_id": m.rule.rule_id,
                "name": m.rule.name,
                "relevance": m.relevance,
                "matched_keywords": m.matched_keywords
            }
            for m in matched_rules
        ]

        # Add findings
        if matched_rules:
            for match in matched_rules[:5]:  # Top 5
                result.add_info(
                    f"Matched rule: {match.rule.rule_id} - {match.rule.name}",
                    rule_id=match.rule.rule_id,
                    relevance=match.relevance
                )

        if unmatched_critical:
            for rule in unmatched_critical:
                result.add_warning(
                    f"Critical rule not covered: {rule.rule_id} - {rule.name}",
                    rule_id=rule.rule_id,
                    suggestion=f"Ensure story covers: {rule.condition}"
                )

        # Coverage warnings
        if coverage_score < 0.3:
            result.add_warning(
                f"Low rule coverage: {coverage_score:.0%}",
                suggestion="Story may be missing important business rules"
            )
        elif coverage_score < 0.5:
            result.add_info(
                f"Moderate rule coverage: {coverage_score:.0%}"
            )

        # Calculate final score
        result.score = coverage_score
        result.passed = coverage_score >= 0.3 and len(unmatched_critical) == 0
        result.summary = f"Matched {len(matched_rules)}/{len(atomic_rules)} rules (coverage: {coverage_score:.0%})"

        return result

    def _load_atomic_rules(
        self,
        knowledge_context: List[Dict[str, Any]]
    ) -> List[AtomicRule]:
        """Load atomic rules from knowledge context."""
        rules = []

        for chunk in knowledge_context:
            metadata = chunk.get("metadata", {})
            content = chunk.get("content", "")

            if metadata.get("rule_type") != "atomic_rule":
                continue

            # Parse rules from content
            parsed_rules = self._parse_rules(
                content,
                metadata.get("module", "unknown"),
                chunk.get("id", "unknown")
            )
            rules.extend(parsed_rules)

        return rules

    def _parse_rules(
        self,
        content: str,
        module: str,
        source: str
    ) -> List[AtomicRule]:
        """Parse atomic rules from markdown content."""
        rules = []

        # Pattern for rule blocks
        # Looking for: ## RULE-XXX: Name
        rule_block_pattern = r'##\s*(RULE-\d+|[A-Z]+-\d+):\s*(.+?)(?=##\s*(?:RULE-|[A-Z]+-)\d+|$)'

        blocks = re.findall(rule_block_pattern, content, re.DOTALL | re.IGNORECASE)

        for rule_id, block_content in blocks:
            rule = self._parse_rule_block(
                rule_id.upper(),
                block_content,
                module,
                source
            )
            if rule:
                rules.append(rule)

        # Also try simpler format: RULE-XXX in tables or lists
        simple_pattern = r'(?:RULE|[A-Z]{2,5})-(\d+)[:\s]+(.+?)(?:\n|$)'
        simple_matches = re.findall(simple_pattern, content)

        for rule_num, description in simple_matches:
            # Avoid duplicates
            rule_id = f"RULE-{rule_num}"
            if not any(r.rule_id == rule_id for r in rules):
                rules.append(AtomicRule(
                    rule_id=rule_id,
                    name=description.strip()[:100],
                    condition="",
                    validation=description.strip(),
                    error_message="",
                    priority="medium",
                    module=module,
                    keywords=self._extract_keywords(description),
                    source=source
                ))

        return rules

    def _parse_rule_block(
        self,
        rule_id: str,
        content: str,
        module: str,
        source: str
    ) -> Optional[AtomicRule]:
        """Parse a single rule block."""
        lines = content.strip().split('\n')
        name = lines[0].strip() if lines else rule_id

        # Extract fields
        condition = ""
        validation = ""
        error_message = ""
        priority = "medium"

        content_lower = content.lower()

        # Extract condition
        cond_match = re.search(r'condition[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE)
        if cond_match:
            condition = cond_match.group(1).strip()

        # Extract validation
        val_match = re.search(r'validation[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE)
        if val_match:
            validation = val_match.group(1).strip()

        # Extract error message
        err_match = re.search(r'error[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE)
        if err_match:
            error_message = err_match.group(1).strip()

        # Extract priority
        if 'critical' in content_lower or 'high' in content_lower:
            priority = 'high'
        elif 'low' in content_lower:
            priority = 'low'

        # Use full content as validation if not extracted
        if not validation:
            validation = content[:500]

        keywords = self._extract_keywords(content)

        return AtomicRule(
            rule_id=rule_id,
            name=name,
            condition=condition,
            validation=validation,
            error_message=error_message,
            priority=priority,
            module=module,
            keywords=keywords,
            source=source
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Remove markdown
        clean = re.sub(r'[#*`\[\](){}|]', '', text)
        clean = clean.lower()

        # Extract words
        words = re.findall(r'\b[a-zA-Z]{4,}\b', clean)

        # Filter common words
        stop_words = {
            'this', 'that', 'with', 'from', 'have', 'been', 'will',
            'when', 'must', 'should', 'could', 'would', 'then',
            'given', 'condition', 'validation', 'error', 'rule'
        }

        keywords = [w for w in words if w not in stop_words]

        # Unique, sorted by frequency
        from collections import Counter
        counts = Counter(keywords)
        return [word for word, _ in counts.most_common(15)]

    def _match_rules(
        self,
        story_text: str,
        rules: List[AtomicRule]
    ) -> List[RuleMatch]:
        """Match rules against story text."""
        matches = []
        story_lower = story_text.lower()
        story_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', story_lower))

        for rule in rules:
            # Calculate keyword overlap
            rule_keywords = set(rule.keywords)
            matched_keywords = list(rule_keywords & story_words)

            if not matched_keywords:
                continue

            # Calculate relevance score
            keyword_coverage = len(matched_keywords) / max(len(rule_keywords), 1)

            # Priority boost
            priority_boost = self.PRIORITY_WEIGHTS.get(rule.priority, 0.5)

            # Calculate final relevance
            relevance = (keyword_coverage * 0.7) + (priority_boost * 0.3)

            # Only include if relevance is significant
            if relevance >= 0.2:
                # Find context snippet
                snippet = self._find_context_snippet(story_text, matched_keywords[0])

                matches.append(RuleMatch(
                    rule=rule,
                    relevance=relevance,
                    matched_keywords=matched_keywords,
                    context_snippet=snippet
                ))

        # Sort by relevance
        matches.sort(key=lambda x: x.relevance, reverse=True)

        return matches

    def _find_context_snippet(self, text: str, keyword: str, window: int = 100) -> str:
        """Find a context snippet around a keyword."""
        text_lower = text.lower()
        keyword_lower = keyword.lower()

        pos = text_lower.find(keyword_lower)
        if pos == -1:
            return ""

        start = max(0, pos - window // 2)
        end = min(len(text), pos + len(keyword) + window // 2)

        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    def _calculate_coverage(
        self,
        matched_rules: List[RuleMatch],
        all_rules: List[AtomicRule],
        story_text: str
    ) -> float:
        """Calculate rule coverage score."""
        if not all_rules:
            return 1.0

        # Weight by priority
        total_weight = sum(
            self.PRIORITY_WEIGHTS.get(r.priority, 0.5)
            for r in all_rules
        )

        matched_weight = sum(
            self.PRIORITY_WEIGHTS.get(m.rule.priority, 0.5) * m.relevance
            for m in matched_rules
        )

        return min(1.0, matched_weight / total_weight)

    def _find_unmatched_critical(
        self,
        matched_rules: List[RuleMatch],
        all_rules: List[AtomicRule],
        story_text: str
    ) -> List[AtomicRule]:
        """Find critical rules that should be matched but aren't."""
        matched_ids = {m.rule.rule_id for m in matched_rules}

        # Critical rules not matched
        critical_unmatched = [
            rule for rule in all_rules
            if rule.priority in ["critical", "high"]
            and rule.rule_id not in matched_ids
            and self._rule_should_apply(rule, story_text)
        ]

        return critical_unmatched

    def _rule_should_apply(self, rule: AtomicRule, story_text: str) -> bool:
        """Determine if a rule should apply to this story."""
        story_lower = story_text.lower()

        # Check if any keywords appear
        for keyword in rule.keywords[:5]:  # Top 5 keywords
            if keyword in story_lower:
                return True

        return False

    def execute(self, story: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute rule matching (convenience method).

        Args:
            story: Story dictionary.

        Returns:
            Dictionary with matching results.
        """
        # This would typically load knowledge context
        # For standalone use, returns empty result
        result = self.validate(story, [])
        return result.to_dict()


if __name__ == "__main__":
    # Quick test
    engine = RuleEngine()

    test_story = {
        "title": "User Registration with Email Verification",
        "description": """
        Implement user registration that requires:
        - Valid email format
        - Password minimum 8 characters
        - Email verification before activation
        - Terms acceptance
        """,
        "acceptance_criteria": [
            "Given valid registration data",
            "When user submits registration",
            "Then verification email should be sent",
            "And account should be pending until verified"
        ]
    }

    # Mock knowledge context with rules
    knowledge = [
        {
            "id": "atomic_rules/user_rules",
            "content": """
            ## RULE-001: Email Format Validation
            **Condition:** User provides email during registration
            **Validation:** Email must match valid email format
            **Error:** Invalid email format
            **Priority:** high

            ## RULE-002: Password Strength
            **Condition:** User sets password
            **Validation:** Password must be at least 8 characters
            **Error:** Password too weak
            **Priority:** high

            ## RULE-003: Terms Acceptance
            **Condition:** User registers
            **Validation:** User must accept terms of service
            **Error:** Terms not accepted
            **Priority:** critical
            """,
            "metadata": {"rule_type": "atomic_rule", "module": "user_management"}
        }
    ]

    result = engine.validate(test_story, knowledge)
    print(result.format())
