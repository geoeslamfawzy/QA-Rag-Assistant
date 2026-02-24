#!/usr/bin/env python3
"""
Local RAG Brain - Main Entry Point

A 100% local QA analysis system that:
1. Fetches Jira stories
2. Retrieves relevant knowledge from local knowledge base
3. Runs validation checks
4. Generates structured prompts for manual paste into Claude Pro

NO CLOUD AI SERVICES - Everything runs locally.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import our modules
from jira_client import JiraClient
from rag import (
    RAGConfig,
    OllamaEmbedder,
    IndexBuilder,
    HybridRetriever,
    StoryPreAnalyzer,
    PromptBuilder,
)
from rag.embeddings import verify_ollama_setup
from rag.retriever import StoryContext
from validators import (
    StateValidator,
    FinancialValidator,
    RuleEngine,
    CrossDepChecker,
    ValidatorPipeline,
)

console = Console()


def check_prerequisites() -> bool:
    """Check that all prerequisites are met."""
    console.print("\n[bold]Checking prerequisites...[/bold]")

    # Check Ollama
    status = verify_ollama_setup()

    if not status["ollama_running"]:
        console.print("[red]ERROR: Ollama is not running[/red]")
        console.print("Start Ollama with: [cyan]ollama serve[/cyan]")
        return False

    if not status["model_available"]:
        console.print(f"[yellow]Model not available. Pulling...[/yellow]")
        embedder = OllamaEmbedder()
        if not embedder.pull_model():
            console.print("[red]ERROR: Failed to pull model[/red]")
            return False

    console.print("[green]Prerequisites OK[/green]")
    return True


def handle_build_index(args):
    """Handle the build-index command."""
    console.print(Panel(
        "[bold]Building Vector Index[/bold]\n"
        "Scanning knowledge base and generating embeddings...",
        title="RAG Brain"
    ))

    if not check_prerequisites():
        return 1

    builder = IndexBuilder()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Building index...", total=None)

        if args.incremental:
            success = builder.incremental_update()
        else:
            success = builder.build_index(force_rebuild=args.force)

        progress.update(task, completed=True)

    if success:
        status = builder.get_status()
        console.print("\n[green]Index built successfully![/green]")
        console.print(f"  Documents: {status['total_documents']}")
        console.print(f"  Chunks: {status['total_chunks']}")
        console.print(f"  Location: {builder.config.INDEX_DIR}")
        return 0
    else:
        console.print("[red]Index build failed[/red]")
        return 1


def handle_status(args):
    """Handle the status command."""
    builder = IndexBuilder()
    status = builder.get_status()

    table = Table(title="RAG Brain Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Index Exists", "Yes" if status["index_exists"] else "No")
    table.add_row("Total Documents", str(status["total_documents"]))
    table.add_row("Total Chunks", str(status["total_chunks"]))
    table.add_row("Last Built", status["last_built"] or "Never")
    table.add_row("Embedding Model", status["embedding_model"])
    table.add_row("Knowledge Base Files", str(status["knowledge_base_files"]))
    table.add_row("Changed Files", str(status["changed_files"]))

    console.print(table)

    # Check Ollama status
    ollama_status = verify_ollama_setup()
    console.print("\n[bold]Ollama Status:[/bold]")
    console.print(f"  Running: {'Yes' if ollama_status['ollama_running'] else 'No'}")
    console.print(f"  Model Available: {'Yes' if ollama_status['model_available'] else 'No'}")

    return 0


def handle_generate_prompt(args):
    """Handle the main prompt generation command."""
    story_key = args.story_key

    console.print(Panel(
        f"[bold]Generating QA Prompt for {story_key}[/bold]\n"
        "Fetching story, retrieving knowledge, running validations...",
        title="RAG Brain"
    ))

    # Check prerequisites
    if not check_prerequisites():
        return 1

    # Check index exists
    builder = IndexBuilder()
    if not builder.config.vector_index_path.exists():
        console.print("[yellow]No index found. Building index first...[/yellow]")
        builder.build_index()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Step 1: Fetch Jira story
        task = progress.add_task("Fetching Jira story...", total=None)
        try:
            jira_client = JiraClient()
            issue = jira_client.get_issue(story_key)
            if not issue:
                console.print(f"[red]Story {story_key} not found[/red]")
                return 1

            story = {
                "key": issue.get("key"),
                "title": issue.get("summary"),
                "status": issue.get("status"),
                "priority": issue.get("priority"),
                "issue_type": issue.get("issue_type"),
                "assignee": issue.get("assignee"),
                "description": issue.get("description", ""),
                "acceptance_criteria": issue.get("acceptance_criteria", []),
            }
        except Exception as e:
            console.print(f"[red]Failed to fetch story: {e}[/red]")
            return 1
        progress.update(task, completed=True)

        # Step 2: Pre-analyze story
        task = progress.add_task("Analyzing story...", total=None)
        pre_analyzer = StoryPreAnalyzer()
        pre_analysis = pre_analyzer.analyze(story)
        progress.update(task, completed=True)

        # Step 3: Retrieve knowledge
        task = progress.add_task("Retrieving knowledge...", total=None)
        retriever = HybridRetriever()

        # Build query from story
        query_parts = [story.get("title", "")]
        if story.get("description"):
            query_parts.append(story["description"][:500])

        query = " ".join(query_parts)

        # Create story context for retrieval
        story_context = StoryContext(
            text=query,
            detected_domains=pre_analysis.detected_domains,
            priority_rule_types=pre_analysis.priority_rule_types,
            risk_flags=pre_analysis.risk_flags,
            keywords=pre_analysis.keywords[:20]
        )

        retrieved_chunks = retriever.retrieve(
            query=query,
            story_context=story_context,
            top_k=10
        )
        retriever.close()
        progress.update(task, completed=True)

        # Step 4: Run validators
        task = progress.add_task("Running validations...", total=None)

        # Convert retrieved chunks for validators
        knowledge_context = [
            {
                "id": chunk.chunk.id,
                "content": chunk.chunk.content,
                "metadata": chunk.chunk.metadata
            }
            for chunk in retrieved_chunks
        ]

        # Validators are injected into the pipeline (OCP + DIP).
        # To add a new validator: create the class and append it to this list.
        pipeline = ValidatorPipeline([
            StateValidator(),
            FinancialValidator(),
            RuleEngine(),
            CrossDepChecker(),
        ])
        validation_results = pipeline.run_as_dicts(story, knowledge_context)

        progress.update(task, completed=True)

        # Step 5: Build prompt
        task = progress.add_task("Building prompt...", total=None)
        prompt_builder = PromptBuilder()
        prompt_builder.set_story(story)
        prompt_builder.set_retrieved_context(retrieved_chunks)
        prompt_builder.set_pre_analysis(pre_analysis)
        prompt_builder.set_validation_results(validation_results)
        prompt_builder.set_debug_mode(args.show_scores)

        prompt_path = prompt_builder.save()
        progress.update(task, completed=True)

    # Display results
    console.print("\n" + "=" * 60)
    console.print("[bold green]Prompt Generated Successfully![/bold green]")
    console.print("=" * 60)

    # Summary
    console.print(f"\n[bold]Story:[/bold] {story_key} - {story.get('title', '')[:50]}")
    console.print(f"[bold]Risk Level:[/bold] {pre_analysis.risk_level.upper()}")
    console.print(f"[bold]Detected Domains:[/bold] {', '.join(pre_analysis.detected_domains[:5])}")
    console.print(f"[bold]Retrieved Chunks:[/bold] {len(retrieved_chunks)}")

    # Validation summary
    console.print("\n[bold]Validation Results:[/bold]")
    for name, result in validation_results.items():
        status = "[green]PASS[/green]" if result["passed"] else "[red]FAIL[/red]"
        score = result.get("score", 1.0)
        console.print(f"  {name}: {status} ({score:.0%})")

    # Output location
    console.print(f"\n[bold]Prompt saved to:[/bold] {prompt_path}")

    # Copy to clipboard option
    if args.clipboard:
        if prompt_builder.to_clipboard():
            console.print("[green]Copied to clipboard![/green]")
        else:
            console.print("[yellow]Could not copy to clipboard[/yellow]")

    console.print("\n[cyan]Next step: Open the prompt file and paste into Claude Pro[/cyan]")

    return 0


def handle_retrieve(args):
    """Handle the retrieve command (debug/testing)."""
    query = args.query

    console.print(f"[bold]Retrieving for query:[/bold] {query[:100]}")

    if not check_prerequisites():
        return 1

    retriever = HybridRetriever()

    if not retriever.load_index():
        console.print("[red]No index found. Run build-index first.[/red]")
        return 1

    results = retriever.retrieve(query, top_k=args.top_k)

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return 0

    console.print(f"\n[bold]Found {len(results)} results:[/bold]\n")

    for i, result in enumerate(results):
        console.print(f"[bold cyan][{i+1}] {result.chunk.id}[/bold cyan]")
        console.print(f"  Module: {result.chunk.metadata.get('module', 'N/A')}")
        console.print(f"  Rule Type: {result.chunk.metadata.get('rule_type', 'N/A')}")
        console.print(f"  Score: {result.final_score:.4f}")

        if args.verbose:
            console.print(f"  Cosine: {result.cosine_score:.4f}")
            console.print(f"  BM25: {result.bm25_score:.4f}")
            console.print(f"  Boost: {result.metadata_boost:.2f}x")

        # Content preview
        content = result.chunk.content[:200].replace("\n", " ")
        console.print(f"  Content: {content}...")
        console.print()

    retriever.close()
    return 0


def main():
    """Main entry point."""
    # Auto-detect story key: if first arg doesn't match a subcommand, treat as story key
    subcommands = ['build-index', 'status', 'retrieve', 'analyze', '-h', '--help']
    if len(sys.argv) > 1 and sys.argv[1] not in subcommands:
        # Check if it looks like a Jira key (e.g., CMB-32860, PROJ-123)
        if '-' in sys.argv[1] and not sys.argv[1].startswith('-'):
            sys.argv.insert(1, 'analyze')

    parser = argparse.ArgumentParser(
        description="Local RAG Brain - QA Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s CMB-35047              Generate prompt for story
  %(prog)s CMB-35047 --show-scores  Include retrieval scores in prompt
  %(prog)s CMB-35047 --clipboard  Copy to clipboard
  %(prog)s build-index            Build/rebuild index
  %(prog)s status                 Show index status
  %(prog)s retrieve "query"       Test retrieval
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Build index command
    build_parser = subparsers.add_parser(
        "build-index",
        help="Build or rebuild the vector index"
    )
    build_parser.add_argument(
        "--force",
        action="store_true",
        help="Force full rebuild"
    )
    build_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only update changed files"
    )

    # Status command
    subparsers.add_parser(
        "status",
        help="Show index status"
    )

    # Retrieve command (for testing)
    retrieve_parser = subparsers.add_parser(
        "retrieve",
        help="Test retrieval with a query"
    )
    retrieve_parser.add_argument(
        "query",
        help="Query text"
    )
    retrieve_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results"
    )
    retrieve_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed scores"
    )

    # Analyze command (story key)
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Generate QA prompt for a Jira story"
    )
    analyze_parser.add_argument(
        "story_key",
        help="Jira story key (e.g., CMB-35047)"
    )
    analyze_parser.add_argument(
        "--show-scores", "-s",
        action="store_true",
        help="Include retrieval relevance scores and validator details in prompt"
    )
    analyze_parser.add_argument(
        "--clipboard", "-c",
        action="store_true",
        help="Copy prompt to clipboard"
    )

    args = parser.parse_args()

    # Route to appropriate handler
    if args.command == "build-index":
        return handle_build_index(args)
    elif args.command == "status":
        return handle_status(args)
    elif args.command == "retrieve":
        return handle_retrieve(args)
    elif args.command == "analyze":
        return handle_generate_prompt(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
