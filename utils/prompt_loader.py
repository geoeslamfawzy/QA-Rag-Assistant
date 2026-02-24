"""
Prompt Loader Utility

Loads markdown prompt templates and injects dynamic data.
Supports placeholder replacement with {{VARIABLE}} syntax.
"""
from pathlib import Path
from typing import Dict, Any
import re


class PromptTemplate:
    """Represents a loaded prompt template with placeholder injection."""

    def __init__(self, content: str, source_path: Path):
        self._content = content
        self._source = source_path
        self._injections: Dict[str, str] = {}

    def inject(self, placeholder: str, value: Any) -> 'PromptTemplate':
        """
        Inject a value for a placeholder. Returns self for chaining.

        Args:
            placeholder: The placeholder name (without braces)
            value: The value to inject (will be converted to string)

        Returns:
            Self for method chaining
        """
        self._injections[placeholder] = str(value) if value is not None else ""
        return self

    def inject_section(self, placeholder: str, lines: list) -> 'PromptTemplate':
        """
        Inject a list of lines as a section.

        Args:
            placeholder: The placeholder name
            lines: List of strings to join with newlines

        Returns:
            Self for method chaining
        """
        self._injections[placeholder] = "\n".join(str(line) for line in lines)
        return self

    def inject_if(self, placeholder: str, value: Any, condition: bool) -> 'PromptTemplate':
        """
        Conditionally inject a value.

        Args:
            placeholder: The placeholder name
            value: The value to inject
            condition: Only inject if True

        Returns:
            Self for method chaining
        """
        if condition:
            self.inject(placeholder, value)
        return self

    def render(self) -> str:
        """
        Render the template with all injections applied.

        Returns:
            Rendered template string with placeholders replaced
        """
        result = self._content

        # Replace all injected placeholders
        for placeholder, value in self._injections.items():
            pattern = r"\{\{" + re.escape(placeholder) + r"\}\}"
            result = re.sub(pattern, value, result)

        # Remove any remaining uninjected placeholders (clean output)
        result = re.sub(r"\{\{[A-Z_]+\}\}", "", result)

        # Clean up multiple consecutive blank lines
        result = re.sub(r'\n{3,}', '\n\n', result)

        return result.strip()

    @property
    def source(self) -> Path:
        """Return the source file path."""
        return self._source


class PromptLoader:
    """
    Loads prompt templates from qa-assistant/ directory.

    Usage:
        template = PromptLoader.load("review.prompt.md")
        template.inject("STORY_KEY", "CMB-32860")
        output = template.render()
    """

    _BASE_DIR = Path(__file__).parent.parent / "qa-assistant"

    @classmethod
    def load(cls, template_name: str) -> PromptTemplate:
        """
        Load a prompt template by name.

        Args:
            template_name: Name of template file (e.g., "review.prompt.md")

        Returns:
            PromptTemplate instance ready for injection

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        path = cls._BASE_DIR / template_name
        if not path.exists():
            raise FileNotFoundError(
                f"Prompt template not found: {path}\n"
                f"Expected location: {cls._BASE_DIR}"
            )

        content = path.read_text(encoding="utf-8")
        return PromptTemplate(content, path)

    @classmethod
    def load_with_common(cls, template_name: str) -> PromptTemplate:
        """
        Load a template and append common footer.

        Args:
            template_name: Name of main template file

        Returns:
            PromptTemplate with common footer appended
        """
        template = cls.load(template_name)
        try:
            common = cls.load("_common.prompt.md")
            template._content += "\n\n" + common._content
        except FileNotFoundError:
            pass  # Common footer is optional
        return template

    @classmethod
    def exists(cls, template_name: str) -> bool:
        """Check if a template file exists."""
        return (cls._BASE_DIR / template_name).exists()

    @classmethod
    def list_templates(cls) -> list:
        """List all available prompt templates."""
        return [f.name for f in cls._BASE_DIR.glob("*.prompt.md")]
