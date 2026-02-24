"""
QA Command Service Module

Unified orchestrator for QA-specific commands.
All commands share RAGContextBuilder pipeline and template-based output.
"""
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path

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
    """

    def __init__(
        self,
        rag_builder: RAGContextBuilder,
        writer: OutputWriter,
    ):
        self._rag_builder = rag_builder
        self._writer = writer

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
    def review(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Review test cases and detect coverage gaps."""
        return self.execute(QACommandType.REVIEW, issue_key)

    def get_ambiguity(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Detect unclear requirements."""
        return self.execute(QACommandType.AMBIGUITY, issue_key)

    def write_story_defect(
        self,
        issue_key: str,
        issue_type: str = "missing_ac"
    ) -> Optional[Dict[str, Any]]:
        """Generate defect for requirement issue."""
        return self.execute(
            QACommandType.STORY_DEFECT,
            issue_key,
            {"issue_type": issue_type}
        )

    def write_defect(
        self,
        issue_key: str,
        violation_type: str = "rule"
    ) -> Optional[Dict[str, Any]]:
        """Generate defect for rule/state/financial violation."""
        return self.execute(
            QACommandType.DEFECT,
            issue_key,
            {"violation_type": violation_type}
        )
