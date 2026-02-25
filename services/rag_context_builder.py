"""
RAG Context Builder Service

Shared service that builds RAG context for any command.
Encapsulates: Jira fetch → Pre-analyze → Retrieve → Validate → Grounding Verification

This service is the single source of truth for RAG pipeline execution.
Both ./bin/rag-brain and ./bin/analyze use this service.

GROUNDING ENFORCEMENT:
This module now includes grounding verification that ensures:
1. Critical business rules are retrieved based on keyword matching
2. Retrieved context contains required rule citations
3. Outputs are validated for domain-specific grounding
"""
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set

from jira_client import JiraClient
from rag import (
    HybridRetriever,
    StoryPreAnalyzer,
)
from rag.config import DEFAULT_CONFIG
from rag.story_pre_analyzer import PreAnalysisResult
from rag.retriever import StoryContext, RetrievalResult
from validators import (
    ValidatorPipeline,
    StateValidator,
    FinancialValidator,
    RuleEngine,
    CrossDepChecker,
)


@dataclass
class GroundingVerification:
    """Result of grounding verification."""
    is_grounded: bool
    grounding_score: float  # 0-1, where 1 is fully grounded
    extracted_rule_ids: List[str]  # Rule IDs found in retrieved context
    required_rule_ids: List[str]  # Rule IDs that should be present based on keywords
    missing_rule_ids: List[str]  # Required rules not found in context
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_grounded": self.is_grounded,
            "grounding_score": self.grounding_score,
            "extracted_rule_ids": self.extracted_rule_ids,
            "required_rule_ids": self.required_rule_ids,
            "missing_rule_ids": self.missing_rule_ids,
            "warnings": self.warnings,
        }


@dataclass
class RAGContext:
    """Complete RAG context for a story."""
    story: Dict[str, Any]
    pre_analysis: PreAnalysisResult
    retrieved_chunks: List[RetrievalResult]
    validation_results: Dict[str, Any]
    knowledge_context: List[Dict[str, Any]]
    grounding: Optional[GroundingVerification] = None  # Grounding verification result


