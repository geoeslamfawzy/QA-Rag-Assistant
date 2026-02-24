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

from .config import RAGConfig
from .embeddings import OllamaEmbedder
from .indexer import IndexBuilder
from .retriever import HybridRetriever
from .story_pre_analyzer import StoryPreAnalyzer
from .prompt_builder import PromptBuilder

__all__ = [
    'RAGConfig',
    'OllamaEmbedder',
    'IndexBuilder',
    'HybridRetriever',
    'StoryPreAnalyzer',
    'PromptBuilder',
]

__version__ = '1.0.0'
