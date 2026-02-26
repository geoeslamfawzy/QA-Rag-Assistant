"""
Local RAG Brain Module

This module provides local RAG (Retrieval-Augmented Generation) capabilities
for QA analysis without any cloud AI dependencies.

Components:
- config: Configuration constants
- embeddings: Ollama embedding integration
- indexer: Vector index builder and persistence
- retriever: Hybrid retrieval (cosine + BM25 + RRF)
- story_pre_analyzer: Intent detection and domain classification
- prompt_builder: Structured prompt assembly
"""

# Lazy imports to avoid loading heavy dependencies when only config is needed
from .config import RAGConfig, DEFAULT_CONFIG

__all__ = [
    'RAGConfig',
    'DEFAULT_CONFIG',
    'OllamaEmbedder',
    'IndexBuilder',
    'HybridRetriever',
    'StoryPreAnalyzer',
    'PromptBuilder',
]

__version__ = '1.0.0'


def __getattr__(name):
    """Lazy import for heavy dependencies."""
    if name == 'OllamaEmbedder':
        from .embeddings import OllamaEmbedder
        return OllamaEmbedder
    elif name == 'IndexBuilder':
        from .indexer import IndexBuilder
        return IndexBuilder
    elif name == 'HybridRetriever':
        from .retriever import HybridRetriever
        return HybridRetriever
    elif name == 'StoryPreAnalyzer':
        from .story_pre_analyzer import StoryPreAnalyzer
        return StoryPreAnalyzer
    elif name == 'PromptBuilder':
        from .prompt_builder import PromptBuilder
        return PromptBuilder
    raise AttributeError(f"module 'rag' has no attribute '{name}'")