class RAGContextBuilder:
    """
    Builds RAG context for any CLI command.

    This is the shared service that encapsulates the complete RAG pipeline:
    1. Fetch Jira story
    2. Pre-analyze story (detect intents, domains, risks)
    3. Retrieve relevant knowledge chunks (hybrid retrieval)
    4. Run validators (state, financial, rule, cross-dep)
    5. Return complete RAGContext

    Usage:
        builder = RAGContextBuilder()
        context = builder.build("CMB-32860")
        if context:
            # Use context.story, context.retrieved_chunks, etc.
        builder.close()
    """

    def __init__(
        self,
        jira_client: Optional[JiraClient] = None,
        retriever: Optional[HybridRetriever] = None,
        pre_analyzer: Optional[StoryPreAnalyzer] = None,
    ):
        """
        Initialize the RAG context builder.

        Args:
            jira_client: Optional JiraClient instance (creates new if not provided)
            retriever: Optional HybridRetriever instance (creates new if not provided)
            pre_analyzer: Optional StoryPreAnalyzer instance (creates new if not provided)
        """
        self._jira = jira_client or JiraClient()
        self._retriever = retriever or HybridRetriever()
        self._pre_analyzer = pre_analyzer or StoryPreAnalyzer()
        self._validators = ValidatorPipeline([
            StateValidator(),
            FinancialValidator(),
            RuleEngine(),
            CrossDepChecker(),
        ])
        self._index_loaded = False

    def _ensure_index_loaded(self) -> bool:
        """Ensure the retriever has loaded the index."""
        if not self._index_loaded:
            self._index_loaded = self._retriever.load_index()
        return self._index_loaded

    def build(self, issue_key: str, top_k: int = 10) -> Optional[RAGContext]:
        """
        Build complete RAG context for a story.

        Args:
            issue_key: Jira issue key (e.g., CMB-32860)
            top_k: Number of chunks to retrieve (default: 10)

        Returns:
            RAGContext with all analysis results, or None if story not found
        """
        # Step 1: Fetch Jira story
        issue = self._jira.get_issue(issue_key)
        if not issue:
            return None

        story = {
            "key": issue.get("key"),
            "title": issue.get("summary"),
            "summary": issue.get("summary"),  # Alias for backward compatibility
            "status": issue.get("status"),
            "priority": issue.get("priority"),
            "issue_type": issue.get("issue_type"),
            "assignee": issue.get("assignee"),
            "reporter": issue.get("reporter"),
            "created": issue.get("created"),
            "updated": issue.get("updated"),
            "url": issue.get("url"),
            "description": issue.get("description", ""),
            "acceptance_criteria": issue.get("acceptance_criteria", []),
        }

        # Step 2: Pre-analyze story
        pre_analysis = self._pre_analyzer.analyze(story)

        # Step 3: Retrieve knowledge
        # Ensure index is loaded
        if not self._ensure_index_loaded():
            # If no index, return context without retrieved chunks
            return RAGContext(
                story=story,
                pre_analysis=pre_analysis,
                retrieved_chunks=[],
                validation_results={},
                knowledge_context=[],
            )

        # Build query from story
        query_parts = [story.get("title", "")]
        if story.get("description"):
            query_parts.append(story["description"][:500])
        query = " ".join(query_parts)

        # Create story context for retrieval
        story_context = StoryContext(
            text=query,
            detected_domains=pre_analysis.detected_domains,
            priority_rule_types=pre_analysis.priority_rule_types,
            risk_flags=pre_analysis.risk_flags,
            keywords=pre_analysis.keywords[:20]
        )

        # Retrieve relevant chunks with guaranteed rule type coverage
        # Uses retrieve_with_rules() to ensure atomic_rule, state_machine,
        # and financial_logic chunks are always included (fixes retrieval bias)
        retrieved_chunks = self._retriever.retrieve_with_rules(
            query=query,
            story_context=story_context,
            top_k=top_k
        )

        # Step 4: Build knowledge context for validators
        knowledge_context = [
            {
                "id": chunk.chunk.id,
                "content": chunk.chunk.content,
                "metadata": chunk.chunk.metadata
            }
            for chunk in retrieved_chunks
        ]

        # Step 5: Run validators
        validation_results = self._validators.run_as_dicts(story, knowledge_context)

        # Create context (without grounding for now)
        context = RAGContext(
            story=story,
            pre_analysis=pre_analysis,
            retrieved_chunks=retrieved_chunks,
            validation_results=validation_results,
            knowledge_context=knowledge_context,
            grounding=None,
        )

        # Step 6: Verify grounding
        context.grounding = self.verify_grounding(context)

        # Log grounding warnings if any
        if context.grounding and context.grounding.warnings:
            import logging
            logger = logging.getLogger(__name__)
            for warning in context.grounding.warnings:
                logger.warning(warning)

        return context

    def build_from_story(self, story: Dict[str, Any], top_k: int = 10) -> RAGContext:
        """
        Build RAG context from an already-fetched story.

        Args:
            story: Story dictionary with key, title, description, etc.
            top_k: Number of chunks to retrieve (default: 10)

        Returns:
            RAGContext with all analysis results
        """
        # Step 1: Pre-analyze story
        pre_analysis = self._pre_analyzer.analyze(story)

        # Step 2: Retrieve knowledge
        if not self._ensure_index_loaded():
            return RAGContext(
                story=story,
                pre_analysis=pre_analysis,
                retrieved_chunks=[],
                validation_results={},
                knowledge_context=[],
            )

        query_parts = [story.get("title", "")]
        if story.get("description"):
            query_parts.append(story["description"][:500])
        query = " ".join(query_parts)

        story_context = StoryContext(
            text=query,
            detected_domains=pre_analysis.detected_domains,
            priority_rule_types=pre_analysis.priority_rule_types,
            risk_flags=pre_analysis.risk_flags,
            keywords=pre_analysis.keywords[:20]
        )

        retrieved_chunks = self._retriever.retrieve_with_rules(
            query=query,
            story_context=story_context,
            top_k=top_k
        )

        # Step 3: Build knowledge context
        knowledge_context = [
            {
                "id": chunk.chunk.id,
                "content": chunk.chunk.content,
                "metadata": chunk.chunk.metadata
            }
            for chunk in retrieved_chunks
        ]

        # Step 4: Run validators
        validation_results = self._validators.run_as_dicts(story, knowledge_context)

        # Create context
        context = RAGContext(
            story=story,
            pre_analysis=pre_analysis,
            retrieved_chunks=retrieved_chunks,
            validation_results=validation_results,
            knowledge_context=knowledge_context,
            grounding=None,
        )

        # Step 5: Verify grounding
        context.grounding = self.verify_grounding(context)

        return context

    def verify_grounding(
        self,
        context: RAGContext
    ) -> GroundingVerification:
        """
        Verify that the RAG context is properly grounded in business rules.

        This method:
        1. Extracts all rule IDs from retrieved chunks
        2. Determines required rules based on keyword matching
        3. Verifies required rules are present in context
        4. Calculates grounding score

        Args:
            context: RAGContext to verify

        Returns:
            GroundingVerification with score and missing rules
        """
        # Extract all rule IDs from retrieved content
        extracted_rules = self._extract_rule_ids_from_context(context.knowledge_context)

        # Determine required rules based on story keywords
        query = context.story.get("title", "") + " " + context.story.get("description", "")
        required_rules = self._get_required_rules_from_keywords(query, context.pre_analysis)

        # Find missing rules
        missing_rules = [r for r in required_rules if r not in extracted_rules]

        # Calculate grounding score
        if required_rules:
            found_count = len(required_rules) - len(missing_rules)
            grounding_score = found_count / len(required_rules)
        else:
            # No required rules identified - check if we have any rules at all
            grounding_score = 1.0 if extracted_rules else 0.5

        # Generate warnings
        warnings = []
        if missing_rules:
            warnings.append(
                f"GROUNDING WARNING: Missing required rules: {', '.join(missing_rules)}. "
                "These rules should be cited based on story keywords."
            )

        if not extracted_rules and context.knowledge_context:
            warnings.append(
                "GROUNDING WARNING: No rule IDs found in retrieved context despite "
                f"having {len(context.knowledge_context)} knowledge chunks."
            )

        is_grounded = grounding_score >= 0.7 and not missing_rules

        return GroundingVerification(
            is_grounded=is_grounded,
            grounding_score=grounding_score,
            extracted_rule_ids=list(extracted_rules),
            required_rule_ids=required_rules,
            missing_rule_ids=missing_rules,
            warnings=warnings,
        )

    def _extract_rule_ids_from_context(
        self,
        knowledge_context: List[Dict[str, Any]]
    ) -> Set[str]:
        """
        Extract all rule IDs from knowledge context chunks.

        Patterns detected:
        - FIN-XXX-NNN (e.g., FIN-REF-012, FIN-B2B-001)
        - RULE-XXX-NNN (e.g., RULE-ENT-001, RULE-ADMIN-005)
        - DEP-XXX-NNN (e.g., DEP-EP-001)
        - RULE-NNN (legacy format)

        Args:
            knowledge_context: List of knowledge chunks

        Returns:
            Set of unique rule IDs found
        """
        rule_ids = set()

        # Patterns for different rule ID formats
        patterns = [
            r'(FIN-[A-Z]{1,5}-\d{3})',   # FIN-REF-012, FIN-B2B-001
            r'(RULE-[A-Z]{1,5}-\d{3})',  # RULE-ENT-001, RULE-ADMIN-005
            r'(DEP-[A-Z]{1,5}-\d{3})',   # DEP-EP-001
            r'(RULE-\d{3})',              # RULE-001 (legacy)
            r'(FIN-GC-\d{3})',            # FIN-GC-001 (gift card)
        ]

        for chunk in knowledge_context:
            content = chunk.get("content", "").upper()

            for pattern in patterns:
                matches = re.findall(pattern, content)
                rule_ids.update(matches)

        return rule_ids

    def _get_required_rules_from_keywords(
        self,
        query: str,
        pre_analysis: PreAnalysisResult
    ) -> List[str]:
        """
        Determine which rules MUST be present based on keyword matching.

        Uses KEYWORD_RULE_MAPPING from config to identify required rules.

        Args:
            query: Combined story text
            pre_analysis: Story pre-analysis result

        Returns:
            List of rule IDs that must be present
        """
        if not hasattr(DEFAULT_CONFIG, 'KEYWORD_RULE_MAPPING'):
            return []

        query_lower = query.lower()

        # Also include keywords from pre-analysis
        all_text = query_lower
        if pre_analysis.keywords:
            all_text += " " + " ".join(pre_analysis.keywords).lower()

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

    def close(self):
        """Release resources."""
        self._retriever.close()
