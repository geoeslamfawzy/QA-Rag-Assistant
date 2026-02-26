"""
RAG Module Constants

Named constants for display limits, truncation lengths, and algorithm parameters.
These are PRESENTATION and ALGORITHM TUNING constants, NOT business logic thresholds.

SAFETY NOTE:
- Coverage thresholds remain in rag/config.py (CRITICAL_COVERAGE_THRESHOLD, etc.)
- These constants affect DISPLAY and ALGORITHM TUNING only
- DO NOT add business rule thresholds here
- DO NOT modify these values without understanding their impact

Consolidated from:
- rag/prompt_builder.py (display limits)
- rag/retriever.py (RRF constant)
- services/rag_context_builder.py (pre-analysis limits)
"""

# ===========================================
# DISPLAY LIMITS (for prompt_builder.py)
# ===========================================

# Maximum chunks to display per rule type in knowledge section
MAX_CHUNKS_PER_RULE_TYPE = 3

# Maximum content length before truncation (characters)
MAX_CONTENT_PREVIEW_LENGTH = 500

# Maximum findings to display per validator
MAX_FINDINGS_TO_DISPLAY = 5

# Maximum extracted rules to display in grounding section
MAX_EXTRACTED_RULES_DISPLAY = 20

# Maximum reasoning chains to display
MAX_CHAINS_TO_DISPLAY = 5

# Maximum story snippet length in reasoning chains (characters)
MAX_STORY_SNIPPET_LENGTH = 150

# Maximum links to display per reasoning chain
MAX_LINKS_PER_CHAIN = 4

# Maximum test implications to display
MAX_TEST_IMPLICATIONS = 10

# Maximum rule-based tests to display
MAX_RULE_BASED_TESTS = 10

# ===========================================
# RETRIEVAL ALGORITHM CONSTANTS
# ===========================================

# RRF (Reciprocal Rank Fusion) constant
# Standard value is 60 - affects rank combination
# Lower = more weight to top ranks, Higher = smoother combination
RRF_K_CONSTANT = 60

# ===========================================
# PRE-ANALYSIS LIMITS
# ===========================================

# Maximum keywords to use from pre-analysis
MAX_PREANALYSIS_KEYWORDS = 20
