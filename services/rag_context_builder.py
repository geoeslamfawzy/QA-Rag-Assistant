"""
RAG Context Builder Service

Shared service that builds RAG context for any command.
Encapsulates: Jira fetch → Pre-analyze → Retrieve → Validate

This service is the single source of truth for RAG pipeline execution.
Both ./bin/rag-brain and ./bin/analyze use this service.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from jira_client import JiraClient
from rag import (
    HybridRetriever,
    StoryPreAnalyzer,
)
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
class RAGContext:
    """Complete RAG context for a story."""
    story: Dict[str, Any]
    pre_analysis: PreAnalysisResult
    retrieved_chunks: List[RetrievalResult]
    validation_results: Dict[str, Any]
    knowledge_context: List[Dict[str, Any]]


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

        # Retrieve relevant chunks
        retrieved_chunks = self._retriever.retrieve(
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

        return RAGContext(
            story=story,
            pre_analysis=pre_analysis,
            retrieved_chunks=retrieved_chunks,
            validation_results=validation_results,
            knowledge_context=knowledge_context,
        )

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

        retrieved_chunks = self._retriever.retrieve(
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

        return RAGContext(
            story=story,
            pre_analysis=pre_analysis,
            retrieved_chunks=retrieved_chunks,
            validation_results=validation_results,
            knowledge_context=knowledge_context,
        )

    def close(self):
        """Release resources."""
        self._retriever.close()
