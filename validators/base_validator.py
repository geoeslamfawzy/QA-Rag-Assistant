"""
Base Validator Module

Abstract base class for all validators.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Validation finding severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationFinding:
    """A single validation finding."""
    message: str
    severity: Severity
    rule_id: Optional[str] = None
    location: Optional[str] = None
    suggestion: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "message": self.message,
            "severity": self.severity.value,
            "rule_id": self.rule_id,
            "location": self.location,
            "suggestion": self.suggestion,
            "context": self.context
        }


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    validator_name: str
    passed: bool
    findings: List[ValidationFinding] = field(default_factory=list)
    summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    score: float = 1.0  # 0-1, where 1 is fully passing

    def add_finding(
        self,
        message: str,
        severity: Severity,
        rule_id: Optional[str] = None,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
        **context
    ):
        """Add a validation finding."""
        self.findings.append(ValidationFinding(
            message=message,
            severity=severity,
            rule_id=rule_id,
            location=location,
            suggestion=suggestion,
            context=context
        ))

    def add_info(self, message: str, **kwargs):
        """Add an info-level finding."""
        self.add_finding(message, Severity.INFO, **kwargs)

    def add_warning(self, message: str, **kwargs):
        """Add a warning-level finding."""
        self.add_finding(message, Severity.WARNING, **kwargs)

    def add_error(self, message: str, **kwargs):
        """Add an error-level finding."""
        self.add_finding(message, Severity.ERROR, **kwargs)

    def add_critical(self, message: str, **kwargs):
        """Add a critical-level finding."""
        self.add_finding(message, Severity.CRITICAL, **kwargs)

    @property
    def error_count(self) -> int:
        """Count of error-level findings."""
        return sum(
            1 for f in self.findings
            if f.severity in [Severity.ERROR, Severity.CRITICAL]
        )

    @property
    def warning_count(self) -> int:
        """Count of warning-level findings."""
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "validator_name": self.validator_name,
            "passed": self.passed,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "details": self.details,
            "score": self.score,
            "error_count": self.error_count,
            "warning_count": self.warning_count
        }

    def format(self) -> str:
        """Format result for display."""
        lines = []
        status = "PASS" if self.passed else "FAIL"
        lines.append(f"[{self.validator_name}] {status} (score: {self.score:.0%})")
        lines.append(f"  {self.summary}")

        if self.findings:
            lines.append(f"  Findings ({len(self.findings)}):")
            for finding in self.findings:
                icon = {
                    Severity.INFO: "i",
                    Severity.WARNING: "!",
                    Severity.ERROR: "X",
                    Severity.CRITICAL: "!!!"
                }.get(finding.severity, "?")

                lines.append(f"    [{icon}] {finding.message}")
                if finding.suggestion:
                    lines.append(f"        Suggestion: {finding.suggestion}")

        return "\n".join(lines)


class BaseValidator(ABC):
    """
    Abstract base class for validators.

    Validators analyze stories against knowledge base content
    to identify gaps, issues, and areas of concern.
    """

    def __init__(self, name: str = "BaseValidator"):
        """
        Initialize the validator.

        Args:
            name: Name of the validator.
        """
        self.name = name

    @abstractmethod
    def validate(
        self,
        story: Dict[str, Any],
        knowledge_context: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate a story against knowledge context.

        Args:
            story: Story dictionary with title, description, acceptance_criteria.
            knowledge_context: Retrieved knowledge chunks.

        Returns:
            ValidationResult with findings.
        """
        pass

    def _extract_story_text(self, story: Dict[str, Any]) -> str:
        """
        Extract full text from story.

        Args:
            story: Story dictionary.

        Returns:
            Combined story text.
        """
        parts = []

        if story.get("title"):
            parts.append(story["title"])

        if story.get("description"):
            parts.append(story["description"])

        if story.get("acceptance_criteria"):
            ac = story["acceptance_criteria"]
            if isinstance(ac, list):
                parts.extend(ac)
            else:
                parts.append(str(ac))

        return "\n\n".join(parts)

    def _create_result(
        self,
        passed: bool = True,
        summary: str = "",
        score: float = 1.0
    ) -> ValidationResult:
        """
        Create a new ValidationResult.

        Args:
            passed: Whether validation passed.
            summary: Summary message.
            score: Validation score (0-1).

        Returns:
            ValidationResult instance.
        """
        return ValidationResult(
            validator_name=self.name,
            passed=passed,
            summary=summary,
            score=score
        )
