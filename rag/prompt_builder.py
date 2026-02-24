"""
Prompt Builder Module

Assembles structured prompt files from:
- Jira story details
- Retrieved knowledge context
- Validation results
- Pre-analysis results

Output is a markdown file ready for manual paste into Claude Pro.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .config import RAGConfig, DEFAULT_CONFIG
from .retriever import RetrievalResult
from .story_pre_analyzer import PreAnalysisResult


@dataclass
class PromptComponents:
    """Components assembled into the final prompt."""
    story: Dict[str, Any] = field(default_factory=dict)
    retrieved_chunks: List[RetrievalResult] = field(default_factory=list)
    pre_analysis: Optional[PreAnalysisResult] = None
    validation_results: Dict[str, Any] = field(default_factory=dict)
    include_debug: bool = False


class PromptBuilder:
    """
    Builds structured prompts for QA analysis.

    Features:
    - Story details formatting
    - Knowledge context inclusion
    - Validation results formatting
    - Risk assessment summary
    - Actionable QA request
    """

    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Initialize the prompt builder.

        Args:
            config: RAG configuration. Uses default if not provided.
        """
        self.config = config or DEFAULT_CONFIG
        self.components = PromptComponents()

    def set_story(self, story: Dict[str, Any]) -> 'PromptBuilder':
        """
        Set the Jira story data.

        Args:
            story: Story dictionary from Jira.

        Returns:
            Self for chaining.
        """
        self.components.story = story
        return self

    def set_retrieved_context(
        self,
        chunks: List[RetrievalResult]
    ) -> 'PromptBuilder':
        """
        Set the retrieved knowledge chunks.

        Args:
            chunks: List of RetrievalResult objects.

        Returns:
            Self for chaining.
        """
        self.components.retrieved_chunks = chunks
        return self

    def set_pre_analysis(
        self,
        analysis: PreAnalysisResult
    ) -> 'PromptBuilder':
        """
        Set the story pre-analysis results.

        Args:
            analysis: PreAnalysisResult from story analyzer.

        Returns:
            Self for chaining.
        """
        self.components.pre_analysis = analysis
        return self

    def set_validation_results(
        self,
        results: Dict[str, Any]
    ) -> 'PromptBuilder':
        """
        Set validation results from all validators.

        Args:
            results: Dictionary of validator name -> ValidationResult.to_dict()

        Returns:
            Self for chaining.
        """
        self.components.validation_results = results
        return self

    def set_debug_mode(self, include_debug: bool) -> 'PromptBuilder':
        """
        Set whether to include debug information.

        Args:
            include_debug: Whether to include retrieval scores etc.

        Returns:
            Self for chaining.
        """
        self.components.include_debug = include_debug
        return self

    def build(self) -> str:
        """
        Build the complete structured prompt.

        Returns:
            Formatted markdown string.
        """
        sections = []

        # Header
        sections.append(self._build_header())

        # Story Details
        sections.append(self._build_story_section())

        # Retrieved Knowledge Context
        sections.append(self._build_knowledge_section())

        # Validation Results
        sections.append(self._build_validation_section())

        # Risk Assessment
        sections.append(self._build_risk_section())

        # QA Analysis Request
        sections.append(self._build_request_section())

        # Footer
        sections.append(self._build_footer())

        return "\n\n".join(filter(None, sections))

    def _build_header(self) -> str:
        """Build the prompt header."""
        story = self.components.story
        key = story.get("key", "UNKNOWN")
        title = story.get("title", story.get("summary", "Untitled"))

        lines = [
            f"# QA Analysis Request: {key}",
            "",
            f"> **Story:** {title}",
            f"> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> **Mode:** Local RAG Brain (100% Local Processing)",
        ]

        return "\n".join(lines)

    def _build_story_section(self) -> str:
        """Build the story details section."""
        story = self.components.story

        lines = [
            "---",
            "",
            "## 1. STORY DETAILS",
            "",
        ]

        # Basic info
        lines.append(f"**Key:** {story.get('key', 'N/A')}")
        lines.append(f"**Title:** {story.get('title', story.get('summary', 'N/A'))}")
        lines.append(f"**Status:** {story.get('status', 'N/A')}")
        lines.append(f"**Priority:** {story.get('priority', 'N/A')}")
        lines.append(f"**Type:** {story.get('issue_type', story.get('type', 'N/A'))}")
        lines.append(f"**Assignee:** {story.get('assignee', 'Unassigned')}")

        # Description
        description = story.get("description", "No description provided")
        lines.append("")
        lines.append("### Description")
        lines.append("")
        lines.append(self._format_content(description))

        # Acceptance Criteria
        ac = story.get("acceptance_criteria", [])
        if ac:
            lines.append("")
            lines.append("### Acceptance Criteria")
            lines.append("")
            if isinstance(ac, list):
                for criterion in ac:
                    lines.append(f"- {criterion}")
            else:
                lines.append(str(ac))

        return "\n".join(lines)

    def _build_knowledge_section(self) -> str:
        """Build the retrieved knowledge section."""
        chunks = self.components.retrieved_chunks

        if not chunks:
            return ""

        lines = [
            "---",
            "",
            "## 2. RETRIEVED KNOWLEDGE CONTEXT",
            "",
            f"*Retrieved {len(chunks)} relevant knowledge chunks from local knowledge base.*",
            "",
        ]

        # Group chunks by rule type
        by_type = {}
        for chunk in chunks:
            rule_type = chunk.chunk.metadata.get("rule_type", "general")
            if rule_type not in by_type:
                by_type[rule_type] = []
            by_type[rule_type].append(chunk)

        # Format each group
        for rule_type, type_chunks in by_type.items():
            lines.append(f"### {rule_type.replace('_', ' ').title()}")
            lines.append("")

            for chunk in type_chunks[:3]:  # Top 3 per type
                metadata = chunk.chunk.metadata
                module = metadata.get("module", "Unknown")

                lines.append(f"**[{chunk.chunk.id}]** (Module: {module})")

                if self.components.include_debug:
                    lines.append(f"*Relevance: {chunk.final_score:.2%}*")

                # Content (truncated)
                content = chunk.chunk.content
                if len(content) > 500:
                    content = content[:500] + "..."

                lines.append("")
                lines.append(f"> {content}")
                lines.append("")

        return "\n".join(lines)

    def _build_validation_section(self) -> str:
        """Build the validation results section."""
        validations = self.components.validation_results

        if not validations:
            return ""

        lines = [
            "---",
            "",
            "## 3. VALIDATION RESULTS",
            "",
        ]

        for validator_name, result in validations.items():
            passed = result.get("passed", True)
            score = result.get("score", 1.0)
            status = "PASS" if passed else "FAIL"

            lines.append(f"### {validator_name}")
            lines.append(f"**Status:** {status} | **Score:** {score:.0%}")
            lines.append("")

            # Summary
            summary = result.get("summary", "")
            if summary:
                lines.append(f"*{summary}*")
                lines.append("")

            # Findings
            findings = result.get("findings", [])
            if findings:
                lines.append("**Findings:**")
                for finding in findings[:5]:  # Top 5 findings
                    severity = finding.get("severity", "info")
                    message = finding.get("message", "")
                    suggestion = finding.get("suggestion", "")

                    icon = {
                        "info": "i",
                        "warning": "!",
                        "error": "X",
                        "critical": "!!!"
                    }.get(severity, "?")

                    lines.append(f"- [{icon}] {message}")
                    if suggestion:
                        lines.append(f"  - *Suggestion: {suggestion}*")
                lines.append("")

            # Details
            details = result.get("details", {})
            if details and self.components.include_debug:
                lines.append("**Details:**")
                for key, value in details.items():
                    if isinstance(value, list) and len(value) > 3:
                        value = value[:3] + ["..."]
                    lines.append(f"- {key}: {value}")
                lines.append("")

        return "\n".join(lines)

    def _build_risk_section(self) -> str:
        """Build the risk assessment section."""
        analysis = self.components.pre_analysis

        if not analysis:
            return ""

        lines = [
            "---",
            "",
            "## 4. RISK ASSESSMENT",
            "",
        ]

        # Risk level
        lines.append(f"**Overall Risk Level:** {analysis.risk_level.upper()}")
        lines.append("")

        # Detected intents
        if analysis.detected_intents:
            lines.append("### Detected Intents")
            for intent in analysis.detected_intents[:5]:
                lines.append(f"- **{intent.intent}:** {intent.confidence:.0%} confidence")
            lines.append("")

        # Detected domains
        if analysis.detected_domains:
            lines.append("### Affected Domains")
            lines.append(", ".join(analysis.detected_domains))
            lines.append("")

        # Risk flags
        if analysis.risk_flags:
            lines.append("### Risk Flags")
            for flag in analysis.risk_flags:
                lines.append(f"- {flag}")
            lines.append("")

        # Priority rule types
        if analysis.priority_rule_types:
            lines.append("### Priority Testing Areas")
            for rule_type in analysis.priority_rule_types:
                lines.append(f"- {rule_type.replace('_', ' ').title()}")
            lines.append("")

        return "\n".join(lines)

    def _build_request_section(self) -> str:
        """Build the QA analysis request section."""
        lines = [
            "---",
            "",
            "## 5. QA ANALYSIS REQUEST",
            "",
            "Based on the story details, retrieved knowledge, and validation results above,",
            "please provide a comprehensive QA analysis including:",
            "",
            "### A. Gap Analysis",
            "- Missing requirements or unclear specifications",
            "- Ambiguities in acceptance criteria",
            "- Unstated assumptions",
            "",
            "### B. Edge Cases",
            "- Boundary conditions",
            "- Error scenarios",
            "- Concurrent operations",
            "- Data edge cases (null, empty, max values)",
            "",
            "### C. Test Scenarios (BDD Format)",
            "Generate test cases covering:",
            "- Happy path scenarios",
            "- Negative/error scenarios",
            "- Boundary conditions",
            "- State transitions (if applicable)",
            "- Financial calculations (if applicable)",
            "- Integration points",
            "",
            "Format: Given/When/Then",
            "",
            "### D. Risk-Based Test Prioritization",
            "- Critical tests (must pass before release)",
            "- High priority tests",
            "- Medium priority tests",
            "- Nice-to-have tests",
            "",
            "### E. Cross-Module Impact",
            "- Identify tests needed for dependent modules",
            "- Regression areas to cover",
            "- Integration test requirements",
        ]

        return "\n".join(lines)

    def _build_footer(self) -> str:
        """Build the prompt footer."""
        lines = [
            "---",
            "",
            "*Generated by Local RAG Brain*",
            f"*Timestamp: {datetime.now().isoformat()}*",
            "*No cloud AI services used - 100% local processing*",
        ]

        return "\n".join(lines)

    def _format_content(self, content: str) -> str:
        """Format content for markdown display."""
        if not content:
            return "*No content*"

        # Preserve markdown but escape certain characters
        content = content.strip()

        # Ensure proper line breaks
        content = content.replace("\r\n", "\n")

        return content

    def save(self, output_path: Optional[Path] = None) -> Path:
        """
        Save the built prompt to a file.

        Args:
            output_path: Optional custom output path.

        Returns:
            Path to the saved file.
        """
        prompt_content = self.build()

        if output_path is None:
            story_key = self.components.story.get("key", "unknown")
            filename = f"{self.config.PROMPT_FILE_PREFIX}{story_key}.md"
            output_path = self.config.PROMPTS_DIR / filename

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        output_path.write_text(prompt_content, encoding='utf-8')

        return output_path

    def to_clipboard(self) -> bool:
        """
        Copy the built prompt to clipboard.

        Returns:
            True if successful, False otherwise.
        """
        try:
            import subprocess

            prompt_content = self.build()

            # Try pbcopy (macOS)
            try:
                process = subprocess.Popen(
                    ['pbcopy'],
                    stdin=subprocess.PIPE
                )
                process.communicate(prompt_content.encode('utf-8'))
                return process.returncode == 0
            except FileNotFoundError:
                pass

            # Try xclip (Linux)
            try:
                process = subprocess.Popen(
                    ['xclip', '-selection', 'clipboard'],
                    stdin=subprocess.PIPE
                )
                process.communicate(prompt_content.encode('utf-8'))
                return process.returncode == 0
            except FileNotFoundError:
                pass

            return False

        except Exception:
            return False

    def get_summary(self) -> str:
        """
        Get a brief summary of the prompt components.

        Returns:
            Summary string.
        """
        story = self.components.story
        chunks = self.components.retrieved_chunks
        validations = self.components.validation_results
        analysis = self.components.pre_analysis

        lines = [
            "Prompt Summary:",
            f"  Story: {story.get('key', 'N/A')} - {story.get('title', 'N/A')[:50]}",
            f"  Retrieved Chunks: {len(chunks)}",
            f"  Validators Run: {len(validations)}",
            f"  Risk Level: {analysis.risk_level if analysis else 'N/A'}",
        ]

        return "\n".join(lines)


