"""
QA Intelligence Package for Deterministic QA Brain v2.0

This package provides the QA Intelligence Layer with:
- Ambiguity Detection Engine
- Gap Analyzer
- Scenario Expander
- Risk-Based Test Designer
- Defect Intelligence Engine
- Knowledge Gap Detector

All modules are fully deterministic with no random elements.
"""

from .ambiguity_engine import AmbiguityEngine
from .gap_analyzer import GapAnalyzer
from .scenario_expander import ScenarioExpander, ScenarioType, TestScenario
from .risk_based_test_designer import RiskBasedTestDesigner
from .defect_engine import DefectEngine
from .knowledge_gap_detector import KnowledgeGapDetector, KnowledgeGap, KnowledgeGapReport

__all__ = [
    # Engines
    'AmbiguityEngine',
    'GapAnalyzer',
    'ScenarioExpander',
    'RiskBasedTestDesigner',
    'DefectEngine',
    'KnowledgeGapDetector',
    # Supporting types
    'ScenarioType',
    'TestScenario',
    'KnowledgeGap',
    'KnowledgeGapReport',
]
