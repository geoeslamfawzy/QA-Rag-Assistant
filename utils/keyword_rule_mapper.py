"""
Keyword-to-Rule Mapping Utilities

Maps story keywords to required business rules based on KEYWORD_RULE_MAPPING config.
Used for grounding enforcement.

This module consolidates duplicate logic from:
- services/rag_context_builder.py (_get_required_rules_from_keywords, lines 699-739)
- rag/retriever.py (_get_forced_rules_from_keywords, lines 603-645)

SAFETY: This module only consolidates existing logic. No changes to mapping logic.
"""

from typing import List, Optional

from rag.config import DEFAULT_CONFIG


def get_required_rules_from_keywords(
    query: str,
    additional_keywords: Optional[List[str]] = None
) -> List[str]:
    """
    Determine which rules MUST be present based on keyword matching.

    Uses KEYWORD_RULE_MAPPING from config to identify required rules.
    This implements the grounding enforcement mechanism to ensure
    critical business rules are always cited when relevant keywords appear.

    Args:
        query: Combined story text (will be lowercased)
        additional_keywords: Optional list of pre-analyzed keywords

    Returns:
        List of rule IDs that must be present (deduplicated)
    """
    if not hasattr(DEFAULT_CONFIG, 'KEYWORD_RULE_MAPPING'):
        return []

    query_lower = query.lower()

    # Combine query with additional keywords
    all_text = query_lower
    if additional_keywords:
        all_text += " " + " ".join(kw.lower() for kw in additional_keywords)

    required_rules = []

    for mapping_name, mapping in DEFAULT_CONFIG.KEYWORD_RULE_MAPPING.items():
        keywords = mapping.get("keywords", [])
        min_matches = mapping.get("min_matches", 2)
        rules = mapping.get("rules", [])

        # Count keyword matches
        match_count = sum(1 for kw in keywords if kw.lower() in all_text)

        if match_count >= min_matches:
            required_rules.extend(rules)

    return list(set(required_rules))  # Deduplicate
