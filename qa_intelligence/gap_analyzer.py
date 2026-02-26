"""
Gap Analyzer for Deterministic QA Brain v2.0

Detects gaps in test coverage through:
1. Rule coverage analysis (required vs retrieved)
2. Boundary condition enumeration
3. State transition completeness
4. Cross-module dependency tracking

All analysis is deterministic - no randomness or probabilistic sampling.
"""

from typing import List, Dict, Set, Optional, TYPE_CHECKING

from models.gap import GapReport, GapItem, GapCategory, RegressionRisk

if TYPE_CHECKING:
    from models.required_rule_set import RequiredRuleSet
    from validators.coverage_validator import CoverageResult
    from core.rule_graph import RuleDependencyGraph


class GapAnalyzer:
    """
    Deterministic gap analysis engine.

    Identifies:
    1. Missing rule coverage
    2. Untested boundary conditions
    3. State transition gaps
    4. Cross-module integration gaps
    5. Regression risk areas

    No randomness - same input always produces same output.
    """

    # Boundary keywords for detection
    BOUNDARY_KEYWORDS = [
        "limit", "maximum", "minimum", "threshold", "cap",
        "ceiling", "floor", "range", "bound", "quota"
    ]

    # Security keywords for security gap detection
    SECURITY_KEYWORDS = [
        "permission", "access", "authorize", "role", "privilege",
        "authentication", "admin", "security", "password", "token"
    ]

    def __init__(self, rule_graph: Optional["RuleDependencyGraph"] = None):
        """
        Initialize the gap analyzer.

        Args:
            rule_graph: Optional rule dependency graph for advanced analysis
        """
        self.graph = rule_graph

    def analyze(
        self,
        required_rules: "RequiredRuleSet",
        coverage_result: "CoverageResult",
        story_text: str
    ) -> GapReport:
        """
        Perform deterministic gap analysis.

        Args:
            required_rules: Complete required rule set
            coverage_result: Coverage validation result
            story_text: Story text for boundary detection

        Returns:
            GapReport with all detected gaps
        """
        items: List[GapItem] = []

        # Step 1: Identify missing rule coverage
        items.extend(self._analyze_missing_rules(required_rules, coverage_result))

        # Step 2: Identify boundary gaps
        items.extend(self._analyze_boundary_gaps(required_rules, story_text))

        # Step 3: Identify state transition gaps
        items.extend(self._analyze_state_gaps(required_rules))

        # Step 4: Identify cross-module gaps
        items.extend(self._analyze_cross_module_gaps(required_rules))

        # Step 5: Identify security gaps
        items.extend(self._analyze_security_gaps(required_rules, story_text))

        # Step 6: Identify regression risks
        regression_areas = self._identify_regression_risks(required_rules)

        # Determine overall regression risk
        regression_risk = self._determine_regression_risk(items, regression_areas)

        # Calculate gap score
        gap_score = self._calculate_gap_score(coverage_result, items)

        # Get all cross-module impacts
        cross_module_impacts = self._get_cross_module_impacts(required_rules)

        return GapReport(
            gap_score=gap_score,
            items=items,
            missing_rule_ids=list(coverage_result.missing_rules) if hasattr(coverage_result, 'missing_rules') else [],
            regression_risk=regression_risk,
            regression_risk_areas=regression_areas,
            cross_module_impacts=cross_module_impacts,
            coverage_by_rule_type=getattr(coverage_result, 'coverage_by_category', {}),
        )

    def _analyze_missing_rules(
        self,
        required_rules: "RequiredRuleSet",
        coverage_result: "CoverageResult"
    ) -> List[GapItem]:
        """Identify gaps from missing rule coverage."""
        items = []

        # Get missing rules from coverage result
        missing_critical = getattr(coverage_result, 'missing_critical', [])
        missing_high_risk = getattr(coverage_result, 'missing_high_risk', [])
        missing_rules = getattr(coverage_result, 'missing_rules', [])

        # Critical missing rules
        for rule_id in missing_critical:
            rule = self._get_rule(rule_id, required_rules)
            if rule:
                items.append(GapItem(
                    category=GapCategory.MISSING_RULE,
                    description=f"CRITICAL rule {rule_id} not covered: {rule.description[:80]}",
                    missing_rule_ids=[rule_id],
                    affected_modules=list(rule.impacts) if rule.impacts else [],
                    suggested_test=f"Add test case for: {rule.validation[:100] if rule.validation else rule.description[:100]}",
                    risk_level="critical",
                    confidence=1.0,
                ))

        # High-risk missing rules
        for rule_id in missing_high_risk:
            if rule_id in missing_critical:
                continue  # Already added
            rule = self._get_rule(rule_id, required_rules)
            if rule:
                items.append(GapItem(
                    category=GapCategory.MISSING_RULE,
                    description=f"HIGH-RISK rule {rule_id} not covered: {rule.description[:60]}",
                    missing_rule_ids=[rule_id],
                    affected_modules=list(rule.impacts) if rule.impacts else [],
                    suggested_test=f"Add high-risk test for: {rule.rule_id}",
                    risk_level="high",
                    confidence=1.0,
                ))

        return items

    def _analyze_boundary_gaps(
        self,
        required_rules: "RequiredRuleSet",
        story_text: str
    ) -> List[GapItem]:
        """Identify boundary conditions that need testing."""
        items = []

        for cat_rule in required_rules.all_rules:
            rule = cat_rule.rule
            rule_text = (rule.description + " " + rule.validation + " " + rule.condition).lower()

            for keyword in self.BOUNDARY_KEYWORDS:
                if keyword in rule_text:
                    items.append(GapItem(
                        category=GapCategory.BOUNDARY_GAP,
                        description=f"Boundary condition in {rule.rule_id}: '{keyword}' needs edge testing",
                        missing_rule_ids=[rule.rule_id],
                        affected_modules=[rule.module] if rule.module else [],
                        suggested_test=f"Test at {keyword} boundary: min, max, just-below, just-above for {rule.rule_id}",
                        risk_level=rule.risk_level.value,
                        confidence=0.9,
                    ))
                    break  # One gap per rule

        return items

    def _analyze_state_gaps(self, required_rules: "RequiredRuleSet") -> List[GapItem]:
        """Identify state transition gaps."""
        items = []

        # Collect all states from rules
        all_states: Set[str] = set()
        state_rule_count: Dict[str, int] = {}

        for cat_rule in required_rules.all_rules:
            rule = cat_rule.rule
            for state in rule.lifecycle_states:
                state_upper = state.upper()
                all_states.add(state_upper)
                state_rule_count[state_upper] = state_rule_count.get(state_upper, 0) + 1

        # Check for states with limited coverage
        for state, count in state_rule_count.items():
            if count < 2:  # Less than 2 rules = potential gap
                items.append(GapItem(
                    category=GapCategory.STATE_GAP,
                    description=f"State '{state}' has limited rule coverage ({count} rule(s))",
                    affected_modules=["state_machine"],
                    suggested_test=f"Add tests for all transitions involving '{state}' state",
                    risk_level="high",
                    confidence=0.85,
                ))

        return items

    def _analyze_cross_module_gaps(
        self,
        required_rules: "RequiredRuleSet"
    ) -> List[GapItem]:
        """Identify cross-module integration gaps."""
        items = []

        for cat_rule in required_rules.cross_module_rules:
            rule = cat_rule.rule
            if len(rule.impacts) >= 2:
                items.append(GapItem(
                    category=GapCategory.CROSS_MODULE_GAP,
                    description=f"Cross-module rule {rule.rule_id} affects: {', '.join(rule.impacts[:5])}",
                    missing_rule_ids=[rule.rule_id],
                    affected_modules=list(rule.impacts),
                    suggested_test=f"Integration test for {rule.rule_id} across {', '.join(rule.impacts[:3])}",
                    risk_level=rule.risk_level.value,
                    confidence=0.9,
                ))

        return items

    def _analyze_security_gaps(
        self,
        required_rules: "RequiredRuleSet",
        story_text: str
    ) -> List[GapItem]:
        """Identify security-related gaps."""
        items = []
        story_lower = story_text.lower()

        # Check if story involves security but rules don't cover it
        security_in_story = any(kw in story_lower for kw in self.SECURITY_KEYWORDS)

        if security_in_story:
            # Check if any rules cover security
            security_rules = []
            for cat_rule in required_rules.all_rules:
                rule = cat_rule.rule
                rule_text = (rule.description + " " + rule.validation).lower()
                if any(kw in rule_text for kw in self.SECURITY_KEYWORDS):
                    security_rules.append(rule.rule_id)

            if not security_rules:
                items.append(GapItem(
                    category=GapCategory.SECURITY_GAP,
                    description="Story involves security concepts but no security rules are covered",
                    affected_modules=["security"],
                    suggested_test="Add security tests for authentication/authorization",
                    risk_level="critical",
                    confidence=0.8,
                ))

        return items

    def _identify_regression_risks(
        self,
        required_rules: "RequiredRuleSet"
    ) -> List[str]:
        """Identify areas with regression risk."""
        risks = []

        for cat_rule in required_rules.all_rules:
            rule = cat_rule.rule
            if rule.depends_on:
                dep_count = len(rule.depends_on)
                risks.append(f"{rule.rule_id} (depends on {dep_count} rules)")

            if rule.impacts and len(rule.impacts) >= 2:
                risks.append(f"{rule.rule_id} (impacts {len(rule.impacts)} modules)")

        return risks[:20]  # Limit to 20

    def _determine_regression_risk(
        self,
        items: List[GapItem],
        regression_areas: List[str]
    ) -> RegressionRisk:
        """Determine overall regression risk level."""
        critical_count = sum(1 for i in items if i.risk_level == "critical")
        high_count = sum(1 for i in items if i.risk_level == "high")

        if critical_count >= 2 or (critical_count >= 1 and len(regression_areas) >= 5):
            return RegressionRisk.CRITICAL
        elif critical_count >= 1 or high_count >= 3:
            return RegressionRisk.HIGH
        elif high_count >= 1 or len(regression_areas) >= 3:
            return RegressionRisk.MEDIUM
        else:
            return RegressionRisk.LOW

    def _calculate_gap_score(
        self,
        coverage_result: "CoverageResult",
        items: List[GapItem]
    ) -> float:
        """
        Calculate deterministic gap score (inverse of coverage with penalties).

        Formula: coverage_percentage - (gap_penalties)
        """
        base_score = getattr(coverage_result, 'coverage_percentage', 0.5)

        # Penalty for each gap type
        penalties = {
            GapCategory.MISSING_RULE: 0.10,
            GapCategory.BOUNDARY_GAP: 0.05,
            GapCategory.STATE_GAP: 0.08,
            GapCategory.CROSS_MODULE_GAP: 0.07,
            GapCategory.ERROR_HANDLING_GAP: 0.06,
            GapCategory.SECURITY_GAP: 0.10,
            GapCategory.REGRESSION_RISK: 0.03,
        }

        total_penalty = sum(
            penalties.get(item.category, 0.02) for item in items
        )

        return max(0.0, min(1.0, base_score - total_penalty))

    def _get_cross_module_impacts(
        self,
        required_rules: "RequiredRuleSet"
    ) -> List[str]:
        """Get all cross-module impacts."""
        impacts: Set[str] = set()

        for cat_rule in required_rules.all_rules:
            rule = cat_rule.rule
            if rule.impacts:
                impacts.update(rule.impacts)

        return sorted(list(impacts))

    def _get_rule(
        self,
        rule_id: str,
        required_rules: "RequiredRuleSet"
    ):
        """Get rule by ID from required rules."""
        for cat_rule in required_rules.all_rules:
            if cat_rule.rule.rule_id == rule_id:
                return cat_rule.rule
        return None
