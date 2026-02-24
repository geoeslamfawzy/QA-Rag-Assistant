"""
Templates Package

Template classes for QA command output generation.
Each template transforms RAGContext into markdown output.
"""
from .base_template import BaseTemplate
from .review_template import ReviewTemplate
from .ambiguity_template import AmbiguityTemplate
from .story_defect_template import StoryDefectTemplate
from .defect_template import DefectTemplate

__all__ = [
    'BaseTemplate',
    'ReviewTemplate',
    'AmbiguityTemplate',
    'StoryDefectTemplate',
    'DefectTemplate',
]
