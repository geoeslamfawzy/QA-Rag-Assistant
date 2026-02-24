"""
Issue Analyzer Module

Pure analysis logic for Jira issues.
No display or formatting logic lives here — see display/analysis_display.py.
"""
import re
from typing import List, Dict, Any
from collections import Counter


class IssueAnalyzer:
    """Analyzer for Jira issues."""
    
    @staticmethod
    def analyze_issues(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform comprehensive analysis on a list of issues.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Dictionary containing analysis results
        """
        if not issues:
            return {}
        
        analysis = {
            'total_issues': len(issues),
            'by_status': Counter(issue['status'] for issue in issues),
            'by_priority': Counter(issue['priority'] for issue in issues),
            'by_type': Counter(issue['issue_type'] for issue in issues),
            'by_assignee': Counter(issue['assignee'] for issue in issues),
            'unassigned_count': sum(1 for issue in issues if issue['assignee'] == 'Unassigned'),
            'recent_updates': sorted(
                issues,
                key=lambda x: x['updated'],
                reverse=True
            )[:5]
        }
        
        return analysis
    
    @staticmethod
    def analyze_single_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single issue for potential issues or insights.
        
        Args:
            issue: Issue dictionary
            
        Returns:
            Dictionary containing analysis insights
        """
        insights = {
            'warnings': [],
            'suggestions': [],
            'info': []
        }
        
        # Check for missing description
        if not issue.get('description') or issue['description'] == 'No description':
            insights['warnings'].append("Issue has no description")
        
        # Check for unassigned issue
        if issue.get('assignee') == 'Unassigned':
            insights['warnings'].append("Issue is unassigned")
        
        # Check for high priority
        if issue.get('priority') in ['Highest', 'High']:
            insights['info'].append(f"High priority issue: {issue['priority']}")
        
        # Check description length
        if issue.get('description'):
            desc_length = len(issue['description'])
            if desc_length < 50:
                insights['suggestions'].append("Description is quite short - consider adding more details")
            elif desc_length > 1000:
                insights['info'].append("Issue has a detailed description")
        
        return insights
    
    @staticmethod
    def analyze_story(issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive analysis of a story based on description and acceptance criteria.

        Args:
            issue: Issue dictionary with description and acceptance_criteria

        Returns:
            Dictionary containing detailed story analysis
        """
        description = issue.get('description', '') or ''
        acceptance_criteria = issue.get('acceptance_criteria', '') or ''

        completeness, ac_analysis = IssueAnalyzer._analyze_completeness(description, acceptance_criteria)
        quality = IssueAnalyzer._analyze_quality(description)
        clarity = IssueAnalyzer._analyze_clarity(description, acceptance_criteria)
        recommendations = IssueAnalyzer._generate_recommendations(
            has_ac=bool(acceptance_criteria),
            desc_length=len(description),
            ac_count=ac_analysis.get('count', 0),
            quality_issues=quality['issues'],
            clarity_issues=clarity['issues'],
        )

        return {
            'completeness': completeness,
            'quality': quality,
            'clarity': clarity,
            'acceptance_criteria_analysis': ac_analysis,
            'recommendations': recommendations,
        }

    @staticmethod
    def _analyze_completeness(description: str, acceptance_criteria: str) -> tuple:
        """Return (completeness dict, ac_analysis dict)."""
        desc_length = len(description)
        has_ac = bool(acceptance_criteria)

        if desc_length >= 100:
            adequacy = 'adequate'
        elif desc_length > 0:
            adequacy = 'short'
        else:
            adequacy = 'missing'

        completeness = {
            'has_description': desc_length > 0,
            'description_length': desc_length,
            'description_adequacy': adequacy,
            'has_acceptance_criteria': has_ac,
        }

        if has_ac:
            ac_analysis = IssueAnalyzer._count_ac_items(acceptance_criteria)
        else:
            ac_analysis = {'count': 0, 'adequacy': 'missing'}

        return completeness, ac_analysis

    @staticmethod
    def _count_ac_items(acceptance_criteria: str) -> Dict[str, Any]:
        """Count and rate acceptance criteria items."""
        ac_length = len(acceptance_criteria)
        criteria_items = re.findall(
            r'[•\-\*]\s*(.+)|^\d+[\.\)]\s*(.+)', acceptance_criteria, re.MULTILINE
        )
        criteria_count = len([item for sublist in criteria_items for item in sublist if item.strip()])
        if criteria_count == 0:
            criteria_count = len([
                line for line in acceptance_criteria.split('\n')
                if line.strip() and not line.strip().startswith('#')
            ])

        if criteria_count >= 3:
            ac_adequacy = 'good'
        elif criteria_count >= 1:
            ac_adequacy = 'adequate'
        else:
            ac_adequacy = 'minimal'

        return {'count': criteria_count, 'length': ac_length, 'adequacy': ac_adequacy}

    @staticmethod
    def _analyze_quality(description: str) -> Dict[str, Any]:
        """Check description quality (user story format, technical details, business value)."""
        issues = []
        strengths = []
        desc_lower = description.lower()

        if 'as a' in desc_lower or 'as an' in desc_lower:
            strengths.append("Uses user story format (As a...)")
        else:
            issues.append("Consider using user story format: 'As a [user], I want [goal] so that [benefit]'")

        technical_keywords = ['api', 'database', 'endpoint', 'service', 'component', 'integration', 'authentication']
        if any(kw in desc_lower for kw in technical_keywords):
            strengths.append("Contains technical details")

        business_keywords = ['user', 'customer', 'business', 'value', 'benefit', 'goal', 'need']
        if any(kw in desc_lower for kw in business_keywords):
            strengths.append("Includes business context")
        else:
            issues.append("Consider adding business context or user value")

        return {'issues': issues, 'strengths': strengths}

    @staticmethod
    def _analyze_clarity(description: str, acceptance_criteria: str) -> Dict[str, Any]:
        """Check clarity (structure, examples, testability, edge cases)."""
        issues = []
        strengths = []
        desc_lower = description.lower()
        desc_length = len(description)

        if desc_length > 0:
            sentences = len([s for s in description.split('.') if s.strip()])
            if sentences >= 3:
                strengths.append("Description has good structure")
            elif sentences < 2:
                issues.append("Description may be too brief - consider adding more context")

        if any(word in desc_lower for word in ('example', 'scenario', 'when')):
            strengths.append("Includes examples or scenarios")
        else:
            issues.append("Consider adding examples or scenarios for clarity")

        if acceptance_criteria:
            testable_keywords = ['should', 'must', 'will', 'can', 'verify', 'validate', 'check']
            ac_lower = acceptance_criteria.lower()
            if any(kw in ac_lower for kw in testable_keywords):
                strengths.append("Acceptance criteria appear testable")
            else:
                issues.append("Ensure acceptance criteria are testable and specific")

            edge_keywords = ['error', 'invalid', 'empty', 'null', 'exception', 'edge case', 'boundary']
            if any(kw in ac_lower for kw in edge_keywords):
                strengths.append("Includes edge cases or error handling")
            else:
                issues.append("Consider adding edge cases and error handling scenarios")

        return {'issues': issues, 'strengths': strengths}

    @staticmethod
    def _generate_recommendations(
        has_ac: bool, desc_length: int, ac_count: int,
        quality_issues: List[str], clarity_issues: List[str]
    ) -> List[str]:
        """Build prioritised recommendation list from analysis results."""
        recommendations = []

        if not has_ac:
            recommendations.append("🔴 CRITICAL: Add acceptance criteria - essential for defining 'done'")

        if desc_length < 100:
            recommendations.append(f"⚠️  Add more detail to the description (currently {desc_length} chars)")

        if has_ac and ac_count < 3:
            recommendations.append(f"⚠️  Consider adding more acceptance criteria (currently {ac_count} items)")

        recommendations.extend([f"💡 {issue}" for issue in quality_issues[:2]])
        recommendations.extend([f"💡 {issue}" for issue in clarity_issues[:2]])

        return recommendations
    
    @staticmethod
    def format_story_analysis_md(issue: Dict[str, Any], analysis: Dict[str, Any], issue_key: str) -> str:
        """Return story analysis as markdown string for saving to file."""
        lines = [
            f"# Story Analysis: {issue_key}",
            f"**{issue.get('summary', '')}**",
            "",
            "## Issue details",
            f"- **Key:** {issue.get('key', '')}",
            f"- **Status:** {issue.get('status', '')}",
            f"- **Type:** {issue.get('issue_type', '')}",
            f"- **Priority:** {issue.get('priority', '')}",
            f"- **Assignee:** {issue.get('assignee', '')}",
            f"- **Reporter:** {issue.get('reporter', '')}",
            f"- **URL:** {issue.get('url', '')}",
            "",
            "## Description",
            issue.get('description', 'No description'),
            "",
        ]
        if issue.get('acceptance_criteria'):
            lines.extend(["## Acceptance Criteria", issue.get('acceptance_criteria', ''), ""])
        lines.extend(["---", "", "## Story Analysis", ""])
        # Completeness
        c = analysis.get('completeness', {})
        lines.extend([
            "### Completeness",
            f"- Description: {'✓' if c.get('has_description') else '✗'} {c.get('description_adequacy', '')} ({c.get('description_length', 0)} chars)",
            f"- Acceptance Criteria: {'✓' if c.get('has_acceptance_criteria') else '✗'}",
        ])
        if c.get('has_acceptance_criteria'):
            ac = analysis.get('acceptance_criteria_analysis', {})
            lines.append(f"  - Criteria count: {ac.get('count', 0)}")
            lines.append(f"  - Quality: {ac.get('adequacy', '')}")
        lines.append("")
        # Quality
        q = analysis.get('quality', {})
        lines.append("### Quality")
        for s in q.get('strengths', []):
            lines.append(f"- ✓ {s}")
        for i in q.get('issues', []):
            lines.append(f"- ⚠️ {i}")
        lines.append("")
        # Clarity
        cl = analysis.get('clarity', {})
        lines.append("### Clarity")
        for s in cl.get('strengths', []):
            lines.append(f"- ✓ {s}")
        for i in cl.get('issues', []):
            lines.append(f"- ⚠️ {i}")
        lines.append("")
        # Recommendations
        recs = analysis.get('recommendations', [])
        if recs:
            lines.append("### Recommendations")
            for r in recs:
                lines.append(f"- {r}")
        else:
            lines.append("### Recommendations")
            lines.append("- ✓ Story looks well-defined!")
        return "\n".join(lines)
