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
from services import OutputWriter, AnalysisService, TestCaseService, RAGContextBuilder, QACommandService

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

    # New QA commands using shared RAG pipeline
    review_parser = subparsers.add_parser('review', help='Review test coverage and detect gaps')
    review_parser.add_argument('issue_key', type=str, help='Story key (e.g., PROJ-123)')

    ambiguity_parser = subparsers.add_parser('get-ambiguity', help='Detect unclear requirements')
    ambiguity_parser.add_argument('issue_key', type=str, help='Story key (e.g., PROJ-123)')

    story_defect_parser = subparsers.add_parser('write-story-defect', help='Generate defect for requirement issue')
    story_defect_parser.add_argument('issue_key', type=str, help='Story key (e.g., PROJ-123)')
    story_defect_parser.add_argument(
        '--issue-type', type=str, default='missing_ac',
        choices=['missing_ac', 'unclear_requirement', 'incomplete_story'],
        help='Type of story issue (default: missing_ac)'
    )
    story_defect_parser.add_argument(
        '--summary', type=str, default=None,
        help='Custom defect summary (overrides auto-generated)'
    )
    story_defect_parser.add_argument(
        '--description', type=str, default=None,
        help='Custom defect description (overrides auto-generated)'
    )

    defect_parser = subparsers.add_parser('write-defect', help='Generate defect for rule/state/financial violation')
    defect_parser.add_argument('issue_key', type=str, help='Story key (e.g., PROJ-123)')
    defect_parser.add_argument(
        '--violation-type', type=str, default='rule',
        choices=['rule', 'state', 'financial', 'cross_dep'],
        help='Type of violation (default: rule)'
    )
    defect_parser.add_argument(
        '--summary', type=str, default=None,
        help='Custom defect summary (overrides auto-generated)'
    )
    defect_parser.add_argument(
        '--description', type=str, default=None,
        help='Custom defect description (overrides auto-generated)'
    )

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

    # Initialize RAG context builder for enhanced analysis
    # This enables ./bin/analyze to use the RAG pipeline
    try:
        rag_builder = RAGContextBuilder(jira_client=client)
    except Exception as e:
        console.print(f"[yellow]Warning: RAG context builder unavailable: {e}[/yellow]")
        console.print("[yellow]Falling back to basic analysis mode.[/yellow]")
        rag_builder = None

    analysis_service = AnalysisService(client, analyzer, writer, rag_builder=rag_builder)
    tc_service = TestCaseService(client, writer, rag_builder=rag_builder)

    # Initialize QA command service for new commands (review, get-ambiguity, write-*-defect)
    qa_service = None
    if rag_builder:
        qa_service = QACommandService(rag_builder, writer)

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
    elif args.command == 'review':
        handle_review(qa_service, args)
    elif args.command == 'get-ambiguity':
        handle_get_ambiguity(qa_service, args)
    elif args.command == 'write-story-defect':
        handle_write_story_defect(qa_service, args)
    elif args.command == 'write-defect':
        handle_write_defect(qa_service, args)
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
    """Handle generate-tc command - exports test cases to CSV and Markdown."""
    console.print(f"[cyan]Generating test cases for {args.issue_key}...[/cyan]")
    result = tc_service.generate(args.issue_key)
    if not result:
        console.print(f"[red]Issue {args.issue_key} not found[/red]")
        return
    console.print(f"[green]✓[/green] CSV (Jira-ready): [bold]{result['csv_path']}[/bold]")
    console.print(f"[green]✓[/green] Markdown: [bold]{result['md_path']}[/bold]")
    console.print(f"[dim]Risk level: {result.get('risk_level', 'MEDIUM')} | Test cases: {len(result.get('test_cases', []))}[/dim]")


def handle_review(qa_service, args):
    """Handle the review command - analyze test coverage gaps."""
    if not qa_service:
        console.print("[red]Error: RAG context builder not available[/red]")
        console.print("[yellow]This command requires the RAG pipeline to be initialized.[/yellow]")
        return

    console.print(f"[cyan]Reviewing test coverage for {args.issue_key}...[/cyan]")
    result = qa_service.review(args.issue_key)
    if not result:
        console.print(f"[red]Issue {args.issue_key} not found[/red]")
        return
    console.print(f"[green]✓[/green] Review written to [bold]{result['saved_path']}[/bold]")


