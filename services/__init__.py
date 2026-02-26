"""
Services Package

Application-level orchestration services.
Each service coordinates infrastructure and domain objects
and is supplied its dependencies via constructor injection.

v2.0: Added QA Intelligence Layer exports.
v2.1: Refactored to dict-based lazy imports (SOLID - Open/Closed Principle).
"""

from importlib import import_module

# Lazy imports to avoid loading heavy dependencies at import time
__all__ = [
    # Core services
    'OutputWriter',
    'AnalysisService',
    'TestCaseService',
    'RAGContextBuilder',
    'RAGContext',
    'QACommandService',
    'QACommandType',
    'JiraCommentService',
    'CommentType',
    'CommentPostResult',
    'XrayService',
    'XrayBatchResult',
    'XrayTestResult',
    'DefectService',
    'DefectResult',
    'JiraDefectCreator',
    'JiraDefectResult',
    'DefectFieldGenerator',
    'GeneratedDefectFields',
    'RegressionDefectCreator',
    'RegressionDefectResult',
    'ProductionBugCreator',
    'ProductionBugResult',
    'StoryDefectCreator',
    'StoryDefectResult',
    'DeterministicGenerator',
    'DeterministicOutput',
    # QA Intelligence v2.0 engines
    'AmbiguityEngine',
    'GapAnalyzer',
    'ScenarioExpander',
    'ScenarioType',
    'TestScenario',
    'RiskBasedTestDesigner',
    'DefectEngine',
    'KnowledgeGapDetector',
    'KnowledgeGap',
    'KnowledgeGapReport',
]

# Lazy import registry: name -> (module_path, class_name, is_external)
# is_external=True means import from external package (qa_intelligence)
# is_external=False (default) means import from this package (.module_name)
_LAZY_IMPORTS = {
    # Core services (internal)
    'OutputWriter': ('.output_writer', 'OutputWriter'),
    'AnalysisService': ('.analysis_service', 'AnalysisService'),
    'TestCaseService': ('.test_case_service', 'TestCaseService'),
    'RAGContextBuilder': ('.rag_context_builder', 'RAGContextBuilder'),
    'RAGContext': ('.rag_context_builder', 'RAGContext'),
    'QACommandService': ('.qa_command_service', 'QACommandService'),
    'QACommandType': ('.qa_command_service', 'QACommandType'),
    'JiraCommentService': ('.jira_comment_service', 'JiraCommentService'),
    'CommentType': ('.jira_comment_service', 'CommentType'),
    'CommentPostResult': ('.jira_comment_service', 'CommentPostResult'),
    'XrayService': ('.xray_service', 'XrayService'),
    'XrayBatchResult': ('.xray_service', 'XrayBatchResult'),
    'XrayTestResult': ('.xray_service', 'XrayTestResult'),
    'DefectService': ('.defect_service', 'DefectService'),
    'DefectResult': ('.defect_service', 'DefectResult'),
    'JiraDefectCreator': ('.jira_defect_creator', 'JiraDefectCreator'),
    'JiraDefectResult': ('.jira_defect_creator', 'JiraDefectResult'),
    'DefectFieldGenerator': ('.defect_field_generator', 'DefectFieldGenerator'),
    'GeneratedDefectFields': ('.defect_field_generator', 'GeneratedDefectFields'),
    'RegressionDefectCreator': ('.regression_defect_creator', 'RegressionDefectCreator'),
    'RegressionDefectResult': ('.regression_defect_creator', 'RegressionDefectResult'),
    'ProductionBugCreator': ('.production_bug_creator', 'ProductionBugCreator'),
    'ProductionBugResult': ('.production_bug_creator', 'ProductionBugResult'),
    'StoryDefectCreator': ('.story_defect_creator', 'StoryDefectCreator'),
    'StoryDefectResult': ('.story_defect_creator', 'StoryDefectResult'),
    'DeterministicGenerator': ('.deterministic_generator', 'DeterministicGenerator'),
    'DeterministicOutput': ('.deterministic_generator', 'DeterministicOutput'),
    # QA Intelligence v2.0 engines (external package)
    'AmbiguityEngine': ('qa_intelligence', 'AmbiguityEngine', True),
    'GapAnalyzer': ('qa_intelligence', 'GapAnalyzer', True),
    'ScenarioExpander': ('qa_intelligence', 'ScenarioExpander', True),
    'ScenarioType': ('qa_intelligence', 'ScenarioType', True),
    'TestScenario': ('qa_intelligence', 'TestScenario', True),
    'RiskBasedTestDesigner': ('qa_intelligence', 'RiskBasedTestDesigner', True),
    'DefectEngine': ('qa_intelligence', 'DefectEngine', True),
    'KnowledgeGapDetector': ('qa_intelligence', 'KnowledgeGapDetector', True),
    'KnowledgeGap': ('qa_intelligence', 'KnowledgeGap', True),
    'KnowledgeGapReport': ('qa_intelligence', 'KnowledgeGapReport', True),
}


def __getattr__(name):
    """
    Lazy import for heavy dependencies.

    Uses dict-based lookup for O(1) performance and easier maintenance.
    To add a new export, simply add an entry to _LAZY_IMPORTS dict.
    """
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module 'services' has no attribute '{name}'")

    entry = _LAZY_IMPORTS[name]
    module_path, class_name = entry[0], entry[1]
    is_external = len(entry) > 2 and entry[2]

    if is_external:
        # External package (e.g., qa_intelligence)
        module = import_module(module_path)
    else:
        # Internal module (relative import)
        module = import_module(module_path, package=__name__)

    return getattr(module, class_name)