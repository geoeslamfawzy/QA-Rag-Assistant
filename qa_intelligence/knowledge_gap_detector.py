"""
Knowledge Gap Detector for Deterministic QA Brain v2.0

Detects when the knowledge base lacks coverage:
1. Story keywords have no matching rules
2. Domain has insufficient rule coverage
3. New concepts appear without rules

All detection is deterministic - no randomness or probabilistic sampling.
If uncertain, marks low confidence (never guesses).
"""

from typing import List, Dict, Set, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from models.required_rule_set import RequiredRuleSet
    from rag.story_pre_analyzer import PreAnalysisResult
    from core.rule_graph import RuleDependencyGraph


@dataclass
class KnowledgeGap:
    """A single knowledge gap."""
    gap_type: str                        # "missing_domain", "missing_concept", "weak_coverage"
    description: str
    keywords_without_rules: List[str] = field(default_factory=list)
    suggested_rule_topics: List[str] = field(default_factory=list)
    severity: str = "medium"             # Based on story risk level
    confidence: float = 1.0              # Confidence in gap detection

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "gap_type": self.gap_type,
            "description": self.description,
            "keywords_without_rules": self.keywords_without_rules,
            "suggested_rule_topics": self.suggested_rule_topics,
            "severity": self.severity,
            "confidence": self.confidence,
        }


@dataclass
class KnowledgeGapReport:
    """Complete knowledge gap analysis."""
    has_gaps: bool
    coverage_confidence: float           # 0-1, how confident we are in KB coverage
    gaps: List[KnowledgeGap] = field(default_factory=list)
    uncovered_keywords: List[str] = field(default_factory=list)
    uncovered_domains: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def is_knowledge_sufficient(self) -> bool:
        """Check if knowledge base is sufficient for this story."""
        return self.coverage_confidence >= 0.7 and not self.has_critical_gaps()

    def has_critical_gaps(self) -> bool:
        """Check if any gap is critical severity."""
        return any(gap.severity == "critical" for gap in self.gaps)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "has_gaps": self.has_gaps,
            "coverage_confidence": self.coverage_confidence,
            "gaps": [gap.to_dict() for gap in self.gaps],
            "uncovered_keywords": self.uncovered_keywords,
            "uncovered_domains": self.uncovered_domains,
            "recommendations": self.recommendations,
            "is_sufficient": self.is_knowledge_sufficient(),
            "has_critical_gaps": self.has_critical_gaps(),
        }

    def to_markdown(self) -> str:
        """Format as markdown."""
        lines = [
            "# Knowledge Gap Report",
            "",
            f"**Coverage Confidence:** {self.coverage_confidence:.0%}",
            f"**Has Gaps:** {'Yes' if self.has_gaps else 'No'}",
            "",
        ]

        if self.has_critical_gaps():
            lines.append("**WARNING: CRITICAL KNOWLEDGE GAPS DETECTED**")
            lines.append("")

        if self.uncovered_keywords:
            lines.append("## Uncovered Keywords")
            for kw in self.uncovered_keywords[:20]:
                lines.append(f"- {kw}")
            lines.append("")

        if self.uncovered_domains:
            lines.append("## Uncovered Domains")
            for domain in self.uncovered_domains:
                lines.append(f"- {domain}")
            lines.append("")

        if self.recommendations:
            lines.append("## Recommendations")
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        if self.gaps:
            lines.append("## Detailed Gaps")
            for gap in self.gaps:
                lines.append(f"\n### {gap.gap_type.replace('_', ' ').title()}")
                lines.append(f"**Severity:** {gap.severity.upper()}")
                lines.append(f"**Description:** {gap.description}")
                if gap.suggested_rule_topics:
                    lines.append("**Suggested Topics:**")
                    for topic in gap.suggested_rule_topics[:5]:
                        lines.append(f"  - {topic}")

        return "\n".join(lines)

    @classmethod
    def no_gaps(cls) -> "KnowledgeGapReport":
        """Create a report indicating no gaps."""
        return cls(
            has_gaps=False,
            coverage_confidence=1.0,
            gaps=[],
            uncovered_keywords=[],
            uncovered_domains=[],
            recommendations=["Knowledge base coverage is adequate"],
        )