# Convenience function
def build_prompt_for_story(
    story: Dict[str, Any],
    chunks: List[RetrievalResult],
    pre_analysis: PreAnalysisResult,
    validations: Dict[str, Any],
    save: bool = True,
    debug: bool = False
) -> str:
    """
    Build a complete prompt for a story.

    Args:
        story: Jira story dictionary.
        chunks: Retrieved knowledge chunks.
        pre_analysis: Story pre-analysis results.
        validations: Validation results dictionary.
        save: Whether to save to file.
        debug: Whether to include debug info.

    Returns:
        The built prompt string.
    """
    builder = PromptBuilder()
    builder.set_story(story)
    builder.set_retrieved_context(chunks)
    builder.set_pre_analysis(pre_analysis)
    builder.set_validation_results(validations)
    builder.set_debug_mode(debug)

    prompt = builder.build()

    if save:
        path = builder.save()
        print(f"Prompt saved to: {path}")

    return prompt


if __name__ == "__main__":
    # Quick test
    from .story_pre_analyzer import StoryPreAnalyzer

    # Mock story
    story = {
        "key": "TEST-123",
        "title": "Test Subscription Upgrade",
        "status": "In Progress",
        "priority": "High",
        "description": "Implement subscription upgrade flow",
        "acceptance_criteria": [
            "User can select new plan",
            "Payment is processed",
            "Subscription is updated"
        ]
    }

    # Mock analysis
    analyzer = StoryPreAnalyzer()
    analysis = analyzer.analyze(story)

    # Build prompt
    builder = PromptBuilder()
    builder.set_story(story)
    builder.set_pre_analysis(analysis)
    builder.set_debug_mode(True)

    prompt = builder.build()
    print(prompt[:2000])
    print("\n... (truncated)")
