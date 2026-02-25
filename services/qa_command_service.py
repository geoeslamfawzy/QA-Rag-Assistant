"""
QA Command Service Module

Unified orchestrator for QA-specific commands.
All commands share RAGContextBuilder pipeline and template-based output.
Defect commands now export Jira-ready CSV files.
Supports --post flag for posting findings as Jira comments.
"""
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path

from builders import DefectBuilder, DefectBuildOptions
from exporters import DefectCSVExporter, StoryDefectCSVExporter
from jira_client import JiraClient
from models.defect import Defect
from services.rag_context_builder import RAGContextBuilder, RAGContext
from services.output_writer import OutputWriter
from templates import (
    ReviewTemplate,
    AmbiguityTemplate,
    StoryDefectTemplate,
    DefectTemplate,
)


class QACommandType(Enum):
    """Supported QA command types."""
    REVIEW = "review"
    AMBIGUITY = "get-ambiguity"
    STORY_DEFECT = "write-story-defect"
    DEFECT = "write-defect"


class QACommandService:
    """
    Orchestrates QA commands using shared RAGContextBuilder.

    Design:
    - Single entry point for all 4 commands
    - Delegates to templates for output formatting
    - No duplication of retrieval/validation logic
    - Supports --post flag for Jira comment posting
    """

    def __init__(
        self,
        rag_builder: RAGContextBuilder,
        writer: OutputWriter,
        jira_client: Optional[JiraClient] = None,
    ):
        self._rag_builder = rag_builder
        self._writer = writer
        self._jira_client = jira_client

        # Defect building and export
        self._defect_builder = DefectBuilder()
        self._defect_csv_exporter = DefectCSVExporter()
        self._story_defect_csv_exporter = StoryDefectCSVExporter()

        # Template registry - maps command type to template instance
        self._templates = {
            QACommandType.REVIEW: ReviewTemplate(),
            QACommandType.AMBIGUITY: AmbiguityTemplate(),
            QACommandType.STORY_DEFECT: StoryDefectTemplate(),
            QACommandType.DEFECT: DefectTemplate(),
        }

    def execute(
        self,
        command_type: QACommandType,
        issue_key: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a QA command.

        Args:
            command_type: Type of command to execute
            issue_key: Jira issue key
            options: Command-specific options (e.g., violation_type)

        Returns:
            Result dict with saved_path, or None if story not found
        """
        options = options or {}

        # Step 1: Build RAG context (shared pipeline)
        rag_context = self._rag_builder.build(issue_key)
        if not rag_context:
            return None

        # Step 2: Get template for command type
        template = self._templates[command_type]

        # Step 3: Render template with RAG context
        content = template.render(rag_context, options)

        # Step 4: Write output using appropriate method
        saved_path = self._write_output(command_type, issue_key, content)

        return {
            "issue_key": issue_key,
            "command": command_type.value,
            "rag_context": rag_context,
            "saved_path": saved_path,
        }

    def _write_output(self, command_type: QACommandType, issue_key: str, content: str) -> Path:
        """Route to appropriate OutputWriter method."""
        writers = {
            QACommandType.REVIEW: self._writer.write_review,
            QACommandType.AMBIGUITY: self._writer.write_ambiguity,
            QACommandType.STORY_DEFECT: self._writer.write_story_defect,
            QACommandType.DEFECT: self._writer.write_defect,
        }
        return writers[command_type](issue_key, content)

    # Convenience methods for each command
    def review(
        self,
        issue_key: str,
        post_comment: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Review test cases and detect coverage gaps.

        Args:
            issue_key: Jira issue key
            post_comment: If True, RAG context is included for comment posting

        Returns:
            Result dict with saved_path and optionally rag_context
        """
        result = self.execute(QACommandType.REVIEW, issue_key)
        # rag_context is already included in execute() return value
        return result

    def get_ambiguity(
        self,
        issue_key: str,
        post_comment: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Detect unclear requirements.

        Args:
            issue_key: Jira issue key
            post_comment: If True, RAG context is included for comment posting

        Returns:
            Result dict with saved_path and optionally rag_context
        """
        result = self.execute(QACommandType.AMBIGUITY, issue_key)
        # rag_context is already included in execute() return value
        return result

    def write_story_defect(
        self,
        issue_key: str,
        issue_type: str = "missing_ac",
        export_csv: bool = True,
        export_markdown: bool = True,
        custom_summary: Optional[str] = None,
        custom_description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate defect for requirement issue.

        Args:
            issue_key: Jira issue key
            issue_type: Type of issue (missing_ac, unclear_requirement, incomplete_story)
            export_csv: Whether to export Jira-ready CSV (default: True)
            export_markdown: Whether to export markdown (default: True)
            custom_summary: Custom defect summary (overrides auto-generated)
            custom_description: Custom defect description (overrides auto-generated)

        Returns:
            Result dict with csv_path, md_path (optional), defect, or None if not found
        """
        # Step 1: Build RAG context
        rag_context = self._rag_builder.build(issue_key)
        if not rag_context:
            return None

        options = DefectBuildOptions(
            issue_type=issue_type,
            defect_type="story_quality",
            custom_summary=custom_summary,
            custom_description=custom_description,
        )

        # Step 2: Build Defect object
        defect = self._defect_builder.build_story_defect(rag_context, options)

        result = {
            "issue_key": issue_key,
            "command": "write-story-defect",
            "rag_context": rag_context,
            "defect": defect,
        }

        # Step 3: Export CSV using StoryDefectCSVExporter (outputs to story-defects/)
        if export_csv:
            csv_path = self._story_defect_csv_exporter.export(defect, issue_key)
            result["csv_path"] = csv_path
            result["saved_path"] = csv_path

        # Step 4: Export Markdown (optional/legacy)
        if export_markdown:
            template = self._templates[QACommandType.STORY_DEFECT]
            content = template.render(rag_context, {"issue_type": issue_type})
            md_path = self._writer.write_story_defect(issue_key, content)
            result["md_path"] = md_path
            if not export_csv:
                result["saved_path"] = md_path

        return result

    def write_defect(
        self,
        issue_key: str,
        violation_type: str = "rule",
        export_csv: bool = True,
        export_markdown: bool = True,
        custom_summary: Optional[str] = None,
        custom_description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate defect for rule/state/financial violation.

        Args:
            issue_key: Jira issue key
            violation_type: Type of violation (rule, state, financial, cross_dep)
            export_csv: Whether to export Jira-ready CSV (default: True)
            export_markdown: Whether to export markdown (default: True)
            custom_summary: Custom defect summary (overrides auto-generated)
            custom_description: Custom defect description (overrides auto-generated)

        Returns:
            Result dict with csv_path, md_path (optional), defect, or None if not found
        """
        # Step 1: Build RAG context
        rag_context = self._rag_builder.build(issue_key)
        if not rag_context:
            return None

        options = DefectBuildOptions(
            violation_type=violation_type,
            defect_type="violation",
            custom_summary=custom_summary,
            custom_description=custom_description,
        )

        # Step 2: Build Defect object
        defect = self._defect_builder.build_violation_defect(rag_context, options)

        result = {
            "issue_key": issue_key,
            "command": "write-defect",
            "rag_context": rag_context,
            "defect": defect,
        }

        # Step 3: Export CSV (primary output)
        if export_csv:
            csv_path = self._defect_csv_exporter.export(defect, issue_key)
            result["csv_path"] = csv_path
            result["saved_path"] = csv_path

        # Step 4: Export Markdown (optional/legacy)
        if export_markdown:
            template = self._templates[QACommandType.DEFECT]
            content = template.render(rag_context, {"violation_type": violation_type})
            md_path = self._writer.write_defect(issue_key, content)
            result["md_path"] = md_path
            if not export_csv:
                result["saved_path"] = md_path

        return result
