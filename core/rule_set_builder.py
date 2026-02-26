"""
Rule Set Builder for Deterministic QA Brain

Builds the mandatory rule set for a story by orchestrating:
1. Direct rule matching from domains/intents
2. Transitive dependency expansion
3. Cross-module rule inclusion
4. State-specific rule filtering
5. Keyword-forced rule inclusion
"""

import logging
from typing import List, Set, Optional, Dict, Any

from models.rule import Rule, RiskLevel
from models.required_rule_set import RequiredRuleSet, CategorizedRule, RuleCategory
from core.rule_graph import RuleDependencyGraph
from rag.config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class RuleSetBuilder:
    """
    Builds the mandatory rule set for a story.

    Orchestrates:
    1. Direct rule matching from domains/intents/keywords
    2. Transitive dependency expansion via rule_graph
    3. Cross-module rule inclusion for multi-domain stories
    4. State-specific rule filtering for detected lifecycle states
    5. Keyword-forced rule inclusion via KEYWORD_RULE_MAPPING

    Example:
        builder = RuleSetBuilder(rule_graph)
        required = builder.build_required_set(
            story_text="Referral rewards should expire on plan switch...",
            pre_analysis=pre_analysis,
            detected_states=["ACTIVE"]
        )
        # Returns RequiredRuleSet with FIN-REF-012, DEP-EP-007, etc.
    """

    def __init__(self, rule_graph: RuleDependencyGraph):
        """
        Initialize the rule set builder.

        Args:
            rule_graph: The rule dependency graph to use for lookups
        """
        self.graph = rule_graph

    def build_required_set(
        self,
        story_text: str,
        pre_analysis: Any,  # PreAnalysisResult
        detected_states: Optional[List[str]] = None
    ) -> RequiredRuleSet:
        """
        Build complete required rule set for a story.

        Args:
            story_text: Combined story text (title + description)
            pre_analysis: Pre-analysis result with intents/domains/risks
            detected_states: Lifecycle states mentioned in story

        Returns:
            RequiredRuleSet with categorized mandatory rules
        """
        # Initialize result
        result = RequiredRuleSet(
            story_key=getattr(pre_analysis, 'story_key', ''),
            detected_domains=getattr(pre_analysis, 'detected_domains', []),
            detected_intents=[
                intent.get('intent', '') if isinstance(intent, dict) else str(intent)
                for intent in getattr(pre_analysis, 'detected_intents', [])
            ],
            detected_states=detected_states or [],
        )

        # Extract context
        domains = result.detected_domains
        intents = result.detected_intents
        keywords = getattr(pre_analysis, 'keywords', [])[:30]
        risk_flags = getattr(pre_analysis, 'risk_flags', [])

        # Step 1: Find direct rules from domains and intents
        direct_rules = self._find_direct_rules(domains, intents, keywords)
        result.direct_rules = direct_rules

        # Step 2: Expand transitive dependencies
        direct_ids = {cr.rule.rule_id for cr in direct_rules}
        dependency_rules = self._expand_dependencies(direct_ids)
        result.dependency_rules = dependency_rules

        # Step 3: Find cross-module rules
        cross_module_rules = self._find_cross_module_rules(domains)
        result.cross_module_rules = cross_module_rules

        # Step 4: Find state-specific rules
        if detected_states:
            state_rules = self._find_state_rules(detected_states)
            result.state_rules = state_rules

        # Step 5: Apply keyword forcing (KEYWORD_RULE_MAPPING)
        keyword_rules = self._apply_keyword_forcing(story_text, keywords)
        result.keyword_rules = keyword_rules

        # Log summary
        counts = result.count_by_category()
        logger.info(
            f"Built required rule set: {counts['total']} rules "
            f"(direct={counts['direct']}, dep={counts['dependency']}, "
            f"cross={counts['cross_module']}, state={counts['state']}, "
            f"keyword={counts['keyword']})"
        )

        if result.critical_rules:
            logger.info(
                f"Critical rules: {[cr.rule.rule_id for cr in result.critical_rules]}"
            )

        return result

    def _find_direct_rules(
        self,
        domains: List[str],
        intents: List[str],
        keywords: List[str]
    ) -> List[CategorizedRule]:
        """
        Find rules directly matching story context.

        Matches by:
        - Domain alignment
        - Keyword overlap
        - Risk level prioritization
        """
        result: List[CategorizedRule] = []
        seen_ids: Set[str] = set()

        # Get rules from relevant domains
        for domain in domains:
            domain_rules = self.graph.get_rules_by_domain(domain)
            for rule in domain_rules:
                if rule.rule_id not in seen_ids:
                    # Check if rule keywords match
                    if rule.matches_keywords(' '.join(keywords), min_matches=1):
                        result.append(CategorizedRule(
                            rule=rule,
                            category=RuleCategory.DIRECT,
                            reason=f"Domain match: {domain}, keywords aligned"
                        ))
                        seen_ids.add(rule.rule_id)

        # Get rules matching keywords (even if domain not detected)
        keyword_matches = self.graph.get_rules_by_keywords(keywords, min_matches=2)
        for rule in keyword_matches:
            if rule.rule_id not in seen_ids:
                result.append(CategorizedRule(
                    rule=rule,
                    category=RuleCategory.DIRECT,
                    reason=f"Keyword match: {len([k for k in keywords if k.lower() in rule.keywords])} keywords"
                ))
                seen_ids.add(rule.rule_id)

        # Prioritize by risk level (critical/high first)
        result.sort(key=lambda cr: (
            0 if cr.rule.risk_level == RiskLevel.CRITICAL else
            1 if cr.rule.risk_level == RiskLevel.HIGH else
            2 if cr.rule.risk_level == RiskLevel.MEDIUM else 3
        ))

        return result

    def _expand_dependencies(
        self,
        direct_rule_ids: Set[str]
    ) -> List[CategorizedRule]:
        """
        Expand transitive dependencies of direct rules.

        Uses the rule graph to find all rules that the direct rules
        depend on, recursively.
        """
        if not direct_rule_ids:
            return []

        result: List[CategorizedRule] = []

        # Get all transitive dependencies
        all_deps = self.graph.expand_dependencies(direct_rule_ids)

        # Filter out direct rules (we only want new dependencies)
        dependency_ids = all_deps - direct_rule_ids

        for dep_id in dependency_ids:
            rule = self.graph.get_rule(dep_id)
            if rule:
                # Find which direct rule triggered this dependency
                triggering_rules = []
                for direct_id in direct_rule_ids:
                    direct_deps = self.graph.expand_dependencies({direct_id})
                    if dep_id in direct_deps:
                        triggering_rules.append(direct_id)

                result.append(CategorizedRule(
                    rule=rule,
                    category=RuleCategory.DEPENDENCY,
                    reason=f"Required by: {', '.join(triggering_rules[:3])}"
                ))

        # Sort by risk level
        result.sort(key=lambda cr: cr.rule.risk_level, reverse=True)

        return result

    def _find_cross_module_rules(
        self,
        domains: List[str]
    ) -> List[CategorizedRule]:
        """
        Find rules spanning multiple affected domains.

        These are rules that coordinate behavior across modules
        and are critical for cross-cutting concerns.
        """
        if len(domains) < 2:
            return []

        result: List[CategorizedRule] = []
        seen_ids: Set[str] = set()

        # Get cross-domain rules
        cross_rules = self.graph.get_cross_domain_rules(domains)

        for rule in cross_rules:
            if rule.rule_id not in seen_ids:
                # Check how many domains this rule impacts
                impacted_domains = [
                    d for d in domains
                    if d.lower() in [i.lower() for i in rule.impacts] or
                    d.lower() == rule.domain.lower()
                ]

                if len(impacted_domains) >= 2:
                    result.append(CategorizedRule(
                        rule=rule,
                        category=RuleCategory.CROSS_MODULE,
                        reason=f"Spans domains: {', '.join(impacted_domains)}"
                    ))
                    seen_ids.add(rule.rule_id)

        return result

    def _find_state_rules(
        self,
        states: List[str]
    ) -> List[CategorizedRule]:
        """
        Find rules applicable to detected lifecycle states.

        Args:
            states: List of detected lifecycle states (e.g., ["ACTIVE", "PENDING"])

        Returns:
            List of rules that apply to these states
        """
        if not states:
            return []

        result: List[CategorizedRule] = []
        seen_ids: Set[str] = set()

        state_rules = self.graph.get_rules_for_states(states)

        for rule in state_rules:
            # Only include if rule has explicit state restrictions
            if rule.lifecycle_states and rule.rule_id not in seen_ids:
                matching_states = [
                    s for s in states
                    if s.upper() in [ls.upper() for ls in rule.lifecycle_states]
                ]

                if matching_states:
                    result.append(CategorizedRule(
                        rule=rule,
                        category=RuleCategory.STATE,
                        reason=f"Applies to states: {', '.join(matching_states)}"
                    ))
                    seen_ids.add(rule.rule_id)

        return result

    def _apply_keyword_forcing(
        self,
        story_text: str,
        keywords: List[str]
    ) -> List[CategorizedRule]:
        """
        Apply KEYWORD_RULE_MAPPING to force-include critical rules.

        Uses config.KEYWORD_RULE_MAPPING patterns to ensure
        rules like FIN-REF-012 are included when keywords match.

        This is the key mechanism for grounding enforcement.
        """
        result: List[CategorizedRule] = []
        seen_ids: Set[str] = set()

        # Get keyword-rule mapping from config
        if not hasattr(DEFAULT_CONFIG, 'KEYWORD_RULE_MAPPING'):
            return result

        keyword_mapping = DEFAULT_CONFIG.KEYWORD_RULE_MAPPING

        # Combine story text and keywords for matching
        all_text = (story_text + ' ' + ' '.join(keywords)).lower()

        for mapping_name, mapping_config in keyword_mapping.items():
            if not isinstance(mapping_config, dict):
                continue

            map_keywords = mapping_config.get('keywords', [])
            min_matches = mapping_config.get('min_matches', 2)
            forced_rule_ids = mapping_config.get('rules', [])

            # Count keyword matches
            match_count = sum(
                1 for kw in map_keywords
                if kw.lower() in all_text
            )

            if match_count >= min_matches:
                # Force include these rules
                matched_keywords = [
                    kw for kw in map_keywords
                    if kw.lower() in all_text
                ]

                for rule_id in forced_rule_ids:
                    if rule_id in seen_ids:
                        continue

                    rule = self.graph.get_rule(rule_id)
                    if rule:
                        result.append(CategorizedRule(
                            rule=rule,
                            category=RuleCategory.KEYWORD,
                            reason=f"Keyword forcing ({mapping_name}): matched '{', '.join(matched_keywords[:3])}'"
                        ))
                        seen_ids.add(rule_id)

                        logger.debug(
                            f"Keyword forcing activated: {mapping_name} -> {rule_id}"
                        )
                    else:
                        logger.warning(
                            f"Keyword mapping references unknown rule: {rule_id}"
                        )

        return result

    def build_minimal_set(
        self,
        story_text: str,
        domains: List[str],
        keywords: List[str]
    ) -> RequiredRuleSet:
        """
        Build minimal required rule set (direct + keyword only).

        Faster version for cases where full expansion is not needed.
        """
        result = RequiredRuleSet(
            detected_domains=domains,
            detected_intents=[],
            detected_states=[],
        )

        # Direct rules
        result.direct_rules = self._find_direct_rules(domains, [], keywords)

        # Keyword forcing
        result.keyword_rules = self._apply_keyword_forcing(story_text, keywords)

        return result

    def get_mandatory_rules_for_domain(
        self,
        domain: str
    ) -> List[Rule]:
        """
        Get all mandatory (critical/high) rules for a domain.

        Useful for understanding domain requirements.
        """
        domain_rules = self.graph.get_rules_by_domain(domain)
        return [
            rule for rule in domain_rules
            if rule.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        ]
