"""
Rule Dependency Graph for Deterministic QA Brain

Implements a directed graph of rule dependencies enabling:
- Transitive dependency expansion
- Cross-domain rule discovery
- Impact chain detection
- Topological ordering for validation
"""

import logging
from typing import Dict, List, Set, Optional, Iterator
from dataclasses import dataclass, field
from collections import defaultdict

from models.rule import Rule, RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class RuleNode:
    """
    Node in the rule dependency graph.

    Tracks both outgoing (depends_on) and incoming (depended_by) edges.
    """
    rule: Rule
    outgoing: Set[str] = field(default_factory=set)   # Rules this depends on
    incoming: Set[str] = field(default_factory=set)   # Rules that depend on this

    def add_dependency(self, rule_id: str) -> None:
        """Add outgoing dependency."""
        self.outgoing.add(rule_id)

    def add_dependent(self, rule_id: str) -> None:
        """Add incoming dependency (rule that depends on this)."""
        self.incoming.add(rule_id)


class RuleDependencyGraph:
    """
    Directed acyclic graph of rule dependencies.

    Enables:
    - Transitive dependency expansion
    - Cross-domain rule discovery
    - Impact chain detection
    - Topological ordering for validation

    Example:
        graph = RuleDependencyGraph()
        graph.build_from_rules(rules)

        # Get all rules needed including dependencies
        required = graph.expand_dependencies({"FIN-REF-012"})
        # Returns: {"FIN-REF-012", "DEP-EP-006", "FIN-B2B-011", ...}

        # Get rules spanning multiple domains
        cross_domain = graph.get_cross_domain_rules(["referrals", "payments"])

        # Get downstream impact of a rule change
        impacted = graph.detect_impact_chain("FIN-REF-012")
    """

    def __init__(self):
        self._nodes: Dict[str, RuleNode] = {}

        # Indices for fast lookup
        self._domain_index: Dict[str, Set[str]] = defaultdict(set)
        self._module_index: Dict[str, Set[str]] = defaultdict(set)
        self._risk_index: Dict[RiskLevel, Set[str]] = defaultdict(set)
        self._keyword_index: Dict[str, Set[str]] = defaultdict(set)
        self._state_index: Dict[str, Set[str]] = defaultdict(set)

    def add_rule(self, rule: Rule) -> None:
        """
        Add a rule to the graph.

        Creates node and updates indices. Does not resolve dependencies yet -
        call build_edges() after all rules are added.
        """
        if rule.rule_id in self._nodes:
            # Update existing node
            self._nodes[rule.rule_id].rule = rule
        else:
            self._nodes[rule.rule_id] = RuleNode(rule=rule)

        # Update indices
        if rule.domain:
            self._domain_index[rule.domain.lower()].add(rule.rule_id)
        if rule.module:
            self._module_index[rule.module.lower()].add(rule.rule_id)
        self._risk_index[rule.risk_level].add(rule.rule_id)

        for keyword in rule.keywords:
            self._keyword_index[keyword.lower()].add(rule.rule_id)

        for state in rule.lifecycle_states:
            self._state_index[state.upper()].add(rule.rule_id)

    def build_from_rules(self, rules: List[Rule]) -> None:
        """
        Build graph from list of rules.

        Args:
            rules: List of Rule objects to add to graph
        """
        # First pass: add all rules
        for rule in rules:
            self.add_rule(rule)

        # Second pass: build edges
        self._build_edges()

        logger.info(
            f"Built rule graph: {len(self._nodes)} rules, "
            f"{self._count_edges()} edges"
        )

    def _build_edges(self) -> None:
        """Build dependency edges between nodes."""
        for rule_id, node in self._nodes.items():
            rule = node.rule

            # Add outgoing edges (this rule depends on)
            for dep_id in rule.depends_on:
                node.add_dependency(dep_id)

                # Add incoming edge to the dependency
                if dep_id in self._nodes:
                    self._nodes[dep_id].add_dependent(rule_id)
                else:
                    logger.warning(
                        f"Rule {rule_id} depends on unknown rule {dep_id}"
                    )

    def _count_edges(self) -> int:
        """Count total edges in graph."""
        return sum(len(node.outgoing) for node in self._nodes.values())

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID."""
        node = self._nodes.get(rule_id)
        return node.rule if node else None

    def has_rule(self, rule_id: str) -> bool:
        """Check if rule exists in graph."""
        return rule_id in self._nodes

    def expand_dependencies(
        self,
        rule_ids: Set[str],
        max_depth: int = 5
    ) -> Set[str]:
        """
        Recursively expand all transitive dependencies.

        Performs breadth-first traversal of dependency graph.

        Args:
            rule_ids: Starting rule IDs
            max_depth: Maximum recursion depth to prevent cycles

        Returns:
            Set of all rule IDs including transitive dependencies
        """
        result: Set[str] = set(rule_ids)
        frontier: Set[str] = set(rule_ids)
        depth = 0

        while frontier and depth < max_depth:
            next_frontier: Set[str] = set()

            for rule_id in frontier:
                node = self._nodes.get(rule_id)
                if node:
                    for dep_id in node.outgoing:
                        if dep_id not in result:
                            result.add(dep_id)
                            next_frontier.add(dep_id)

            frontier = next_frontier
            depth += 1

        if depth >= max_depth and frontier:
            logger.warning(
                f"Dependency expansion hit max_depth={max_depth} "
                f"with {len(frontier)} unexpanded rules"
            )

        return result

    def get_direct_dependencies(self, rule_id: str) -> Set[str]:
        """Get direct dependencies of a rule (not transitive)."""
        node = self._nodes.get(rule_id)
        return set(node.outgoing) if node else set()

    def get_dependents(self, rule_id: str) -> Set[str]:
        """Get rules that directly depend on this rule."""
        node = self._nodes.get(rule_id)
        return set(node.incoming) if node else set()

    def get_cross_domain_rules(
        self,
        domains: List[str]
    ) -> List[Rule]:
        """
        Get rules that span across specified domains.

        Finds rules that:
        1. Are directly in any of the domains
        2. Have dependencies spanning multiple domains
        3. Have impacts on multiple domains

        Args:
            domains: List of domain names to check

        Returns:
            List of Rule objects spanning the domains
        """
        if not domains:
            return []

        domains_lower = [d.lower() for d in domains]
        result: Set[str] = set()

        # Rules directly in the domains
        for domain in domains_lower:
            result.update(self._domain_index.get(domain, set()))

        # Rules with dependencies spanning domains
        for rule_id, node in self._nodes.items():
            rule = node.rule

            # Check if rule's dependencies span domains
            dep_domains: Set[str] = set()
            for dep_id in node.outgoing:
                dep_rule = self.get_rule(dep_id)
                if dep_rule and dep_rule.domain:
                    dep_domains.add(dep_rule.domain.lower())

            if len(dep_domains.intersection(domains_lower)) > 1:
                result.add(rule_id)

            # Check if rule's impacts span domains
            impact_overlap = sum(
                1 for impact in rule.impacts
                if impact.lower() in domains_lower
            )
            if impact_overlap > 1:
                result.add(rule_id)

        return [self._nodes[rid].rule for rid in result if rid in self._nodes]

    def detect_impact_chain(
        self,
        rule_id: str,
        max_depth: int = 5
    ) -> List[Rule]:
        """
        Detect all rules impacted by changes to given rule.

        Returns rules that depend on this rule (downstream impact).
        Results are in reverse topological order (direct dependents first).

        Args:
            rule_id: The rule to check impact for
            max_depth: Maximum depth to traverse

        Returns:
            List of rules impacted by changes to this rule
        """
        result: List[str] = []
        visited: Set[str] = set()
        frontier: Set[str] = {rule_id}
        depth = 0

        while frontier and depth < max_depth:
            next_frontier: Set[str] = set()

            for rid in frontier:
                if rid in visited:
                    continue
                visited.add(rid)

                if rid != rule_id:  # Don't include the source rule
                    result.append(rid)

                # Get rules that depend on this one
                node = self._nodes.get(rid)
                if node:
                    for dependent_id in node.incoming:
                        if dependent_id not in visited:
                            next_frontier.add(dependent_id)

            frontier = next_frontier
            depth += 1

        return [
            self._nodes[rid].rule
            for rid in result
            if rid in self._nodes
        ]

    def get_rules_by_risk_level(
        self,
        min_level: RiskLevel = RiskLevel.HIGH
    ) -> List[Rule]:
        """
        Get all rules at or above specified risk level.

        Args:
            min_level: Minimum risk level to include

        Returns:
            List of rules at or above the risk level
        """
        result: List[Rule] = []

        for level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            if level >= min_level:
                for rule_id in self._risk_index.get(level, set()):
                    node = self._nodes.get(rule_id)
                    if node:
                        result.append(node.rule)

        return result

    def get_rules_by_keywords(
        self,
        keywords: List[str],
        min_matches: int = 2
    ) -> List[Rule]:
        """
        Find rules matching keyword combinations.

        Args:
            keywords: Keywords to search for
            min_matches: Minimum keyword matches required

        Returns:
            List of rules matching the keywords
        """
        if not keywords:
            return []

        # Count matches per rule
        rule_matches: Dict[str, int] = defaultdict(int)

        for keyword in keywords:
            kw_lower = keyword.lower()
            for rule_id in self._keyword_index.get(kw_lower, set()):
                rule_matches[rule_id] += 1

        # Filter by min_matches
        result = [
            self._nodes[rid].rule
            for rid, count in rule_matches.items()
            if count >= min_matches and rid in self._nodes
        ]

        return result

    def get_rules_for_states(
        self,
        states: List[str]
    ) -> List[Rule]:
        """
        Get rules applicable to given lifecycle states.

        Args:
            states: List of state names (e.g., ["ACTIVE", "PENDING"])

        Returns:
            List of rules that apply to any of the states
        """
        if not states:
            return list(self.all_rules())

        result: Set[str] = set()

        for state in states:
            state_upper = state.upper()
            result.update(self._state_index.get(state_upper, set()))

        # Also include rules with no state restrictions
        for rule_id, node in self._nodes.items():
            if not node.rule.lifecycle_states:
                result.add(rule_id)

        return [
            self._nodes[rid].rule
            for rid in result
            if rid in self._nodes
        ]

    def get_rules_by_domain(self, domain: str) -> List[Rule]:
        """Get all rules in a domain."""
        rule_ids = self._domain_index.get(domain.lower(), set())
        return [
            self._nodes[rid].rule
            for rid in rule_ids
            if rid in self._nodes
        ]

    def get_rules_by_module(self, module: str) -> List[Rule]:
        """Get all rules in a module."""
        rule_ids = self._module_index.get(module.lower(), set())
        return [
            self._nodes[rid].rule
            for rid in rule_ids
            if rid in self._nodes
        ]

    def all_rules(self) -> Iterator[Rule]:
        """Iterate over all rules in graph."""
        for node in self._nodes.values():
            yield node.rule

    def all_rule_ids(self) -> Set[str]:
        """Get all rule IDs in graph."""
        return set(self._nodes.keys())

    def validate_graph_integrity(self) -> List[str]:
        """
        Validate graph has no cycles and all references resolve.

        Returns:
            List of warnings/errors found
        """
        issues: List[str] = []

        # Check for missing dependencies
        for rule_id, node in self._nodes.items():
            for dep_id in node.outgoing:
                if dep_id not in self._nodes:
                    issues.append(
                        f"Rule {rule_id} depends on unknown rule {dep_id}"
                    )

        # Check for cycles using DFS
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle(rule_id: str) -> bool:
            visited.add(rule_id)
            rec_stack.add(rule_id)

            node = self._nodes.get(rule_id)
            if node:
                for dep_id in node.outgoing:
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        issues.append(
                            f"Cycle detected: {rule_id} -> {dep_id}"
                        )
                        return True

            rec_stack.remove(rule_id)
            return False

        for rule_id in self._nodes:
            if rule_id not in visited:
                has_cycle(rule_id)

        return issues

    def get_statistics(self) -> Dict[str, any]:
        """Get graph statistics."""
        return {
            "total_rules": len(self._nodes),
            "total_edges": self._count_edges(),
            "by_domain": {
                domain: len(ids)
                for domain, ids in self._domain_index.items()
            },
            "by_module": {
                module: len(ids)
                for module, ids in self._module_index.items()
            },
            "by_risk": {
                level.value: len(ids)
                for level, ids in self._risk_index.items()
            },
        }

    def to_dict(self) -> Dict[str, any]:
        """Export graph for debugging/visualization."""
        return {
            "statistics": self.get_statistics(),
            "nodes": {
                rule_id: {
                    "rule": node.rule.to_dict(),
                    "outgoing": list(node.outgoing),
                    "incoming": list(node.incoming),
                }
                for rule_id, node in self._nodes.items()
            },
        }

    def __len__(self) -> int:
        return len(self._nodes)

    def __repr__(self) -> str:
        return f"RuleDependencyGraph(rules={len(self._nodes)}, edges={self._count_edges()})"
