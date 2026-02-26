"""
Rule ID Extraction Utilities

Centralized rule ID extraction to prevent duplication and ensure
consistent pattern matching across the codebase.

This module consolidates duplicate logic from:
- services/rag_context_builder.py (_extract_rule_ids_from_context)
- validators/coverage_validator.py (similar patterns)

SAFETY: This module only consolidates existing logic. No new patterns.
"""

import re
from typing import List, Set, Dict, Any


# Standard rule ID patterns (consolidated from rag_context_builder.py lines 682-688)
RULE_ID_PATTERNS = [
    r'(FIN-[A-Z]{1,5}-\d{3})',    # FIN-REF-012, FIN-B2B-001
    r'(RULE-[A-Z]{1,5}-\d{3})',   # RULE-ENT-001, RULE-ADMIN-005
    r'(DEP-[A-Z]{1,5}-\d{3})',    # DEP-EP-001
    r'(RULE-\d{3})',               # RULE-001 (legacy)
    r'(FIN-GC-\d{3})',             # FIN-GC-001 (gift card)
]


def extract_rule_ids_from_text(content: str) -> Set[str]:
    """
    Extract all rule IDs from text content.

    Patterns detected:
    - FIN-XXX-NNN (e.g., FIN-REF-012, FIN-B2B-001)
    - RULE-XXX-NNN (e.g., RULE-ENT-001, RULE-ADMIN-005)
    - DEP-XXX-NNN (e.g., DEP-EP-001)
    - RULE-NNN (legacy format)
    - FIN-GC-NNN (gift card)

    Args:
        content: Text content to search

    Returns:
        Set of unique rule IDs found (uppercase)
    """
    rule_ids = set()
    content_upper = content.upper()

    for pattern in RULE_ID_PATTERNS:
        matches = re.findall(pattern, content_upper)
        rule_ids.update(matches)

    return rule_ids


def extract_rule_ids_from_context(
    knowledge_context: List[Dict[str, Any]]
) -> Set[str]:
    """
    Extract all rule IDs from knowledge context chunks.

    Args:
        knowledge_context: List of knowledge chunks with 'content' field

    Returns:
        Set of unique rule IDs found
    """
    rule_ids = set()

    for chunk in knowledge_context:
        content = chunk.get("content", "")
        rule_ids.update(extract_rule_ids_from_text(content))

    return rule_ids
