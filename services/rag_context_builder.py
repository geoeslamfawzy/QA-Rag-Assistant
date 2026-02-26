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

DETERMINISTIC QA BRAIN v2.0:
Extended with QA Intelligence Layer for:
1. Rule dependency tracking and expansion
2. Coverage validation with strict mode
3. Deterministic output generation with reasoning chains
4. Ambiguity detection engine
5. Gap analysis
6. Scenario expansion
7. Risk-based test design
8. Defect intelligence
9. Knowledge gap detection
"""
import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
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
    CoverageValidator,
    CoverageResult,
)

# Deterministic QA Brain imports
from models.required_rule_set import RequiredRuleSet
from models.test_case import TestCase
from models.defect import Defect
from models.ambiguity import AmbiguityReport
from models.gap import GapReport
from core.rule_graph import RuleDependencyGraph
from core.rule_loader import RuleLoader
from core.rule_set_builder import RuleSetBuilder
from services.deterministic_generator import DeterministicGenerator, DeterministicOutput

# QA Intelligence v2.0 imports
from qa_intelligence.ambiguity_engine import AmbiguityEngine
from qa_intelligence.gap_analyzer import GapAnalyzer
from qa_intelligence.scenario_expander import ScenarioExpander, TestScenario
from qa_intelligence.risk_based_test_designer import RiskBasedTestDesigner
from qa_intelligence.defect_engine import DefectEngine
from qa_intelligence.knowledge_gap_detector import KnowledgeGapDetector, KnowledgeGapReport

logger = logging.getLogger(__name__)


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
    """Complete RAG context for a story (v2.0)."""
    story: Dict[str, Any]
    pre_analysis: PreAnalysisResult
    retrieved_chunks: List[RetrievalResult]
    validation_results: Dict[str, Any]
    knowledge_context: List[Dict[str, Any]]
    grounding: Optional[GroundingVerification] = None  # Grounding verification result

    # Deterministic QA Brain fields
    required_rules: Optional[RequiredRuleSet] = None
    coverage_result: Optional[CoverageResult] = None
    deterministic_output: Optional[DeterministicOutput] = None

    # QA Intelligence v2.0 fields
    ambiguity_report: Optional[AmbiguityReport] = None
    gap_report: Optional[GapReport] = None
    test_scenarios: Optional[List[TestScenario]] = None
    test_cases: Optional[List[TestCase]] = None
    generated_defects: Optional[List[Defect]] = None
    knowledge_gap_report: Optional[KnowledgeGapReport] = None


class RAGContextBuilder:
    """
    Builds RAG context for any CLI command.

    This is the shared service that encapsulates the complete RAG pipeline:
    1. Fetch Jira story
    2. Pre-analyze story (detect intents, domains, risks)
    3. Retrieve relevant knowledge chunks (hybrid retrieval)
    4. Run validators (state, financial, rule, cross-dep)
    5. Build required rule set (Deterministic QA Brain)
    6. Validate coverage
    7. Generate deterministic output
    8. Run QA Intelligence v2.0 analysis
    9. Return complete RAGContext

    Usage:
        builder = RAGContextBuilder()
        context = builder.build("CMB-32860")
        if context:
            # Use context.story, context.retrieved_chunks, etc.
            # v2.0: context.ambiguity_report, context.gap_report, etc.
        builder.close()
    """

    def __init__(
        self,
        jira_client: Optional[JiraClient] = None,
        retriever: Optional[HybridRetriever] = None,
        pre_analyzer: Optional[StoryPreAnalyzer] = None,
        enable_deterministic: bool = True,
    ):
        """
        Initialize the RAG context builder.

        Args:
            jira_client: Optional JiraClient instance (creates new if not provided)
            retriever: Optional HybridRetriever instance (creates new if not provided)
            pre_analyzer: Optional StoryPreAnalyzer instance (creates new if not provided)
            enable_deterministic: Enable deterministic QA brain features (default: True)
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
        self._enable_deterministic = enable_deterministic

        # Initialize Deterministic QA Brain components
        self._rule_graph: Optional[RuleDependencyGraph] = None
        self._rule_set_builder: Optional[RuleSetBuilder] = None
        self._coverage_validator: Optional[CoverageValidator] = None
        self._deterministic_generator: Optional[DeterministicGenerator] = None

        # QA Intelligence v2.0 engines
        self._ambiguity_engine: Optional[AmbiguityEngine] = None
        self._gap_analyzer: Optional[GapAnalyzer] = None
        self._scenario_expander: Optional[ScenarioExpander] = None
        self._test_designer: Optional[RiskBasedTestDesigner] = None
        self._defect_engine: Optional[DefectEngine] = None
        self._knowledge_gap_detector: Optional[KnowledgeGapDetector] = None

        if enable_deterministic:
            self._init_deterministic_components()
            self._init_qa_intelligence_v2()

    def _ensure_index_loaded(self) -> bool:
        """Ensure the retriever has loaded the index."""
        if not self._index_loaded:
            self._index_loaded = self._retriever.load_index()
        return self._index_loaded

    def _init_deterministic_components(self) -> None:
        """
        Initialize Deterministic QA Brain components.

        Loads rules from knowledge base and builds the rule dependency graph.
        """
        try:
            # Load rules from knowledge base
            kb_path = Path(DEFAULT_CONFIG.KNOWLEDGE_BASE_DIR)
            rule_loader = RuleLoader(kb_path)
            rules = rule_loader.load_all_rules()

            # Build rule dependency graph
            self._rule_graph = RuleDependencyGraph()
            self._rule_graph.build_from_rules(rules)

            # Initialize builders and validators
            self._rule_set_builder = RuleSetBuilder(self._rule_graph)
            self._coverage_validator = CoverageValidator(
                strict_mode=DEFAULT_CONFIG.STRICT_MODE
            )
            self._deterministic_generator = DeterministicGenerator(
                self._rule_graph,
                strict_mode=DEFAULT_CONFIG.STRICT_MODE
            )

            logger.info(
                f"Deterministic QA Brain initialized: "
                f"{len(self._rule_graph)} rules loaded"
            )

        except Exception as e:
            logger.warning(
                f"Failed to initialize deterministic components: {e}. "
                "Falling back to basic RAG mode."
            )
            self._enable_deterministic = False

    def _init_qa_intelligence_v2(self) -> None:
        """
        Initialize QA Intelligence v2.0 engines.

        All engines are deterministic - no randomness or probabilistic sampling.
        """
        try:
            if self._rule_graph:
                self._ambiguity_engine = AmbiguityEngine(self._rule_graph)
                self._gap_analyzer = GapAnalyzer(self._rule_graph)
                self._scenario_expander = ScenarioExpander(self._rule_graph)
                self._knowledge_gap_detector = KnowledgeGapDetector(self._rule_graph)

            # These don't need the rule graph
            self._test_designer = RiskBasedTestDesigner()
            self._defect_engine = DefectEngine()

            logger.info("QA Intelligence v2.0 engines initialized")

        except Exception as e:
            logger.warning(
                f"Failed to initialize QA Intelligence v2.0: {e}. "
                "QA Intelligence features will be unavailable."
            )

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
        # Note: MAX_PREANALYSIS_KEYWORDS = 20 (see rag/constants.py)
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

        # Deterministic QA Brain steps (if enabled)
        required_rules = None
        coverage_result = None
        deterministic_output = None

        # QA Intelligence v2.0 outputs
        ambiguity_report = None
        gap_report = None
        test_scenarios = None
        test_cases = None
        generated_defects = None
        knowledge_gap_report = None

        if self._enable_deterministic and self._rule_set_builder:
            # Step 6: Build required rule set
            detected_states = pre_analysis.entities.get("states", []) if hasattr(pre_analysis, 'entities') else []
            required_rules = self._rule_set_builder.build_required_set(
                story_text=query,
                pre_analysis=pre_analysis,
                detected_states=detected_states
            )
            required_rules.story_key = story.get("key", "")

            # Step 7: Validate coverage
            retrieved_rule_ids = self._extract_rule_ids_from_context(knowledge_context)
            if self._coverage_validator:
                coverage_result = self._coverage_validator.validate_coverage(
                    required_rules=required_rules,
                    retrieved_rule_ids=retrieved_rule_ids
                )

                # Log coverage warnings
                if coverage_result.warnings:
                    for warning in coverage_result.warnings:
                        logger.warning(warning)

            # Step 8: Generate deterministic output
            if self._deterministic_generator and coverage_result:
                deterministic_output = self._deterministic_generator.generate(
                    story=story,
                    required_rules=required_rules,
                    coverage_result=coverage_result,
                    knowledge_context=knowledge_context
                )

                if not deterministic_output.can_generate:
                    logger.warning(
                        f"Deterministic generation blocked: "
                        f"{deterministic_output.generation_blocked_reason}"
                    )

            # Step 9: QA Intelligence v2.0 analysis
            story_text = self._build_story_text(story)

            # 9a: Ambiguity analysis
            if self._ambiguity_engine and required_rules:
                ambiguity_report = self._ambiguity_engine.analyze(
                    story_text=story_text,
                    required_rules=required_rules,
                    detected_states=detected_states
                )
                if ambiguity_report.has_blocking_ambiguities():
                    logger.warning(
                        f"Blocking ambiguities detected: {len(ambiguity_report.get_critical_items())} critical items"
                    )

            # 9b: Gap analysis
            if self._gap_analyzer and required_rules and coverage_result:
                gap_report = self._gap_analyzer.analyze(
                    required_rules=required_rules,
                    coverage_result=coverage_result,
                    story_text=story_text
                )
                if gap_report.has_critical_gaps():
                    logger.warning(
                        f"Critical gaps detected: {len(gap_report.get_critical_gaps())} critical items"
                    )

            # 9c: Scenario expansion
            if self._scenario_expander and required_rules:
                test_scenarios = self._scenario_expander.expand(
                    required_rules=required_rules,
                    story_key=story.get("key", "UNKNOWN")
                )
                logger.info(f"Generated {len(test_scenarios)} test scenarios")

            # 9d: Test case design
            if self._test_designer and test_scenarios:
                test_cases = self._test_designer.design_test_cases(
                    scenarios=test_scenarios,
                    story_key=story.get("key", "UNKNOWN")
                )
                logger.info(f"Designed {len(test_cases)} test cases")

            # 9e: Defect generation
            if self._defect_engine:
                generated_defects = []

                # From ambiguity report
                if ambiguity_report:
                    ambiguity_defects = self._defect_engine.generate_from_ambiguity(
                        ambiguity_report=ambiguity_report,
                        story_key=story.get("key", "UNKNOWN")
                    )
                    generated_defects.extend(ambiguity_defects)

                # From gap report
                if gap_report:
                    gap_defects = self._defect_engine.generate_from_gaps(
                        gap_report=gap_report,
                        story_key=story.get("key", "UNKNOWN")
                    )
                    generated_defects.extend(gap_defects)

                # From validation results
                validation_defects = self._defect_engine.generate_from_validation(
                    validation_results=validation_results,
                    story_key=story.get("key", "UNKNOWN")
                )
                generated_defects.extend(validation_defects)

                if generated_defects:
                    logger.info(f"Generated {len(generated_defects)} defects")

            # 9f: Knowledge gap detection
            if self._knowledge_gap_detector and required_rules:
                knowledge_gap_report = self._knowledge_gap_detector.detect(
                    pre_analysis=pre_analysis,
                    required_rules=required_rules,
                    story_text=story_text
                )
                if knowledge_gap_report.has_gaps:
                    logger.warning(
                        f"Knowledge gaps detected: confidence={knowledge_gap_report.coverage_confidence:.0%}"
                    )

        # Create context
        context = RAGContext(
            story=story,
            pre_analysis=pre_analysis,
            retrieved_chunks=retrieved_chunks,
            validation_results=validation_results,
            knowledge_context=knowledge_context,
            grounding=None,
            required_rules=required_rules,
            coverage_result=coverage_result,
            deterministic_output=deterministic_output,
            # QA Intelligence v2.0
            ambiguity_report=ambiguity_report,
            gap_report=gap_report,
            test_scenarios=test_scenarios,
            test_cases=test_cases,
            generated_defects=generated_defects,
            knowledge_gap_report=knowledge_gap_report,
        )

        # Step 10: Verify grounding (legacy)
        context.grounding = self.verify_grounding(context)

        # Log grounding warnings if any
        if context.grounding and context.grounding.warnings:
            for warning in context.grounding.warnings:
                logger.warning(warning)

        return context

    def _build_story_text(self, story: Dict[str, Any]) -> str:
        """Build combined story text for analysis."""
        parts = []

        if story.get("title"):
            parts.append(story["title"])

        if story.get("description"):
            parts.append(story["description"])

        if story.get("acceptance_criteria"):
            ac_list = story["acceptance_criteria"]
            if isinstance(ac_list, list):
                parts.extend(ac_list)
            elif isinstance(ac_list, str):
                parts.append(ac_list)

        return " ".join(parts)

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
        # Delegate to shared utility (consolidates duplicate logic)
        from utils.rule_extractor import extract_rule_ids_from_context
        return extract_rule_ids_from_context(knowledge_context)

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
        # Delegate to shared utility (consolidates duplicate logic)
        from utils.keyword_rule_mapper import get_required_rules_from_keywords
        keywords = pre_analysis.keywords if pre_analysis.keywords else []
        return get_required_rules_from_keywords(query, keywords)

    def close(self):
        """Release resources."""
        self._retriever.close()
