"""
Issue Display Module

Handles all Rich console rendering of Jira issue data.
Extracted from JiraClient to satisfy the Single Responsibility Principle:
JiraClient owns data access; IssueDisplay owns presentation.
"""
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.table import Table


class IssueDisplay:
    """Renders Jira issue data to the terminal using Rich."""

    def __init__(self, console: Optional[Console] = None):
        self._console = console or Console()

    def display_issues(self, issues: List[Dict[str, Any]]) -> None:
        """Render a formatted table of issues."""
        if not issues:
            self._console.print("[yellow]No issues found[/yellow]")
            return

        table = Table(title="Jira Issues", show_header=True, header_style="bold magenta")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Summary", style="white")
        table.add_column("Status", style="green")
        table.add_column("Assignee", style="yellow")
        table.add_column("Priority", style="red")
        table.add_column("Type", style="blue")

        for issue in issues:
            summary = issue['summary']
            table.add_row(
                issue['key'],
                summary[:50] + '...' if len(summary) > 50 else summary,
                issue['status'],
                issue['assignee'],
                issue['priority'],
                issue['issue_type'],
            )

        self._console.print(table)

    def display_issue_details(self, issue: Dict[str, Any]) -> None:
        """Render full details of a single issue."""
        self._console.print(f"\n[bold cyan]Issue: {issue['key']}[/bold cyan]")
        self._console.print(f"[bold]Summary:[/bold] {issue['summary']}")
        self._console.print(f"[bold]Status:[/bold] {issue['status']}")
        self._console.print(f"[bold]Type:[/bold] {issue['issue_type']}")
        self._console.print(f"[bold]Priority:[/bold] {issue['priority']}")
        self._console.print(f"[bold]Assignee:[/bold] {issue['assignee']}")
        self._console.print(f"[bold]Reporter:[/bold] {issue['reporter']}")
        self._console.print(f"[bold]Created:[/bold] {issue['created']}")
        self._console.print(f"[bold]Updated:[/bold] {issue['updated']}")
        self._console.print(f"[bold]URL:[/bold] {issue['url']}")
        self._console.print(f"\n[bold]Description:[/bold]\n{issue['description']}\n")
        if issue.get('acceptance_criteria'):
            self._console.print(f"[bold]Acceptance Criteria:[/bold]\n{issue['acceptance_criteria']}\n")

    def display_comments(self, comments: List[Dict[str, Any]]) -> None:
        """Render comments for an issue."""
        if not comments:
            self._console.print("\n[yellow]No comments found[/yellow]")
            return
        self._console.print("\n[bold]Comments:[/bold]")
        for i, comment in enumerate(comments, 1):
            self._console.print(
                f"\n[cyan]Comment {i} by {comment['author']} ({comment['created']}):[/cyan]"
            )
            self._console.print(comment['body'])
