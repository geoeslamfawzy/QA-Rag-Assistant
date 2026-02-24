"""
Display Package

All Rich console rendering is isolated here.
Domain and service classes import from this package
instead of depending on Rich directly.
"""
from .issue_display import IssueDisplay
from .analysis_display import AnalysisDisplay

__all__ = ['IssueDisplay', 'AnalysisDisplay']