def handle_get_ambiguity(qa_service, args):
    """Handle the get-ambiguity command - detect unclear requirements."""
    if not qa_service:
        console.print("[red]Error: RAG context builder not available[/red]")
        console.print("[yellow]This command requires the RAG pipeline to be initialized.[/yellow]")
        return

    console.print(f"[cyan]Analyzing ambiguities for {args.issue_key}...[/cyan]")
    result = qa_service.get_ambiguity(args.issue_key)
    if not result:
        console.print(f"[red]Issue {args.issue_key} not found[/red]")
        return
    console.print(f"[green]✓[/green] Ambiguity analysis written to [bold]{result['saved_path']}[/bold]")


def handle_write_story_defect(qa_service, args):
    """Handle the write-story-defect command - generate defect for requirement issue."""
    if not qa_service:
        console.print("[red]Error: RAG context builder not available[/red]")
        console.print("[yellow]This command requires the RAG pipeline to be initialized.[/yellow]")
        return

    issue_type = getattr(args, 'issue_type', 'missing_ac')
    custom_summary = getattr(args, 'summary', None)
    custom_description = getattr(args, 'description', None)

    # Interactive prompt for defect description if not provided via CLI
    if custom_description is None:
        console.print(Panel.fit(
            "[bold cyan]Defect Description Required[/bold cyan]\n"
            "Please provide a description of the defect you observed.\n"
            "This will be preserved exactly as entered.",
            border_style="cyan"
        ))
        custom_description = Prompt.ask(
            "[bold]Enter defect description[/bold]",
            default=""
        )
        if not custom_description.strip():
            console.print("[yellow]Warning: No description provided. Proceeding with auto-generated description.[/yellow]")
            custom_description = None

    console.print(f"[cyan]Generating story defect ({issue_type}) for {args.issue_key}...[/cyan]")
    result = qa_service.write_story_defect(
        args.issue_key,
        issue_type=issue_type,
        custom_summary=custom_summary,
        custom_description=custom_description,
    )
    if not result:
        console.print(f"[red]Issue {args.issue_key} not found[/red]")
        return

    # Display CSV path (primary output for Jira import)
    if "csv_path" in result:
        console.print(f"[green]✓[/green] CSV (Jira-ready): [bold]{result['csv_path']}[/bold]")

    # Display Markdown path (secondary/documentation)
    if "md_path" in result:
        console.print(f"[green]✓[/green] Markdown: [bold]{result['md_path']}[/bold]")

    # Display defect summary
    defect = result.get("defect")
    if defect:
        console.print(f"[dim]Risk: {defect.risk_level} | Component: {defect.component}[/dim]")


def handle_write_defect(qa_service, args):
    """Handle the write-defect command - generate defect for rule/state/financial violation."""
    if not qa_service:
        console.print("[red]Error: RAG context builder not available[/red]")
        console.print("[yellow]This command requires the RAG pipeline to be initialized.[/yellow]")
        return

    violation_type = getattr(args, 'violation_type', 'rule')
    custom_summary = getattr(args, 'summary', None)
    custom_description = getattr(args, 'description', None)

    console.print(f"[cyan]Generating defect ({violation_type} violation) for {args.issue_key}...[/cyan]")
    result = qa_service.write_defect(
        args.issue_key,
        violation_type=violation_type,
        custom_summary=custom_summary,
        custom_description=custom_description,
    )
    if not result:
        console.print(f"[red]Issue {args.issue_key} not found[/red]")
        return

    # Display CSV path (primary output for Jira import)
    if "csv_path" in result:
        console.print(f"[green]✓[/green] CSV (Jira-ready): [bold]{result['csv_path']}[/bold]")

    # Display Markdown path (secondary/documentation)
    if "md_path" in result:
        console.print(f"[green]✓[/green] Markdown: [bold]{result['md_path']}[/bold]")

    # Display defect summary
    defect = result.get("defect")
    if defect:
        console.print(f"[dim]Risk: {defect.risk_level} | Component: {defect.component}[/dim]")


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
