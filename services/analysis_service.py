"""
Analysis Service Module

Orchestrates the story analysis workflow: fetch → analyze → write.
Receives all dependencies via constructor (Dependency Inversion Principle).

Now enhanced with RAG context for knowledge-grounded analysis.
"""
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime

from jira_client import JiraClient
from analyzer import IssueAnalyzer
from services.output_writer import OutputWriter

if TYPE_CHECKING:
    from services.rag_context_builder import RAGContextBuilder, RAGContext


class AnalysisService:
    """
    Coordinates JiraClient, IssueAnalyzer, OutputWriter, and RAGContextBuilder
    so that CLI handlers contain no orchestration logic.

    When RAGContextBuilder is provided, analysis is enhanced with:
    - Retrieved knowledge chunks from the knowledge base
    - Validation results from StateValidator, FinancialValidator, etc.
    - Risk assessment and domain classification
    """

    def __init__(
        self,
        client: JiraClient,
        analyzer: IssueAnalyzer,
        writer: OutputWriter,
        rag_builder: Optional['RAGContextBuilder'] = None,
    ):
        """
        Initialize the analysis service.

        Args:
            client: JiraClient for fetching issues
            analyzer: IssueAnalyzer for basic analysis
            writer: OutputWriter for saving results
            rag_builder: Optional RAGContextBuilder for RAG-enhanced analysis
        """
        self._client = client
        self._analyzer = analyzer
        self._writer = writer
        self._rag_builder = rag_builder

    def analyze_story(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Fetch, analyze, and save a story.

        If RAGContextBuilder is available, uses RAG-enhanced analysis.
        Otherwise, falls back to basic heuristic analysis.

        Args:
            issue_key: Jira issue key (e.g., CMB-32860)

        Returns:
            Result dict with issue, analysis, and saved_path, or None if not found
        """
        if self._rag_builder:
            return self._analyze_with_rag(issue_key)
        else:
            return self._analyze_basic(issue_key)

    def _analyze_basic(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Basic analysis without RAG (backward compatibility)."""
        issue = self._client.get_issue(issue_key)
        if not issue:
            return None
        analysis = self._analyzer.analyze_story(issue)
        content = self._analyzer.format_story_analysis_md(issue, analysis, issue_key)
        saved_path = self._writer.write_analysis(issue_key, content)
        return {"issue": issue, "analysis": analysis, "saved_path": saved_path}

    def _analyze_with_rag(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """RAG-enhanced analysis with knowledge context and validation."""
        # Build RAG context (includes fetch, pre-analyze, retrieve, validate)
        rag_context = self._rag_builder.build(issue_key)
        if not rag_context:
            return None

        # Also run basic analysis for completeness/quality checks
        basic_analysis = self._analyzer.analyze_story(rag_context.story)

        # Format RAG-enhanced output
        content = self._format_rag_analysis_md(rag_context, basic_analysis, issue_key)
        saved_path = self._writer.write_analysis(issue_key, content)

        return {
            "issue": rag_context.story,
            "analysis": basic_analysis,
            "rag_context": rag_context,
            "saved_path": saved_path,
        }

    def _format_rag_analysis_md(
        self,
        rag_context: 'RAGContext',
        basic_analysis: Dict[str, Any],
        issue_key: str,
    ) -> str:
        """Format RAG-enhanced analysis as markdown."""
        story = rag_context.story
        pre_analysis = rag_context.pre_analysis
        validation_results = rag_context.validation_results

        lines = [
            f"# RAG-Enhanced Story Analysis: {issue_key}",
            f"**{story.get('title', story.get('summary', ''))}**",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "---",
            "",
            "## Issue Details",
            f"- **Key:** {story.get('key', '')}",
            f"- **Status:** {story.get('status', '')}",
            f"- **Type:** {story.get('issue_type', '')}",
            f"- **Priority:** {story.get('priority', '')}",
            f"- **Assignee:** {story.get('assignee', '')}",
            "",
            "## Description",
            story.get('description', 'No description') or 'No description',
            "",
        ]

        # Acceptance Criteria
        ac = story.get('acceptance_criteria')
        if ac:
            lines.extend(["## Acceptance Criteria", ac if isinstance(ac, str) else "\n".join(ac), ""])

        lines.extend(["---", ""])

        # Risk Assessment
        lines.extend([
            "## Risk Assessment",
            f"- **Risk Level:** {pre_analysis.risk_level.upper()}",
            f"- **Detected Domains:** {', '.join(pre_analysis.detected_domains[:5]) or 'None'}",
            f"- **Priority Rule Types:** {', '.join(pre_analysis.priority_rule_types[:5]) or 'None'}",
            "",
        ])

        if pre_analysis.risk_flags:
            lines.append("**Risk Flags:**")
            for flag in pre_analysis.risk_flags[:5]:
                lines.append(f"- {flag}")
            lines.append("")

        # Detected Intents
        if pre_analysis.detected_intents:
            lines.extend(["## Detected Intents", ""])
            for intent in pre_analysis.detected_intents[:5]:
                lines.append(f"- **{intent.intent}** (confidence: {intent.confidence:.0%})")
            lines.append("")

        # Validation Results
        lines.extend(["## Validation Results", ""])
        for validator_name, result in validation_results.items():
            status = "PASS" if result.get("passed", True) else "FAIL"
            score = result.get("score", 1.0)
            lines.append(f"### {validator_name}: {status} ({score:.0%})")

            findings = result.get("findings", [])
            if findings:
                for finding in findings[:3]:
                    severity = finding.get("severity", "INFO")
                    message = finding.get("message", "")
                    lines.append(f"- [{severity}] {message}")
            lines.append("")

        # Retrieved Knowledge Context
        if rag_context.retrieved_chunks:
            lines.extend(["## Retrieved Knowledge Context", ""])
            for i, chunk in enumerate(rag_context.retrieved_chunks[:5], 1):
                module = chunk.chunk.metadata.get("module", "unknown")
                rule_type = chunk.chunk.metadata.get("rule_type", "general")
                lines.append(f"### [{i}] {chunk.chunk.id}")
                lines.append(f"*Module: {module} | Type: {rule_type} | Relevance: {chunk.final_score:.0%}*")
                lines.append("")
                # Truncate content for readability
                content_preview = chunk.chunk.content[:500]
                if len(chunk.chunk.content) > 500:
                    content_preview += "..."
                lines.append(content_preview)
                lines.append("")

        # Basic Analysis (completeness, quality, clarity)
        lines.extend(["---", "", "## Story Quality Analysis", ""])

        # Completeness
        c = basic_analysis.get('completeness', {})
        lines.extend([
            "### Completeness",
            f"- Description: {'Yes' if c.get('has_description') else 'No'} ({c.get('description_length', 0)} chars, {c.get('description_adequacy', 'unknown')})",
            f"- Acceptance Criteria: {'Yes' if c.get('has_acceptance_criteria') else 'No'}",
        ])
        ac_analysis = basic_analysis.get('acceptance_criteria_analysis', {})
        if ac_analysis.get('count', 0) > 0:
            lines.append(f"  - Criteria count: {ac_analysis.get('count', 0)}")
            lines.append(f"  - Quality: {ac_analysis.get('adequacy', 'unknown')}")
        lines.append("")

        # Quality
        q = basic_analysis.get('quality', {})
        lines.append("### Quality")
        for s in q.get('strengths', []):
            lines.append(f"- {s}")
        for i in q.get('issues', []):
            lines.append(f"- {i}")
        lines.append("")

        # Clarity
        cl = basic_analysis.get('clarity', {})
        lines.append("### Clarity")
        for s in cl.get('strengths', []):
            lines.append(f"- {s}")
        for i in cl.get('issues', []):
            lines.append(f"- {i}")
        lines.append("")

        # Recommendations
        recs = basic_analysis.get('recommendations', [])
        lines.append("### Recommendations")
        if recs:
            for r in recs:
                lines.append(f"- {r}")
        else:
            lines.append("- Story looks well-defined!")
        lines.append("")

        # Footer
        lines.extend([
            "---",
            "",
            "*This analysis was generated using the RAG-enhanced QA system with Yassir Mobility knowledge base.*",
        ])

        return "\n".join(lines)

    def analyze_bulk(self, jql: Optional[str], limit: int) -> Optional[Dict[str, Any]]:
        """Fetch multiple issues and run bulk analysis. Returns result dict or None."""
        issues = self._client.get_issues(jql=jql, max_results=limit)
        if not issues:
            return None
        return {"issues": issues, "analysis": self._analyzer.analyze_issues(issues)}

    def get_single_insights(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Fetch a single issue and produce quick insights. Returns result dict or None."""
        issue = self._client.get_issue(issue_key)
        if not issue:
            return None
        return {"issue": issue, "insights": self._analyzer.analyze_single_issue(issue)}

    def close(self):
        """Release resources."""
        if self._rag_builder:
            self._rag_builder.close()
