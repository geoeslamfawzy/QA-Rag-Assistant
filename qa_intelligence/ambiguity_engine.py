"""
Ambiguity Engine for Deterministic QA Brain v2.0

Detects ambiguities in user stories using:
1. Pattern matching for vague language
2. Rule gap analysis (story mentions concept but no rule covers it)
3. State machine completeness checking
4. Boundary condition detection

All detection is deterministic - no randomness or probabilistic sampling.
"""

from typing import List, Dict, Set, Optional, TYPE_CHECKING
from dataclasses import dataclass
import re

from models.ambiguity import (
    AmbiguityReport,
    AmbiguityItem,
    AmbiguityCategory,
    AmbiguitySeverity,
)

if TYPE_CHECKING:
    from models.required_rule_set import RequiredRuleSet
    from core.rule_graph import RuleDependencyGraph


class AmbiguityEngine:
    """
    Deterministic ambiguity detection engine.

    Detects ambiguities through:
    1. VAGUE_PATTERNS: Regex patterns for vague language
    2. MISSING_BOUNDARY: Numeric concepts without limits
    3. UNDEFINED_STATE: State references without rules
    4. RULE_GAP: Story concepts not covered by rules

    No randomness - same input always produces same output.
    """

    # Deterministic pattern lists
    VAGUE_QUANTIFIER_PATTERNS = [
        (r'\b(some|few|many|several|various)\b', AmbiguitySeverity.MEDIUM, "vague quantifier"),
        (r'\b(appropriate|suitable|relevant|proper)\b', AmbiguitySeverity.HIGH, "subjective term"),
        (r'\b(etc\.?|and so on|and more|and others)\b', AmbiguitySeverity.HIGH, "open-ended list"),
        (r'\b(as needed|if necessary|when required|as appropriate)\b', AmbiguitySeverity.MEDIUM, "conditional phrase"),
        (r'\b(possibly|maybe|perhaps|might)\b', AmbiguitySeverity.MEDIUM, "uncertain language"),
    ]

    MISSING_BOUNDARY_PATTERNS = [
        (r'\b(limit|maximum|minimum|max|min)\b(?!.*\d)', AmbiguitySeverity.CRITICAL, "limit without value"),
        (r'\b(within|between)\b(?!.*\d)', AmbiguitySeverity.HIGH, "range without values"),
        (r'\b(up to|at least|more than|less than|at most)\b(?!.*\d)', AmbiguitySeverity.HIGH, "bound without value"),
        (r'\b(threshold|cap|ceiling|floor)\b(?!.*\d)', AmbiguitySeverity.HIGH, "threshold without value"),
    ]

    UNDEFINED_BEHAVIOR_PATTERNS = [
        (r'\b(should|might|could|may)\b(?!\s+not)', AmbiguitySeverity.MEDIUM, "weak requirement (use 'must')"),
        (r'\b(handle|manage|process)\s+(errors?|exceptions?|failures?)\b(?!.*\bthen\b)', AmbiguitySeverity.HIGH, "error handling without behavior"),
        (r'\b(invalid|error|failure|exception)\b(?!.*\bthen\b)(?!.*\bdisplay\b)(?!.*\bshow\b)', AmbiguitySeverity.CRITICAL, "error without handling"),
        (r'\b(otherwise|else)\b(?!.*\bthen\b)', AmbiguitySeverity.MEDIUM, "alternative without action"),
    ]

    MISSING_ACTOR_PATTERNS = [
        (r'^(the system|it)\s+(should|must|will)', AmbiguitySeverity.LOW, "generic actor"),
        (r'\b(someone|anyone|user)\s+(can|should|must)', AmbiguitySeverity.MEDIUM, "undefined actor"),
    ]

    CONFLICTING_REQUIREMENT_PATTERNS = [
        (r'\b(always|never)\b.*\b(sometimes|occasionally)\b', AmbiguitySeverity.CRITICAL, "conflicting frequency"),
        (r'\b(must|shall)\b.*\b(optional|may)\b', AmbiguitySeverity.HIGH, "conflicting obligation"),
    ]

    def __init__(self, rule_graph: Optional["RuleDependencyGraph"] = None):
        """
        Initialize the ambiguity engine.

        Args:
            rule_graph: Optional rule dependency graph for rule gap analysis
        """
        self.graph = rule_graph
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile all regex patterns for efficiency."""
        self._compiled_vague = [
            (re.compile(p, re.IGNORECASE), s, d)
            for p, s, d in self.VAGUE_QUANTIFIER_PATTERNS
        ]
        self._compiled_boundary = [
            (re.compile(p, re.IGNORECASE), s, d)
            for p, s, d in self.MISSING_BOUNDARY_PATTERNS
        ]
        self._compiled_undefined = [
            (re.compile(p, re.IGNORECASE), s, d)
            for p, s, d in self.UNDEFINED_BEHAVIOR_PATTERNS
        ]
        self._compiled_actor = [
            (re.compile(p, re.IGNORECASE | re.MULTILINE), s, d)
            for p, s, d in self.MISSING_ACTOR_PATTERNS
        ]
        self._compiled_conflict = [
            (re.compile(p, re.IGNORECASE), s, d)
            for p, s, d in self.CONFLICTING_REQUIREMENT_PATTERNS
        ]

    def analyze(
        self,
        story_text: str,
        required_rules: Optional["RequiredRuleSet"] = None,
        detected_states: Optional[List[str]] = None
    ) -> AmbiguityReport:
        """
        Perform deterministic ambiguity analysis.

        Args:
            story_text: Combined story text (title + description + AC)
            required_rules: The required rule set for gap analysis
            detected_states: Lifecycle states mentioned in story

        Returns:
            AmbiguityReport with all detected ambiguities
        """
        if not story_text:
            return AmbiguityReport.empty()

        items: List[AmbiguityItem] = []

        # Step 1: Detect vague quantifiers
        items.extend(self._detect_vague_quantifiers(story_text))

        # Step 2: Detect missing boundaries
        items.extend(self._detect_missing_boundaries(story_text))

        # Step 3: Detect undefined behaviors
        items.extend(self._detect_undefined_behaviors(story_text))

        # Step 4: Detect undefined actors
        items.extend(self._detect_undefined_actors(story_text))

        # Step 5: Detect conflicting requirements
        items.extend(self._detect_conflicts(story_text))

        # Step 6: Detect state gaps (if graph available)
        if self.graph and detected_states:
            items.extend(self._detect_state_gaps(story_text, detected_states))

        # Step 7: Detect rule coverage gaps (if required_rules available)
        if required_rules:
            items.extend(self._detect_rule_gaps(story_text, required_rules))

        # Calculate score (deterministic formula)
        score = self._calculate_ambiguity_score(items)

        # Determine overall severity (deterministic: highest found)
        overall_severity = self._determine_overall_severity(items)

        # Extract unique questions (maintain order)
        seen_questions: Set[str] = set()
        questions: List[str] = []
        for item in items:
            if item.clarification_question not in seen_questions:
                seen_questions.add(item.clarification_question)
                questions.append(item.clarification_question)

        # Extract unique categories
        categories = list(set(item.category for item in items))

        return AmbiguityReport(
            ambiguity_score=score,
            items=items,
            clarification_questions=questions,
            categories_detected=categories,
            overall_severity=overall_severity,
        )

    def _detect_vague_quantifiers(self, text: str) -> List[AmbiguityItem]:
        """Detect vague quantifier patterns."""
        items = []
        for pattern, severity, desc in self._compiled_vague:
            for match in pattern.finditer(text):
                # Get context around match
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].strip()

                items.append(AmbiguityItem(
                    category=AmbiguityCategory.VAGUE_QUANTIFIER,
                    severity=severity,
                    description=f"Vague quantifier '{match.group()}' ({desc})",
                    location=f"...{context}...",
                    clarification_question=f"What is the specific count or amount for '{match.group()}'?",
                    confidence=0.9,
                ))
        return items

    def _detect_missing_boundaries(self, text: str) -> List[AmbiguityItem]:
        """Detect concepts needing boundaries but lacking them."""
        items = []
        for pattern, severity, desc in self._compiled_boundary:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].strip()

                items.append(AmbiguityItem(
                    category=AmbiguityCategory.MISSING_BOUNDARY,
                    severity=severity,
                    description=f"Boundary term '{match.group()}' without specific value ({desc})",
                    location=f"...{context}...",
                    clarification_question=f"What is the specific numeric value for '{match.group()}'?",
                    confidence=0.95,
                ))
        return items

    def _detect_undefined_behaviors(self, text: str) -> List[AmbiguityItem]:
        """Detect undefined error/edge behaviors."""
        items = []
        for pattern, severity, desc in self._compiled_undefined:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].strip()

                items.append(AmbiguityItem(
                    category=AmbiguityCategory.UNDEFINED_BEHAVIOR,
                    severity=severity,
                    description=f"Potential undefined behavior: '{match.group()}' ({desc})",
                    location=f"...{context}...",
                    clarification_question=f"What should happen when '{match.group()}'?",
                    confidence=0.85,
                ))
        return items

    def _detect_undefined_actors(self, text: str) -> List[AmbiguityItem]:
        """Detect undefined or generic actors."""
        items = []
        for pattern, severity, desc in self._compiled_actor:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                context = text[start:end].strip()

                items.append(AmbiguityItem(
                    category=AmbiguityCategory.UNDEFINED_ACTOR,
                    severity=severity,
                    description=f"Undefined actor: '{match.group()}' ({desc})",
                    location=f"...{context}...",
                    clarification_question=f"Who specifically performs this action? What role?",
                    confidence=0.8,
                ))
        return items

    def _detect_conflicts(self, text: str) -> List[AmbiguityItem]:
        """Detect conflicting requirements."""
        items = []
        for pattern, severity, desc in self._compiled_conflict:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].strip()

                items.append(AmbiguityItem(
                    category=AmbiguityCategory.CONFLICTING_REQUIREMENT,
                    severity=severity,
                    description=f"Conflicting requirement detected ({desc})",
                    location=f"...{context}...",
                    clarification_question=f"Which requirement takes precedence? Please resolve the conflict.",
                    confidence=0.9,
                ))
        return items

    def _detect_state_gaps(
        self,
        text: str,
        detected_states: List[str]
    ) -> List[AmbiguityItem]:
        """Detect referenced states without rules."""
        items = []
        if not self.graph:
            return items

        text_upper = text.upper()

        # Get all states from rule graph
        available_states: Set[str] = set()
        for rule in self.graph.all_rules():
            available_states.update(s.upper() for s in rule.lifecycle_states)

        # Check detected states
        for state in detected_states:
            state_upper = state.upper()
            if state_upper not in available_states:
                items.append(AmbiguityItem(
                    category=AmbiguityCategory.MISSING_STATE,
                    severity=AmbiguitySeverity.HIGH,
                    description=f"State '{state}' referenced but no rules cover transitions",
                    location=f"Story references state: {state}",
                    clarification_question=f"What rules govern the '{state}' state transitions?",
                    confidence=0.85,
                ))

        return items

    def _detect_rule_gaps(
        self,
        text: str,
        required_rules: "RequiredRuleSet"
    ) -> List[AmbiguityItem]:
        """Detect concepts in story not covered by rules."""
        items = []

        # Check if critical rules have evidence in story
        for cat_rule in required_rules.critical_rules:
            rule = cat_rule.rule
            # Check if rule keywords appear in story
            has_evidence = rule.matches_keywords(text, min_matches=1)

            if not has_evidence:
                items.append(AmbiguityItem(
                    category=AmbiguityCategory.IMPLICIT_ASSUMPTION,
                    severity=AmbiguitySeverity.HIGH,
                    description=f"Critical rule {rule.rule_id} required but story lacks matching keywords",
                    location=f"Rule: {rule.description[:80]}...",
                    clarification_question=f"Does this story involve {rule.description}?",
                    violated_rule_ids=[rule.rule_id],
                    confidence=0.7,  # Lower confidence since it's inference
                ))

        return items

    def _calculate_ambiguity_score(self, items: List[AmbiguityItem]) -> float:
        """
        Calculate deterministic ambiguity score.

        Formula: weighted_severity_sum (capped at 1.0)
        - CRITICAL items: 0.25 each
        - HIGH items: 0.15 each
        - MEDIUM items: 0.08 each
        - LOW items: 0.03 each
        """
        if not items:
            return 0.0

        weights = {
            AmbiguitySeverity.CRITICAL: 0.25,
            AmbiguitySeverity.HIGH: 0.15,
            AmbiguitySeverity.MEDIUM: 0.08,
            AmbiguitySeverity.LOW: 0.03,
        }

        total_weight = sum(weights.get(item.severity, 0.05) for item in items)
        return min(1.0, total_weight)

    def _determine_overall_severity(
        self,
        items: List[AmbiguityItem]
    ) -> AmbiguitySeverity:
        """Deterministic: return highest severity found."""
        if not items:
            return AmbiguitySeverity.LOW

        severity_order = [
            AmbiguitySeverity.CRITICAL,
            AmbiguitySeverity.HIGH,
            AmbiguitySeverity.MEDIUM,
            AmbiguitySeverity.LOW,
        ]

        for severity in severity_order:
            if any(item.severity == severity for item in items):
                return severity

        return AmbiguitySeverity.LOW
