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
class GroundingInfo:
    """Grounding verification information for prompts."""
    is_grounded: bool = True
    grounding_score: float = 1.0
    extracted_rule_ids: List[str] = field(default_factory=list)
    required_rule_ids: List[str] = field(default_factory=list)
    missing_rule_ids: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class PromptComponents:
    """Components assembled into the final prompt."""
    story: Dict[str, Any] = field(default_factory=dict)
    retrieved_chunks: List[RetrievalResult] = field(default_factory=list)
    pre_analysis: Optional[PreAnalysisResult] = None
    validation_results: Dict[str, Any] = field(default_factory=dict)
    grounding: Optional[GroundingInfo] = None
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

    def set_grounding(self, grounding: Optional[GroundingInfo]) -> 'PromptBuilder':
        """
        Set grounding verification results.

        Args:
            grounding: GroundingInfo from RAG context builder.

        Returns:
            Self for chaining.
        """
        self.components.grounding = grounding
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

        # Grounding Verification (shows extracted rules and warnings)
        sections.append(self._build_grounding_section())

        # Validation Results
        sections.append(self._build_validation_section())

        # Risk Assessment
        sections.append(self._build_risk_section())

        # QA Analysis Request (now with rule-specific recommendations)
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

    def _build_grounding_section(self) -> str:
        """Build the grounding verification section."""
        grounding = self.components.grounding

        if not grounding:
            return ""

        lines = [
            "---",
            "",
            "## GROUNDING VERIFICATION",
            "",
        ]

        # Grounding status
        status = "GROUNDED" if grounding.is_grounded else "WEAK GROUNDING"
        score_percent = f"{grounding.grounding_score:.0%}"
        lines.append(f"**Status:** {status} ({score_percent})")
        lines.append("")

        # Extracted rules (what the system found)
        if grounding.extracted_rule_ids:
            lines.append("### Extracted Rule Citations")
            lines.append("*Rules found in retrieved knowledge context:*")
            lines.append("")
            for rule_id in sorted(grounding.extracted_rule_ids)[:20]:  # Top 20
                lines.append(f"- `{rule_id}`")
            lines.append("")

        # Required rules (what should be there)
        if grounding.required_rule_ids:
            lines.append("### Required Rules (Based on Keywords)")
            lines.append("*Rules that MUST be cited based on story content:*")
            lines.append("")
            for rule_id in grounding.required_rule_ids:
                status_icon = "" if rule_id in grounding.extracted_rule_ids else " **MISSING**"
                lines.append(f"- `{rule_id}`{status_icon}")
            lines.append("")

        # Warnings
        if grounding.warnings:
            lines.append("### Grounding Warnings")
            for warning in grounding.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)

    def _build_request_section(self) -> str:
        """
        Build the QA analysis request section.

        Now includes RULE-SPECIFIC test recommendations instead of generic advice.
        """
        grounding = self.components.grounding
        pre_analysis = self.components.pre_analysis

        lines = [
            "---",
            "",
            "## 5. QA ANALYSIS REQUEST",
            "",
            "Based on the story details, retrieved knowledge, and validation results above,",
            "please provide a comprehensive QA analysis including:",
            "",
        ]

        # Section A: Gap Analysis
        lines.extend([
            "### A. Gap Analysis",
            "- Missing requirements or unclear specifications",
            "- Ambiguities in acceptance criteria",
            "- Unstated assumptions",
            "",
        ])

        # Section B: Rule-Specific Test Cases (REPLACING GENERIC ADVICE)
        lines.append("### B. Rule-Based Test Cases")
        lines.append("*Generate test cases that validate these specific business rules:*")
        lines.append("")

        # Add rule-specific test recommendations based on extracted rules
        if grounding and grounding.extracted_rule_ids:
            rule_tests = self._generate_rule_specific_tests(grounding.extracted_rule_ids)
            for test in rule_tests[:10]:  # Top 10 rule-based tests
                lines.append(f"- {test}")
            lines.append("")
        else:
            lines.append("- Verify all applicable business rules from knowledge base")
            lines.append("")

        # Section C: Edge Cases
        lines.extend([
            "### C. Edge Cases & Boundaries",
            "- Boundary conditions",
            "- Error scenarios",
            "- Concurrent operations",
            "- Data edge cases (null, empty, max values)",
            "",
        ])

        # Section D: Domain-Specific Testing
        lines.append("### D. Domain-Specific Testing")
        if pre_analysis and pre_analysis.detected_domains:
            lines.append(f"*Focus on these affected domains: {', '.join(pre_analysis.detected_domains)}*")
            lines.append("")
            for domain in pre_analysis.detected_domains[:5]:
                lines.append(f"- Verify {domain} module integration")
        else:
            lines.append("- Test cross-module integration")
        lines.append("")

        # Section E: Risk-Based Prioritization
        lines.extend([
            "### E. Risk-Based Test Prioritization",
            "- **P0 Critical:** Tests that verify core business rules",
            "- **P1 High:** Tests that verify financial calculations and state transitions",
            "- **P2 Medium:** Tests that verify edge cases and error handling",
            "- **P3 Low:** Tests that verify UI/UX and non-critical paths",
            "",
        ])

        # Section F: Format requirement
        lines.extend([
            "### F. Test Case Format",
            "Use BDD format: Given/When/Then",
            "Include rule ID citations where applicable (e.g., 'Per FIN-REF-012...')",
        ])

        return "\n".join(lines)

    def _generate_rule_specific_tests(self, rule_ids: List[str]) -> List[str]:
        """
        Generate rule-specific test recommendations.

        Maps rule ID patterns to specific test recommendations.
        """
        tests = []

        for rule_id in rule_ids:
            rule_upper = rule_id.upper()

            # Financial referral rules
            if "FIN-REF" in rule_upper:
                if "012" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify referral rewards EXPIRE immediately on payment plan switch")
                elif "013" in rule_upper or "014" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify NO conversion between free trips and invoice discounts")
                else:
                    tests.append(f"Test {rule_id}: Verify referral reward calculation and application")

            # B2B pricing/budget rules
            elif "FIN-B2B" in rule_upper:
                if "001" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify trip BLOCKED when wallet_balance < estimated_trip_cost")
                elif "005" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify trip BLOCKED when (used + cost) > budget_limit")
                elif "009" in rule_upper or "010" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify plan switch behavior and balance handling")
                else:
                    tests.append(f"Test {rule_id}: Verify financial calculation per rule")

            # Gift card rules
            elif "FIN-GC" in rule_upper:
                tests.append(f"Test {rule_id}: Verify gift card lifecycle and balance handling")

            # Enterprise rules
            elif "RULE-ENT" in rule_upper or "ENT-" in rule_upper:
                if "001" in rule_upper or "010" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify single Super Admin policy enforcement")
                elif "002" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify account access blocked until status = ACTIVE")
                elif "003" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify only INACTIVE enterprises can be deleted")
                else:
                    tests.append(f"Test {rule_id}: Verify enterprise lifecycle rule")

            # Admin rules
            elif "RULE-ADMIN" in rule_upper or "ADMIN-" in rule_upper:
                if "003" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify legal info REQUIRED for invoice generation")
                elif "005" in rule_upper or "006" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify Super Admin promotion/demotion rules")
                elif "007" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify all admin actions are logged (audit trail)")
                elif "008" in rule_upper:
                    tests.append(f"Test {rule_id}: Verify export date range limited to 31 days")
                else:
                    tests.append(f"Test {rule_id}: Verify admin permission rule")

            # User rules
            elif "RULE-USER" in rule_upper or "USER-" in rule_upper:
                tests.append(f"Test {rule_id}: Verify user management rule")

            # Program rules
            elif "RULE-PROG" in rule_upper or "PROG-" in rule_upper:
                tests.append(f"Test {rule_id}: Verify program configuration rule")

            # Trip rules
            elif "RULE-TRIP" in rule_upper or "TRIP-" in rule_upper:
                tests.append(f"Test {rule_id}: Verify trip booking/completion rule")

            # Dependency rules
            elif "DEP-" in rule_upper:
                tests.append(f"Test {rule_id}: Verify cross-module dependency")

            # Generic fallback
            else:
                tests.append(f"Test {rule_id}: Verify rule compliance")

        return tests

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
