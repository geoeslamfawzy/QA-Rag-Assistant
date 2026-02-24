"""
Analysis Display Module

Handles all Rich console rendering of analysis results.
Extracted from IssueAnalyzer to satisfy the Single Responsibility Principle:
IssueAnalyzer owns analysis logic; AnalysisDisplay owns presentation.
"""
from typing import Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel


class AnalysisDisplay:
    """Renders analysis results to the terminal using Rich."""

    def __init__(self, console: Optional[Console] = None):
        self._console = console or Console()

    def display_analysis(self, analysis: Dict[str, Any]) -> None:
        """Render bulk issue analysis (counts by status, priority, type, assignee)."""
        if not analysis:
            self._console.print("[yellow]No analysis data available[/yellow]")
            return

        self._console.print("\n[bold cyan]Issue Analysis[/bold cyan]\n")
        self._console.print(f"[bold]Total Issues:[/bold] {analysis['total_issues']}")
        self._console.print(f"[bold]Unassigned Issues:[/bold] {analysis['unassigned_count']}\n")

        self._print_panel("By Status", "green", [
            f"{status}: {count}" for status, count in analysis['by_status'].items()
        ])
        self._print_panel("By Priority", "red", [
            f"{priority}: {count}" for priority, count in analysis['by_priority'].items()
        ])
        self._print_panel("By Type", "blue", [
            f"{issue_type}: {count}" for issue_type, count in analysis['by_type'].items()
        ])
        self._print_panel("By Assignee (Top 10)", "yellow", [
            f"{assignee}: {count}"
            for assignee, count in analysis['by_assignee'].most_common(10)
        ])

        if analysis['recent_updates']:
            self._console.print("\n[bold]Recently Updated Issues:[/bold]")
            for issue in analysis['recent_updates']:
                self._console.print(f"  • {issue['key']}: {issue['summary'][:60]}...")

    def display_issue_insights(self, insights: Dict[str, Any], issue_key: str) -> None:
        """Render quick insights for a single issue."""
        self._console.print(f"\n[bold cyan]Analysis for {issue_key}[/bold cyan]\n")

        if insights['warnings']:
            self._console.print("[bold red]Warnings:[/bold red]")
            for warning in insights['warnings']:
                self._console.print(f"  • {warning}")

        if insights['suggestions']:
            self._console.print("\n[bold yellow]Suggestions:[/bold yellow]")
            for suggestion in insights['suggestions']:
                self._console.print(f"  • {suggestion}")

        if insights['info']:
            self._console.print("\n[bold blue]Info:[/bold blue]")
            for info in insights['info']:
                self._console.print(f"  • {info}")

        if not any([insights['warnings'], insights['suggestions'], insights['info']]):
            self._console.print("[green]No issues detected[/green]")

    def display_story_analysis(self, analysis: Dict[str, Any], issue_key: str) -> None:
        """Render comprehensive story analysis (completeness, quality, clarity, recommendations)."""
        self._console.print(f"\n[bold cyan]Story Analysis: {issue_key}[/bold cyan]\n")

        completeness = analysis['completeness']
        desc_status = "✓" if completeness['has_description'] else "✗"
        ac_status = "✓" if completeness['has_acceptance_criteria'] else "✗"

        self._console.print("[bold]Completeness:[/bold]")
        self._console.print(
            f"  {desc_status} Description: {completeness['description_adequacy']}"
            f" ({completeness['description_length']} chars)"
        )
        self._console.print(f"  {ac_status} Acceptance Criteria: {completeness['has_acceptance_criteria']}")

        if completeness['has_acceptance_criteria']:
            ac = analysis['acceptance_criteria_analysis']
            self._console.print(f"    • Criteria count: {ac['count']}")
            self._console.print(f"    • Quality: {ac['adequacy']}")

        self._console.print("\n[bold]Quality:[/bold]")
        for strength in analysis['quality']['strengths']:
            self._console.print(f"  ✓ {strength}")
        for issue in analysis['quality']['issues']:
            self._console.print(f"  ⚠  {issue}")

        self._console.print("\n[bold]Clarity:[/bold]")
        for strength in analysis['clarity']['strengths']:
            self._console.print(f"  ✓ {strength}")
        for issue in analysis['clarity']['issues']:
            self._console.print(f"  ⚠  {issue}")

        if analysis['recommendations']:
            self._console.print("\n[bold yellow]Recommendations:[/bold yellow]")
            for rec in analysis['recommendations']:
                self._console.print(f"  {rec}")
        else:
            self._console.print("\n[green]Story looks well-defined![/green]")

    def _print_panel(self, title: str, border_style: str, lines: list) -> None:
        if lines:
            self._console.print(Panel("\n".join(lines), title=title, border_style=border_style))
