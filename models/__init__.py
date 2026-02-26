"""Models Package for Deterministic QA Brain v2.0"""

# Core models
from .test_case import TestCase, PRIORITY_FROM_RISK
from .rule import Rule, RiskLevel
from .required_rule_set import RequiredRuleSet, CategorizedRule, RuleCategory
from .reasoning_chain import (
    ReasoningChain,
    ReasoningLink,
    ReasoningStepType,
    ReasoningContext,
)
from .evidence import EvidenceResult
from .defect import Defect, DefectType, Reproducibility, PRIORITY_MAP, SEVERITY_FROM_RISK

# v2.0 QA Intelligence models
from .ambiguity import (
    AmbiguityCategory,
    AmbiguitySeverity,
    AmbiguityItem,
    AmbiguityReport,
)
from .gap import (
    GapCategory,
    GapItem,
    GapReport,
    RegressionRisk,
)

__all__ = [
    # Core models
    'TestCase',
    'PRIORITY_FROM_RISK',
    'Rule',
    'RiskLevel',
    'RequiredRuleSet',
    'CategorizedRule',
    'RuleCategory',
    'ReasoningChain',
    'ReasoningLink',
    'ReasoningStepType',
    'ReasoningContext',
    'EvidenceResult',
    'Defect',
    'DefectType',
    'Reproducibility',
    'PRIORITY_MAP',
    'SEVERITY_FROM_RISK',
    # v2.0 QA Intelligence models
    'AmbiguityCategory',
    'AmbiguitySeverity',
    'AmbiguityItem',
    'AmbiguityReport',
    'GapCategory',
    'GapItem',
    'GapReport',
    'RegressionRisk',
]