class KnowledgeGapDetector:
    """
    Detects gaps in knowledge base coverage.

    Uses deterministic analysis:
    1. Keyword coverage analysis
    2. Domain coverage check
    3. Concept-to-rule mapping validation

    If domain detected but no matching rules found:
    - knowledge_gap_detected = True
    - confidence_in_kb = calculated float

    NEVER silently passes - always reports gaps explicitly.
    """

    def __init__(self, rule_graph: Optional["RuleDependencyGraph"] = None):
        """
        Initialize the knowledge gap detector.

        Args:
            rule_graph: Rule dependency graph for coverage analysis
        """
        self.graph = rule_graph
        self._kb_keywords: Set[str] = set()
        self._kb_domains: Set[str] = set()

        if rule_graph:
            self._build_keyword_index()

    def _build_keyword_index(self) -> None:
        """Build index of all keywords in knowledge base."""
        if not self.graph:
            return

        for rule in self.graph.all_rules():
            # Add keywords
            self._kb_keywords.update(kw.lower() for kw in rule.keywords)

            # Add domain
            if rule.domain:
                self._kb_domains.add(rule.domain.lower())

            # Add module as pseudo-domain
            if rule.module:
                self._kb_domains.add(rule.module.lower())

    def detect(
        self,
        pre_analysis: "PreAnalysisResult",
        required_rules: "RequiredRuleSet",
        story_text: str
    ) -> KnowledgeGapReport:
        """
        Detect knowledge base gaps for this story.

        Args:
            pre_analysis: Story pre-analysis result
            required_rules: Required rule set
            story_text: Full story text

        Returns:
            KnowledgeGapReport with gap details
        """
        gaps: List[KnowledgeGap] = []

        # Get keywords and domains from pre_analysis
        story_keywords = getattr(pre_analysis, 'keywords', [])
        story_domains = getattr(pre_analysis, 'detected_domains', [])

        # Step 1: Find uncovered keywords
        uncovered_keywords = self._find_uncovered_keywords(story_keywords)

        if uncovered_keywords:
            gaps.append(KnowledgeGap(
                gap_type="missing_concept",
                description=f"Keywords without matching rules: {', '.join(uncovered_keywords[:10])}",
                keywords_without_rules=uncovered_keywords,
                suggested_rule_topics=[f"Add rules covering: {kw}" for kw in uncovered_keywords[:5]],
                severity="high" if len(uncovered_keywords) > 5 else "medium",
                confidence=0.85,
            ))

        # Step 2: Check domain coverage
        uncovered_domains = self._find_uncovered_domains(story_domains)

        if uncovered_domains:
            gaps.append(KnowledgeGap(
                gap_type="missing_domain",
                description=f"Domains without rules: {', '.join(uncovered_domains)}",
                suggested_rule_topics=[f"Add rules for domain: {d}" for d in uncovered_domains],
                severity="critical",
                confidence=0.95,
            ))

        # Step 3: Check rule coverage depth
        coverage_gap = self._check_coverage_depth(required_rules)
        if coverage_gap:
            gaps.append(coverage_gap)

        # Step 4: Check for concept gaps in story text
        concept_gaps = self._check_concept_gaps(story_text, story_keywords)
        gaps.extend(concept_gaps)

        # Calculate confidence
        coverage_confidence = self._calculate_confidence(
            story_keywords,
            uncovered_keywords,
            required_rules
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(gaps, coverage_confidence)

        return KnowledgeGapReport(
            has_gaps=len(gaps) > 0,
            coverage_confidence=coverage_confidence,
            gaps=gaps,
            uncovered_keywords=uncovered_keywords,
            uncovered_domains=uncovered_domains,
            recommendations=recommendations,
        )

    def _find_uncovered_keywords(
        self,
        story_keywords: List[str]
    ) -> List[str]:
        """Find keywords not covered by any rule."""
        uncovered = []

        for keyword in story_keywords:
            kw_lower = keyword.lower()

            # Skip very short keywords
            if len(kw_lower) < 3:
                continue

            # Check exact match
            if kw_lower in self._kb_keywords:
                continue

            # Check partial matches (keyword in KB keyword or vice versa)
            has_partial = any(
                kw_lower in kb_kw or kb_kw in kw_lower
                for kb_kw in self._kb_keywords
                if len(kb_kw) >= 3
            )

            if not has_partial:
                uncovered.append(keyword)

        return uncovered

    def _find_uncovered_domains(
        self,
        story_domains: List[str]
    ) -> List[str]:
        """Find domains not covered in knowledge base."""
        uncovered = []

        for domain in story_domains:
            domain_lower = domain.lower()

            # Check exact match
            if domain_lower in self._kb_domains:
                continue

            # Check partial matches
            has_partial = any(
                domain_lower in kb_dom or kb_dom in domain_lower
                for kb_dom in self._kb_domains
            )

            if not has_partial:
                uncovered.append(domain)

        return uncovered

    def _check_coverage_depth(
        self,
        required_rules: "RequiredRuleSet"
    ) -> Optional[KnowledgeGap]:
        """Check if required rules have sufficient depth."""
        # Check if rule set is empty
        if not required_rules or not hasattr(required_rules, 'all_rules'):
            return KnowledgeGap(
                gap_type="weak_coverage",
                description="No rules match this story - knowledge base may be incomplete",
                severity="critical",
                confidence=0.9,
            )

        all_rules = list(required_rules.all_rules)

        if len(all_rules) == 0:
            return KnowledgeGap(
                gap_type="weak_coverage",
                description="No applicable rules found for this story",
                severity="critical",
                confidence=0.9,
            )

        # Check if we have too few rules
        if len(all_rules) < 3:
            return KnowledgeGap(
                gap_type="weak_coverage",
                description=f"Only {len(all_rules)} rules found - coverage may be insufficient",
                severity="high",
                confidence=0.8,
            )

        return None

    def _check_concept_gaps(
        self,
        story_text: str,
        story_keywords: List[str]
    ) -> List[KnowledgeGap]:
        """Check for high-level concept gaps."""
        gaps = []
        story_lower = story_text.lower()

        # Important business concepts that should have rules
        important_concepts = {
            "payment": ["payment", "pay", "charge", "billing", "invoice"],
            "authentication": ["login", "auth", "password", "credential", "session"],
            "authorization": ["permission", "role", "access", "privilege", "admin"],
            "data_integrity": ["save", "delete", "update", "modify", "create"],
            "state_management": ["status", "state", "lifecycle", "transition", "workflow"],
        }

        for concept, keywords in important_concepts.items():
            # Check if concept appears in story
            concept_mentioned = any(kw in story_lower for kw in keywords)

            if concept_mentioned:
                # Check if KB has rules for this concept
                concept_covered = any(
                    any(kw in kb_kw for kw in keywords)
                    for kb_kw in self._kb_keywords
                )

                if not concept_covered:
                    gaps.append(KnowledgeGap(
                        gap_type="missing_concept",
                        description=f"Story involves '{concept}' but KB may lack coverage",
                        keywords_without_rules=keywords[:3],
                        suggested_rule_topics=[f"Add {concept} rules"],
                        severity="high" if concept in ["payment", "authentication", "authorization"] else "medium",
                        confidence=0.7,  # Lower confidence - it's inference
                    ))

        return gaps

    def _calculate_confidence(
        self,
        all_keywords: List[str],
        uncovered: List[str],
        required_rules: "RequiredRuleSet"
    ) -> float:
        """Calculate confidence in knowledge base coverage."""
        if not all_keywords:
            return 0.5  # Uncertain

        # Keyword coverage factor
        keyword_coverage = 1.0 - (len(uncovered) / max(len(all_keywords), 1))

        # Rule count factor
        rule_count = 0
        if required_rules and hasattr(required_rules, 'all_rules'):
            rule_count = len(list(required_rules.all_rules))

        rule_factor = min(1.0, rule_count / 5)  # Expect at least 5 rules

        # Weighted combination
        confidence = (keyword_coverage * 0.6) + (rule_factor * 0.4)

        return max(0.0, min(1.0, confidence))

    def _generate_recommendations(
        self,
        gaps: List[KnowledgeGap],
        confidence: float
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if not gaps and confidence >= 0.8:
            recommendations.append("Knowledge base coverage is adequate for this story")
            return recommendations

        for gap in gaps:
            if gap.gap_type == "missing_domain":
                recommendations.append(
                    f"ACTION: Add rules to knowledge-base for domain(s): {gap.description}"
                )
            elif gap.gap_type == "missing_concept":
                if gap.keywords_without_rules:
                    keywords_str = ', '.join(gap.keywords_without_rules[:5])
                    recommendations.append(
                        f"ACTION: Review keywords [{keywords_str}] and add relevant rules"
                    )
            elif gap.gap_type == "weak_coverage":
                recommendations.append(
                    f"ACTION: Expand knowledge base - {gap.description}"
                )

        if confidence < 0.5:
            recommendations.append(
                "WARNING: Low confidence in KB coverage - manual review recommended"
            )

        return recommendations if recommendations else ["No specific actions required"]
