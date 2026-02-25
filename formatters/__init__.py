"""
Formatters Package

Provides comment formatters for Jira posting.
Each formatter converts RAGContext to structured Jira comments.
"""
from .base_comment_formatter import (
    BaseCommentFormatter,
    JiraComment,
    CommentSection,
)
from .analyze_comment_formatter import AnalyzeCommentFormatter
from .review_comment_formatter import ReviewCommentFormatter
from .ambiguity_comment_formatter import AmbiguityCommentFormatter

__all__ = [
    "BaseCommentFormatter",
    "JiraComment",
    "CommentSection",
    "AnalyzeCommentFormatter",
    "ReviewCommentFormatter",
    "AmbiguityCommentFormatter",
]
