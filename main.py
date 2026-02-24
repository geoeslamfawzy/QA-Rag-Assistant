#!/usr/bin/env python3
"""
Jira Work Items Manager
Thin CLI entry point — all orchestration is delegated to services.
"""
import sys
import argparse

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from jira_client import JiraClient
from analyzer import IssueAnalyzer
from display import IssueDisplay, AnalysisDisplay
from services import OutputWriter, AnalysisService, TestCaseService

console = Console()


def main():
    """Build the CLI, construct dependencies once, route to handlers."""
    parser = argparse.ArgumentParser(
        description='Jira Work Items Manager - View, analyze, and comment on Jira issues'
    )
    parser.add_argument('--project', type=str, help='Jira project key (e.g., PROJ)')
    parser.add_argument('--jql', type=str, help='JQL query string to filter issues')
    parser.add_argument('--limit', type=int, default=50, help='Maximum issues to fetch (default: 50)')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    list_parser = subparsers.add_parser('list', help='List issues')
    list_parser.add_argument('--analyze', action='store_true', help='Show analysis of issues')

    view_parser = subparsers.add_parser('view', help='View a specific issue')
    view_parser.add_argument('issue_key', type=str, help='Issue key (e.g., PROJ-123)')
    view_parser.add_argument('--analyze', action='store_true', help='Analyze the issue')
    view_parser.add_argument('--comments', action='store_true', help='Show comments')

    comment_parser = subparsers.add_parser('comment', help='Add a comment to an issue')
    comment_parser.add_argument('issue_key', type=str, help='Issue key (e.g., PROJ-123)')
    comment_parser.add_argument('--text', type=str, help='Comment text (prompts if omitted)')

    analyze_parser = subparsers.add_parser('analyze', help='Analyze issues')
    analyze_parser.add_argument('issue_key', type=str, nargs='?', help='Issue key (optional)')

    story_parser = subparsers.add_parser('story', help='Analyze a story (description and AC)')
    story_parser.add_argument('issue_key', type=str, help='Story key (e.g., PROJ-123)')

    tc_parser = subparsers.add_parser('generate-tc', help='Generate test cases for a story')
    tc_parser.add_argument('issue_key', type=str, help='Story key (e.g., PROJ-123)')

    args = parser.parse_args()

    # Construct dependencies once — all handlers receive them via parameters (DIP)
    try:
        client = JiraClient()
    except Exception as e:
        console.print(f"[red]Error initializing Jira client: {e}[/red]")
        console.print("\n[yellow]Please check your .env file:[/yellow]")
        console.print("  JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN must be set")
        sys.exit(1)

    analyzer = IssueAnalyzer()
    writer = OutputWriter()
    issue_display = IssueDisplay(console)
    analysis_display = AnalysisDisplay(console)
    analysis_service = AnalysisService(client, analyzer, writer)
    tc_service = TestCaseService(client, writer)

    if args.command == 'list':
        handle_list(client, analysis_service, issue_display, analysis_display, args)
    elif args.command == 'view':
        handle_view(client, analysis_service, issue_display, analysis_display, args)
    elif args.command == 'comment':
        handle_comment(client, args)
    elif args.command in ('analyze', 'story'):
        handle_analyze(analysis_service, issue_display, analysis_display, args)

    elif args.command == 'generate-tc':
        handle_generate_tc(tc_service, args)
    else:
        interactive_mode(client, analysis_service, issue_display, analysis_display)


# ---------------------------------------------------------------------------
# Command handlers — thin routing only, no business logic
# ---------------------------------------------------------------------------

def handle_list(client, analysis_service, issue_display, analysis_display, args):
    jql = args.jql
    project = args.project or client.project_key
    if project and not jql:
        jql = f"project = {project}"

    issues = client.get_issues(jql=jql, max_results=args.limit)
    issue_display.display_issues(issues)

    if args.analyze and issues:
        result = analysis_service.analyze_bulk(jql, args.limit)
        if result:
            analysis_display.display_analysis(result['analysis'])


def handle_view(client, analysis_service, issue_display, analysis_display, args):
    issue = client.get_issue(args.issue_key)
    if not issue:
        console.print(f"[red]Issue {args.issue_key} not found[/red]")
        return

    issue_display.display_issue_details(issue)

    if args.comments:
        issue_display.display_comments(client.get_comments(args.issue_key))

    if args.analyze:
        result = analysis_service.get_single_insights(args.issue_key)
        if result:
            analysis_display.display_issue_insights(result['insights'], args.issue_key)


def handle_comment(client, args):
    comment_text = args.text or Prompt.ask("Enter your comment")
    if not comment_text:
        console.print("[red]Comment cannot be empty[/red]")
        return
    client.add_comment(args.issue_key, comment_text)


