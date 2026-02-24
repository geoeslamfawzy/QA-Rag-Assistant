"""
Output Writer Module

Single point of responsibility for all generated file I/O.
All output paths are resolved relative to the project root.
"""
from pathlib import Path
from typing import Optional


class OutputWriter:
    """
    Writes generated output files under the output/ directory.

    Centralises directory creation, path construction, and file writing
    so callers never touch the filesystem directly.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self._base = base_dir or Path(__file__).parent.parent / "output"

    def write_analysis(self, issue_key: str, content: str) -> Path:
        """Write story analysis markdown. Returns the path written."""
        return self._write("analysis", f"analysis-{issue_key}.md", content)

    def write_test_cases(self, issue_key: str, content: str) -> Path:
        """Write BDD test case markdown. Returns the path written."""
        return self._write("test-suite", f"test-cases-{issue_key}.md", content)

    def write_prompt(self, issue_key: str, content: str) -> Path:
        """Write RAG-generated prompt markdown. Returns the path written."""
        return self._write("prompts", f"prompt-{issue_key}.md", content)

    def _write(self, subdir: str, filename: str, content: str) -> Path:
        out_dir = self._base / subdir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        out_path.write_text(content, encoding="utf-8")
        return out_path
