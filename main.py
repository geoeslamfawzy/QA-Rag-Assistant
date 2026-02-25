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
from services import (
    OutputWriter,
    AnalysisService,
    TestCaseService,
    RAGContextBuilder,
    QACommandService,
    JiraCommentService,
    CommentType,
    XrayService,
    DefectService,
)
from services.defect_service import DefectFormatter
from services.regression_defect_creator import RegressionDefectCreator, RegressionDefectResult
from services.production_bug_creator import ProductionBugCreator, ProductionBugResult
from services.story_defect_creator import StoryDefectCreator, StoryDefectResult

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
    analyze_parser.add_argument('--post', action='store_true', help='Post findings as Jira comment')

    story_parser = subparsers.add_parser('story', help='Analyze a story (description and AC)')
    story_parser.add_argument('issue_key', type=str, help='Story key (e.g., PROJ-123)')

    tc_parser = subparsers.add_parser('generate-tc', help='Generate test cases for a story')
    tc_parser.add_argument('issue_key', type=str, help='Story key (e.g., PROJ-123)')
    tc_parser.add_argument(
        '--xray',
        action='store_true',
        help='Create Test issues in Jira and link to story'
    )

    # New QA commands using shared RAG pipeline
    review_parser = subparsers.add_parser('review', help='Review test coverage and detect gaps')
    review_parser.add_argument('issue_key', type=str, help='Story key (e.g., PROJ-123)')
    review_parser.add_argument('--post', action='store_true', help='Post findings as Jira comment')

    ambiguity_parser = subparsers.add_parser('get-ambiguity', help='Detect unclear requirements')
    ambiguity_parser.add_argument('issue_key', type=str, help='Story key (e.g., PROJ-123)')
    ambiguity_parser.add_argument('--post', action='store_true', help='Post findings as Jira comment')

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
    story_defect_parser.add_argument(
        '--jira',
        action='store_true',
        help='Create defect directly in Jira (using RAG-grounded content)'
    )
    story_defect_parser.add_argument(
        '--priority', type=str, default='p1',
        choices=['p0', 'p1', 'p2', 'p3'],
        help='Priority for Jira defect: p0=Critical, p1=High (default), p2=Medium, p3=Low'
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
    defect_parser.add_argument(
        '--jira',
        action='store_true',
        help='Create defect directly in Jira (using RAG-grounded content)'
    )
    defect_parser.add_argument(
        '--priority', type=str, default='p1',
        choices=['p0', 'p1', 'p2', 'p3'],
        help='Priority for Jira defect: p0=Critical, p1=High (default), p2=Medium, p3=Low'
    )

    # Create defect directly in Jira
    create_defect_parser = subparsers.add_parser('create-defect', help='Create a defect/bug in Jira')
    create_defect_parser.add_argument('--story', type=str, help='Link to story (e.g., CMB-32860)')
    create_defect_parser.add_argument('--summary', type=str, required=True, help='Defect summary/title')
    create_defect_parser.add_argument('--description', type=str, help='Defect description (prompts if omitted)')
    create_defect_parser.add_argument(
        '--priority', type=str, default='p1',
        choices=['p0', 'p1', 'p2', 'p3'],
        help='Priority: p0=Critical, p1=High (default), p2=Medium, p3=Low'
    )
    create_defect_parser.add_argument(
        '--module', type=str, required=True,
        help='Module name (e.g., GiftCard, Login, Payment)'
    )
    create_defect_parser.add_argument(
        '--env', type=str, default='preprod',
        choices=['preprod', 'staging'],
        help='Environment (default: preprod)'
    )
    create_defect_parser.add_argument(
        '--browser', type=str, default='chrome',
        choices=['chrome', 'superapp'],
        help='Browser/App (default: chrome)'
    )
    create_defect_parser.add_argument(
        '--ai',
        action='store_true',
        help='Use AI (Ollama) to generate professional summary and description'
    )

    # Create Regular Defect (standalone Bug, NO parent, HAS labels, HAS prefix)
    regular_defect_parser = subparsers.add_parser(
        'create-regular-defect',
        help='Create a standalone Bug in Jira (no parent, with labels and prefix)'
    )
    regular_defect_parser.add_argument(
        '--module', type=str, required=True,
        help='Module name (e.g., GiftCard, Login, Payment)'
    )
    regular_defect_parser.add_argument(
        '--env', type=str, default='preprod',
        choices=['preprod', 'staging', 'prod'],
        help='Environment (default: preprod)'
    )
    regular_defect_parser.add_argument(
        '--platform', type=str, default='WebApp',
        choices=['WebApp', 'iOS', 'Android', 'SuperApp'],
        help='Platform (default: WebApp)'
    )
    regular_defect_parser.add_argument(
        '--priority', type=str, default='p1',
        choices=['p0', 'p1', 'p2', 'p3'],
        help='Priority (default: p1)'
    )

    # Create Production Bug (standalone Bug, NO parent, optional labels)
    bug_parser = subparsers.add_parser(
        'create-bug',
        help='Create a Production Bug in Jira (no parent, Issue Type: Bug)'
    )
    bug_parser.add_argument(
        '--module', type=str, required=True,
        help='Module name (e.g., GiftCard, Login, Payment)'
    )
    bug_parser.add_argument(
        '--env', type=str, default='prod',
        choices=['preprod', 'staging', 'prod'],
        help='Environment (default: prod)'
    )
    bug_parser.add_argument(
        '--platform', type=str, default='WebApp',
        choices=['WebApp', 'iOS', 'Android', 'SuperApp'],
        help='Platform (default: WebApp)'
    )
    bug_parser.add_argument(
        '--priority', type=str, default='p1',
        choices=['p0', 'p1', 'p2', 'p3'],
        help='Priority (default: p1)'
    )

    # Create Story Defect (Bug under User Story, HAS parent, NO labels, NO prefix)
    story_defect_new_parser = subparsers.add_parser(
        'create-story-defect',
        help='Create a Bug under a User Story (with parent, no labels, no prefix)'
    )
    story_defect_new_parser.add_argument(
        'parent_key', type=str,
        help='Parent story key (e.g., CMB-32860) - REQUIRED'
    )
    story_defect_new_parser.add_argument(
        '--module', type=str, default=None,
        help='Module name (auto-detected from story if omitted)'
    )
    story_defect_new_parser.add_argument(
        '--priority', type=str, default='p1',
        choices=['p0', 'p1', 'p2', 'p3'],
        help='Priority (default: p1)'
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

    # Initialize XrayService for --xray functionality
    xray_service = XrayService(client)

    # Initialize DefectService for create-defect command
    defect_service = DefectService(client)

    tc_service = TestCaseService(
        client,
        writer,
        rag_builder=rag_builder,
        xray_service=xray_service,
    )

    # Initialize Jira comment service for --post functionality
    comment_service = JiraCommentService(client)

    # Initialize QA command service for new commands (review, get-ambiguity, write-*-defect)
    qa_service = None
    if rag_builder:
        qa_service = QACommandService(rag_builder, writer, client)

    if args.command == 'list':
        handle_list(client, analysis_service, issue_display, analysis_display, args)
    elif args.command == 'view':
        handle_view(client, analysis_service, issue_display, analysis_display, args)
    elif args.command == 'comment':
        handle_comment(client, args)
    elif args.command in ('analyze', 'story'):
        handle_analyze(analysis_service, comment_service, issue_display, analysis_display, args)

    elif args.command == 'generate-tc':
        handle_generate_tc(tc_service, args)
    elif args.command == 'review':
        handle_review(qa_service, comment_service, args)
    elif args.command == 'get-ambiguity':
        handle_get_ambiguity(qa_service, comment_service, args)
    elif args.command == 'write-story-defect':
        handle_write_story_defect(qa_service, args)
    elif args.command == 'write-defect':
        handle_write_defect(qa_service, args)
    elif args.command == 'create-defect':
        handle_create_defect(defect_service, args)
    elif args.command == 'create-regular-defect':
        handle_create_regular_defect(client, args)
    elif args.command == 'create-bug':
        handle_create_bug(client, args)
    elif args.command == 'create-story-defect':
        handle_create_story_defect(client, args)
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


def handle_analyze(analysis_service, comment_service, issue_display, analysis_display, args):
    if args.issue_key:
        post_comment = getattr(args, 'post', False)
        result = analysis_service.analyze_story(args.issue_key)
        if not result:
            console.print(f"[red]Issue {args.issue_key} not found[/red]")
            return
        issue_display.display_issue_details(result['issue'])
        analysis_display.display_story_analysis(result['analysis'], args.issue_key)
        console.print(f"[green]✓[/green] Analysis written to [bold]{result['saved_path']}[/bold]")

        # Handle --post flag
        if post_comment and result.get('rag_context'):
            comment_result = comment_service.post_comment(
                args.issue_key,
                result['rag_context'],
                CommentType.ANALYZE,
            )
            if comment_result.success:
                console.print(f"[green]✓[/green] Comment posted to Jira ({comment_result.finding_count} findings)")
            else:
                console.print(f"[yellow]⚠[/yellow] Failed to post comment: {comment_result.error}")
    else:
        result = analysis_service.analyze_bulk(args.jql, args.limit)
        if result:
            analysis_display.display_analysis(result['analysis'])
        else:
            console.print("[yellow]No issues to analyze[/yellow]")


def handle_generate_tc(tc_service, args):
    """Handle generate-tc command - exports test cases to CSV and Markdown."""
    create_in_jira = getattr(args, 'xray', False)

    console.print(f"[cyan]Generating test cases for {args.issue_key}...[/cyan]")
    result = tc_service.generate(args.issue_key, create_in_jira=create_in_jira)

    if not result:
        console.print(f"[red]Issue {args.issue_key} not found[/red]")
        return

    # Always show CSV and Markdown paths
    console.print(f"[green]✓[/green] CSV (Jira-ready): [bold]{result['csv_path']}[/bold]")
    console.print(f"[green]✓[/green] Markdown: [bold]{result['md_path']}[/bold]")
    console.print(f"[dim]Risk level: {result.get('risk_level', 'MEDIUM')} | Test cases: {len(result.get('test_cases', []))}[/dim]")

    # Show XRAY results if --xray was used
    if 'xray_result' in result:
        xray_result = result['xray_result']
        console.print("")  # Blank line
        console.print("[bold cyan]XRAY Test Creation Results:[/bold cyan]")

        # Show created tests
        if xray_result.created:
            console.print(f"[green]✓ Created {xray_result.created_count} Test issue(s):[/green]")
            for tr in xray_result.created:
                linked_status = "[green]linked[/green]" if tr.linked else "[yellow]not linked[/yellow]"
                summary_truncated = tr.summary[:50] + "..." if len(tr.summary) > 50 else tr.summary
                console.print(f"  - {tr.issue_key}: {summary_truncated} ({linked_status})")

        # Show skipped (duplicates)
        if xray_result.skipped:
            console.print(f"[yellow]⚠ Skipped {xray_result.skipped_count} duplicate(s):[/yellow]")
            for tr in xray_result.skipped:
                summary_truncated = tr.summary[:50] + "..." if len(tr.summary) > 50 else tr.summary
                console.print(f"  - {tr.issue_key}: {summary_truncated}")

        # Show failures
        if xray_result.failed:
            console.print(f"[red]✗ Failed {xray_result.failed_count} creation(s):[/red]")
            for tr in xray_result.failed:
                console.print(f"  - {tr.test_case_id}: {tr.error}")


def handle_review(qa_service, comment_service, args):
    """Handle the review command - analyze test coverage gaps."""
    if not qa_service:
        console.print("[red]Error: RAG context builder not available[/red]")
        console.print("[yellow]This command requires the RAG pipeline to be initialized.[/yellow]")
        return

    post_comment = getattr(args, 'post', False)
    console.print(f"[cyan]Reviewing test coverage for {args.issue_key}...[/cyan]")
    result = qa_service.review(args.issue_key, post_comment=post_comment)
    if not result:
        console.print(f"[red]Issue {args.issue_key} not found[/red]")
        return
    console.print(f"[green]✓[/green] Review written to [bold]{result['saved_path']}[/bold]")

    # Handle --post flag
    if post_comment and result.get('rag_context'):
        comment_result = comment_service.post_comment(
            args.issue_key,
            result['rag_context'],
            CommentType.REVIEW,
        )
        if comment_result.success:
            console.print(f"[green]✓[/green] Comment posted to Jira ({comment_result.finding_count} findings)")
        else:
            console.print(f"[yellow]⚠[/yellow] Failed to post comment: {comment_result.error}")


def handle_get_ambiguity(qa_service, comment_service, args):
    """Handle the get-ambiguity command - detect unclear requirements."""
    if not qa_service:
        console.print("[red]Error: RAG context builder not available[/red]")
        console.print("[yellow]This command requires the RAG pipeline to be initialized.[/yellow]")
        return

    post_comment = getattr(args, 'post', False)
    console.print(f"[cyan]Analyzing ambiguities for {args.issue_key}...[/cyan]")
    result = qa_service.get_ambiguity(args.issue_key, post_comment=post_comment)
    if not result:
        console.print(f"[red]Issue {args.issue_key} not found[/red]")
        return
    console.print(f"[green]✓[/green] Ambiguity analysis written to [bold]{result['saved_path']}[/bold]")

    # Handle --post flag
    if post_comment and result.get('rag_context'):
        comment_result = comment_service.post_comment(
            args.issue_key,
            result['rag_context'],
            CommentType.AMBIGUITY,
        )
        if comment_result.success:
            console.print(f"[green]✓[/green] Comment posted to Jira ({comment_result.finding_count} findings)")
        else:
            console.print(f"[yellow]⚠[/yellow] Failed to post comment: {comment_result.error}")


def handle_write_story_defect(qa_service, args):
    """Handle the write-story-defect command - generate defect for requirement issue."""
    if not qa_service:
        console.print("[red]Error: RAG context builder not available[/red]")
        console.print("[yellow]This command requires the RAG pipeline to be initialized.[/yellow]")
        return

    issue_type = getattr(args, 'issue_type', 'missing_ac')
    custom_summary = getattr(args, 'summary', None)
    custom_description = getattr(args, 'description', None)
    create_in_jira = getattr(args, 'jira', False)
    priority = getattr(args, 'priority', 'p1')

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
        create_in_jira=create_in_jira,
        priority=priority,
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

    # Display Jira creation result if --jira was used
    if "jira_result" in result:
        jira_result = result["jira_result"]
        if jira_result.success:
            console.print(f"[green]✓[/green] Created in Jira: [bold]{jira_result.issue_key}[/bold]")
            if jira_result.linked:
                console.print(f"[green]✓[/green] Linked to {args.issue_key}")
            elif jira_result.error:
                console.print(f"[yellow]⚠[/yellow] Linking failed: {jira_result.error}")
        else:
            console.print(f"[red]✗[/red] Failed to create in Jira: {jira_result.error}")


def handle_write_defect(qa_service, args):
    """Handle the write-defect command - generate defect for rule/state/financial violation."""
    if not qa_service:
        console.print("[red]Error: RAG context builder not available[/red]")
        console.print("[yellow]This command requires the RAG pipeline to be initialized.[/yellow]")
        return

    violation_type = getattr(args, 'violation_type', 'rule')
    custom_summary = getattr(args, 'summary', None)
    custom_description = getattr(args, 'description', None)
    create_in_jira = getattr(args, 'jira', False)
    priority = getattr(args, 'priority', 'p1')

    console.print(f"[cyan]Generating defect ({violation_type} violation) for {args.issue_key}...[/cyan]")
    result = qa_service.write_defect(
        args.issue_key,
        violation_type=violation_type,
        create_in_jira=create_in_jira,
        priority=priority,
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

    # Display Jira creation result if --jira was used
    if "jira_result" in result:
        jira_result = result["jira_result"]
        if jira_result.success:
            console.print(f"[green]✓[/green] Created in Jira: [bold]{jira_result.issue_key}[/bold]")
            if jira_result.linked:
                console.print(f"[green]✓[/green] Linked to {args.issue_key}")
            elif jira_result.error:
                console.print(f"[yellow]⚠[/yellow] Linking failed: {jira_result.error}")
        else:
            console.print(f"[red]✗[/red] Failed to create in Jira: {jira_result.error}")


def handle_create_defect(defect_service, args):
    """Handle the create-defect command - create a defect/bug directly in Jira."""
    user_summary = args.summary
    description = args.description
    story_key = getattr(args, 'story', None)
    priority = getattr(args, 'priority', 'p1')
    module = args.module
    env = getattr(args, 'env', 'preprod')
    browser = getattr(args, 'browser', 'chrome')
    use_ai = getattr(args, 'ai', False)

    # Prompt for description if not provided
    if not description:
        console.print(Panel.fit(
            "[bold cyan]Defect Description[/bold cyan]\n"
            "Please provide a detailed description of the defect.",
            border_style="cyan"
        ))
        description = Prompt.ask("[bold]Enter defect description[/bold]", default="")
        if not description.strip():
            console.print("[yellow]Warning: No description provided.[/yellow]")
            description = user_summary  # Use summary as fallback

    # Check if AI is requested and available
    generator = None
    if use_ai:
        try:
            from rag.ollama_generator import OllamaGenerator
            generator = OllamaGenerator()
            if not generator.check_connection():
                console.print("[yellow]Warning: Ollama not running, falling back to template[/yellow]")
                use_ai = False
            elif not generator.check_model_available():
                console.print(f"[yellow]Warning: Model '{generator.model}' not available, falling back to template[/yellow]")
                console.print("[dim]Run: ollama pull mistral[/dim]")
                use_ai = False
            else:
                console.print("[cyan]Using AI to generate professional description...[/cyan]")
        except ImportError:
            console.print("[yellow]Warning: OllamaGenerator not available, falling back to template[/yellow]")
            use_ai = False

    # Format summary and description
    if use_ai and generator:
        formatted_summary = DefectFormatter.format_summary_with_ai(
            generator, user_summary, module, env, browser
        )
        formatted_description = DefectFormatter.format_description_with_ai(
            generator, description, module, env, browser
        )
    else:
        formatted_summary = DefectFormatter.format_summary(
            user_summary, module, env, browser
        )
        formatted_description = DefectFormatter.format_description(
            description, module, env, browser
        )

    # Map priority to display name
    priority_display = {
        'p0': 'P0 - Critical',
        'p1': 'P1 - High',
        'p2': 'P2 - Medium',
        'p3': 'P3 - Low',
    }.get(priority, 'P1 - High')

    # Display info
    env_display = "Preprod" if env == "preprod" else "Staging"
    browser_display = "Chrome" if browser == "chrome" else "Super App"

    console.print(f"[cyan]Creating defect in Jira...[/cyan]")
    console.print(f"[dim]Module: {module} | Env: {env_display} | Browser: {browser_display}[/dim]")
    console.print(f"[dim]Priority: {priority_display}[/dim]")
    if story_key:
        console.print(f"[dim]Linking to story: {story_key}[/dim]")

    result = defect_service.create_defect(
        summary=formatted_summary,
        description=formatted_description,
        story_key=story_key,
        priority=priority,
    )

    if result.success:
        console.print(f"[green]✓[/green] Created defect: [bold]{result.issue_key}[/bold]")
        if story_key:
            if result.linked:
                console.print(f"[green]✓[/green] Linked to {story_key}")
            else:
                console.print(f"[yellow]⚠[/yellow] Linking failed: {result.error}")
    else:
        console.print(f"[red]✗[/red] Failed to create defect: {result.error}")


def prompt_defect_description() -> str:
    """Prompt user for defect description interactively."""
    console.print(Panel.fit(
        "[bold cyan]Enter Defect Description[/bold cyan]\n"
        "Describe the issue, user behavior, and context.\n"
        "[dim]Your input will be used to auto-generate professional defect fields.[/dim]",
        border_style="cyan"
    ))

    description = Prompt.ask(
        "[bold]Enter defect description[/bold]",
        default=""
    )
    return description.strip()


def handle_create_bug(client, args):
    """Handle create-bug command - Production Bug, NO parent, Issue Type: Bug."""
    user_description = prompt_defect_description()

    if not user_description:
        console.print("[red]Error: Defect description is required[/red]")
        return

    console.print(f"\n[cyan]Creating Production Bug...[/cyan]")
    console.print(f"[dim]Module: {args.module} | Env: {args.env.upper()} | Platform: {args.platform}[/dim]")

    creator = ProductionBugCreator(client)
    result = creator.create(
        user_description=user_description,
        module=args.module,
        env=args.env,
        platform=args.platform,
        priority=args.priority,
    )

    if result.success:
        console.print(f"[green]✓[/green] Created: [bold]{result.issue_key}[/bold]")
        console.print(f"[dim]Type: Production Bug (Issue Type: Bug)[/dim]")
    else:
        console.print(f"[red]✗[/red] Failed: {result.error}")


def handle_create_regular_defect(client, args):
    """Handle create-regular-defect command - Regression Defect (Issue Type: Defect), NO parent, HAS labels, HAS prefix."""
    # Always prompt for description
    user_description = prompt_defect_description()

    if not user_description:
        console.print("[red]Error: Defect description is required[/red]")
        return

    console.print(f"\n[cyan]Creating Regression Defect...[/cyan]")
    console.print(f"[dim]Module: {args.module} | Env: {args.env.upper()} | Platform: {args.platform}[/dim]")

    creator = RegressionDefectCreator(client)
    result = creator.create(
        user_description=user_description,
        module=args.module,
        env=args.env,
        platform=args.platform,
        priority=args.priority,
    )

    if result.success:
        console.print(f"[green]✓[/green] Created: [bold]{result.issue_key}[/bold]")
        console.print(f"[dim]Type: Regression Defect (Issue Type: Defect)[/dim]")
    else:
        console.print(f"[red]✗[/red] Failed: {result.error}")


def handle_create_story_defect(client, args):
    """Handle create-story-defect command - Bug under story, HAS parent, NO labels, NO prefix."""
    # Always prompt for description
    user_description = prompt_defect_description()

    if not user_description:
        console.print("[red]Error: Defect description is required[/red]")
        return

    console.print(f"\n[cyan]Creating Story Defect under {args.parent_key}...[/cyan]")
    if args.module:
        console.print(f"[dim]Module: {args.module}[/dim]")
    else:
        console.print(f"[dim]Module: auto-detected from story[/dim]")

    creator = StoryDefectCreator(client)
    result = creator.create(
        user_description=user_description,
        parent_key=args.parent_key,
        module=args.module,
        priority=args.priority,
    )

    if result.success:
        console.print(f"[green]✓[/green] Created: [bold]{result.issue_key}[/bold]")
        if result.linked:
            console.print(f"[green]✓[/green] Linked to: {result.parent_key}")
        else:
            console.print(f"[yellow]⚠[/yellow] Created but not linked: {result.error}")
        console.print(f"[dim]Type: Story Defect (Bug linked to story, no labels, clean summary)[/dim]")
    else:
        console.print(f"[red]✗[/red] Failed: {result.error}")


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