def handle_analyze(analysis_service, issue_display, analysis_display, args):
    if args.issue_key:
        result = analysis_service.analyze_story(args.issue_key)
        if not result:
            console.print(f"[red]Issue {args.issue_key} not found[/red]")
            return
        issue_display.display_issue_details(result['issue'])
        analysis_display.display_story_analysis(result['analysis'], args.issue_key)
        console.print(f"[green]✓[/green] Analysis written to [bold]{result['saved_path']}[/bold]")
    else:
        result = analysis_service.analyze_bulk(args.jql, args.limit)
        if result:
            analysis_display.display_analysis(result['analysis'])
        else:
            console.print("[yellow]No issues to analyze[/yellow]")


def handle_generate_tc(tc_service, args):
    result = tc_service.generate(args.issue_key)
    if not result:
        console.print(f"[red]Issue {args.issue_key} not found[/red]")
        return
    console.print(f"[green]✓[/green] Test cases written to [bold]{result['saved_path']}[/bold]")


_ISSUE_KEY_PROMPT = "Issue key (e.g., PROJ-123)"


# ---------------------------------------------------------------------------
# Interactive mode — each menu choice is its own function (SRP)
# ---------------------------------------------------------------------------

def interactive_mode(client, analysis_service, issue_display, analysis_display):
    console.print(Panel.fit(
        "[bold cyan]Jira Work Items Manager[/bold cyan]\n"
        "Interactive mode - Choose an action",
        border_style="cyan"
    ))
    actions = {
        "1": lambda: _interactive_list(client, analysis_service, issue_display, analysis_display),
        "2": lambda: _interactive_view(client, analysis_service, issue_display, analysis_display),
        "3": lambda: _interactive_comment(client),
        "4": lambda: _interactive_bulk_analyze(analysis_service, analysis_display),
        "5": lambda: _interactive_single_insights(analysis_service, analysis_display),
    }
    while True:
        console.print("\n[bold]Available actions:[/bold]")
        console.print("1. List issues")
        console.print("2. View issue details")
        console.print("3. Add comment to issue")
        console.print("4. Analyze issues")
        console.print("5. Analyze single issue")
        console.print("6. Exit")
        choice = Prompt.ask("\nSelect an action", choices=list(actions) + ["6"], default="1")
        if choice == "6":
            console.print("[green]Goodbye![/green]")
            break
        actions[choice]()


def _interactive_list(client, analysis_service, issue_display, analysis_display):
    project = Prompt.ask("Project key (press Enter for all)", default="")
    jql = Prompt.ask("JQL query (press Enter to skip)", default="")
    limit = _prompt_int("Max results", default=50)
    if project and not jql:
        jql = f"project = {project}"
    issues = client.get_issues(jql=jql or None, max_results=limit)
    issue_display.display_issues(issues)
    if issues and Confirm.ask("\nAnalyze these issues?"):
        result = analysis_service.analyze_bulk(jql or None, limit)
        if result:
            analysis_display.display_analysis(result['analysis'])


def _interactive_view(client, analysis_service, issue_display, analysis_display):
    issue_key = Prompt.ask(_ISSUE_KEY_PROMPT)
    issue = client.get_issue(issue_key)
    if not issue:
        return
    issue_display.display_issue_details(issue)
    if Confirm.ask("\nShow comments?"):
        issue_display.display_comments(client.get_comments(issue_key))
    if Confirm.ask("\nAnalyze this issue?"):
        result = analysis_service.get_single_insights(issue_key)
        if result:
            analysis_display.display_issue_insights(result['insights'], issue_key)


def _interactive_comment(client):
    issue_key = Prompt.ask(_ISSUE_KEY_PROMPT)
    comment = Prompt.ask("Enter your comment")
    if comment:
        client.add_comment(issue_key, comment)


def _interactive_bulk_analyze(analysis_service, analysis_display):
    project = Prompt.ask("Project key (press Enter for all)", default="")
    jql = Prompt.ask("JQL query (press Enter to skip)", default="")
    limit = _prompt_int("Max results", default=50)
    if project and not jql:
        jql = f"project = {project}"
    result = analysis_service.analyze_bulk(jql or None, limit)
    if result:
        analysis_display.display_analysis(result['analysis'])
    else:
        console.print("[yellow]No issues to analyze[/yellow]")


def _interactive_single_insights(analysis_service, analysis_display):
    issue_key = Prompt.ask(_ISSUE_KEY_PROMPT)
    result = analysis_service.get_single_insights(issue_key)
    if result:
        analysis_display.display_issue_insights(result['insights'], issue_key)


def _prompt_int(label: str, default: int) -> int:
    raw = Prompt.ask(label, default=str(default))
    try:
        return int(raw)
    except ValueError:
        return default


if __name__ == '__main__':
    main()
