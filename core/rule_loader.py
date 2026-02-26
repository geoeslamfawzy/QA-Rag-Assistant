"""
Rule Loader for Deterministic QA Brain

Loads and parses rules from knowledge base markdown files.
Supports both legacy format and enhanced format with full metadata.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from models.rule import Rule, RiskLevel

logger = logging.getLogger(__name__)


class RuleLoader:
    """
    Loads and parses rules from knowledge base markdown files.

    Supports enhanced rule format with:
    - YAML frontmatter for file-level metadata
    - Structured rule blocks with dependencies
    - Cross-reference parsing
    - Backward compatibility with legacy formats

    Example Enhanced Format:
        ### FIN-REF-012: Payment Plan Change Reward Expiration
        **Risk Level:** critical
        **Lifecycle States:** ACTIVE
        **Depends On:** DEP-EP-006, FIN-B2B-011
        **Impacts:** referrals, payments, invoices
        **Keywords:** payment plan, switch, prepaid, postpaid, expire, reward

        **Condition:** Enterprise changes payment plan (Prepaid <-> Postpaid)

        **Validation:**
        - ALL existing referral rewards MUST be immediately invalidated

        **Error Message:** "Rewards invalidated due to payment plan change"
    """

    # Regex patterns for rule parsing
    RULE_ID_PATTERN = r'((?:FIN|RULE|DEP)-[A-Z]{1,5}-\d{3})'
    RULE_HEADER_PATTERN = r'###?\s*((?:FIN|RULE|DEP)-[A-Z0-9-]+)[:\s]+(.+?)(?=\n|$)'

    # Field extraction patterns
    FIELD_PATTERNS = {
        'risk_level': r'\*\*Risk\s*Level[:\*]*\s*\*?\*?\s*([^\n*]+)',
        'lifecycle_states': r'\*\*Lifecycle\s*States?[:\*]*\s*\*?\*?\s*([^\n*]+)',
        'depends_on': r'\*\*Depends?\s*On[:\*]*\s*\*?\*?\s*([^\n*]+)',
        'impacts': r'\*\*Impacts?[:\*]*\s*\*?\*?\s*([^\n*]+)',
        'keywords': r'\*\*Keywords?[:\*]*\s*\*?\*?\s*([^\n*]+)',
        'condition': r'\*\*Condition[:\*]*\s*\*?\*?\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)',
        'validation': r'\*\*Validation[:\*]*\s*\*?\*?\s*([\s\S]+?)(?=\*\*Error|\*\*Condition|\*\*Test|$|\n###)',
        'error_message': r'\*\*Error(?:\s*Message)?[:\*]*\s*\*?\*?\s*"?([^"\n]+)"?',
    }

    def __init__(self, knowledge_base_path: Path):
        """
        Initialize the rule loader.

        Args:
            knowledge_base_path: Path to knowledge-base directory
        """
        self.kb_path = Path(knowledge_base_path)

    def load_all_rules(self) -> List[Rule]:
        """
        Load all rules from knowledge base.

        Scans all markdown files in the knowledge base directories:
        - atomic_rules/
        - financial_logic/
        - state_machines/
        - cross_dependencies/
        - modules/

        Returns:
            List of all Rule objects found
        """
        rules: List[Rule] = []
        seen_ids: set = set()

        # Directories to scan (in priority order)
        scan_dirs = [
            'atomic_rules',
            'financial_logic',
            'state_machines',
            'cross_dependencies',
            'modules',
        ]

        for dir_name in scan_dirs:
            dir_path = self.kb_path / dir_name
            if dir_path.exists():
                for file_path in dir_path.glob('*.md'):
                    try:
                        file_rules = self.load_rules_from_file(file_path)
                        for rule in file_rules:
                            if rule.rule_id not in seen_ids:
                                rules.append(rule)
                                seen_ids.add(rule.rule_id)
                            else:
                                logger.debug(
                                    f"Duplicate rule ID {rule.rule_id} in {file_path}"
                                )
                    except Exception as e:
                        logger.error(f"Error loading rules from {file_path}: {e}")

        logger.info(f"Loaded {len(rules)} rules from knowledge base")
        return rules

    def load_rules_from_file(self, file_path: Path) -> List[Rule]:
        """
        Load rules from a specific markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            List of Rule objects found in the file
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return []

        # Parse file-level metadata from YAML frontmatter
        file_metadata = self._parse_frontmatter(content)
        content_without_frontmatter = self._remove_frontmatter(content)

        # Parse rules from content
        rules = self._parse_rules_from_content(
            content_without_frontmatter,
            file_metadata,
            str(file_path)
        )

        return rules

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """
        Parse YAML frontmatter from markdown content.

        Expected format:
        ---
        rule_type: financial_logic
        module: referrals
        risk_level: high
        ---
        """
        frontmatter_pattern = r'^---\s*\n([\s\S]*?)\n---'
        match = re.match(frontmatter_pattern, content)

        if match:
            if HAS_YAML:
                try:
                    return yaml.safe_load(match.group(1)) or {}
                except yaml.YAMLError as e:
                    logger.warning(f"Failed to parse frontmatter: {e}")
                    return {}
            else:
                # Fallback: simple key: value parsing
                result = {}
                for line in match.group(1).split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        result[key.strip()] = value.strip()
                return result

        return {}

    def _remove_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter from content."""
        return re.sub(r'^---\s*\n[\s\S]*?\n---\s*\n?', '', content)

    def _parse_rules_from_content(
        self,
        content: str,
        file_metadata: Dict[str, Any],
        source_file: str
    ) -> List[Rule]:
        """
        Parse rules from markdown content.

        Supports multiple formats:
        1. Enhanced format with structured fields
        2. Legacy format: "- RULE-XXX: Description"
        3. Header format: "### RULE-XXX: Name"
        """
        rules: List[Rule] = []
        seen_ids: set = set()

        # Strategy 1: Enhanced format with ### headers
        enhanced_rules = self._parse_enhanced_rules(content, file_metadata, source_file)
        for rule in enhanced_rules:
            if rule.rule_id not in seen_ids:
                rules.append(rule)
                seen_ids.add(rule.rule_id)

        # Strategy 2: Legacy list format
        legacy_rules = self._parse_legacy_rules(content, file_metadata, source_file)
        for rule in legacy_rules:
            if rule.rule_id not in seen_ids:
                rules.append(rule)
                seen_ids.add(rule.rule_id)

        return rules

    def _parse_enhanced_rules(
        self,
        content: str,
        file_metadata: Dict[str, Any],
        source_file: str
    ) -> List[Rule]:
        """
        Parse enhanced format rules with structured fields.

        Example:
            ### FIN-REF-012: Payment Plan Change
            **Risk Level:** critical
            **Depends On:** DEP-EP-006
            ...
        """
        rules: List[Rule] = []

        # Split by rule headers
        # Pattern matches: ### FIN-XXX-NNN: Title
        header_pattern = r'(###?\s*(?:FIN|RULE|DEP)-[A-Z0-9-]+[:\s]+[^\n]+)'
        parts = re.split(header_pattern, content)

        for i in range(1, len(parts), 2):
            if i + 1 >= len(parts):
                continue

            header = parts[i]
            body = parts[i + 1] if i + 1 < len(parts) else ""

            # Extract rule ID and name from header
            header_match = re.match(self.RULE_HEADER_PATTERN, header)
            if not header_match:
                continue

            rule_id = header_match.group(1).upper()
            rule_name = header_match.group(2).strip()

            # Parse structured fields from body
            rule = self._parse_rule_block(
                rule_id=rule_id,
                rule_name=rule_name,
                content=body,
                file_metadata=file_metadata,
                source_file=source_file
            )

            if rule:
                rules.append(rule)

        return rules

    def _parse_rule_block(
        self,
        rule_id: str,
        rule_name: str,
        content: str,
        file_metadata: Dict[str, Any],
        source_file: str
    ) -> Optional[Rule]:
        """
        Parse a single rule block with enhanced format.
        """
        # Extract fields using patterns
        fields = {}
        for field_name, pattern in self.FIELD_PATTERNS.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                fields[field_name] = match.group(1).strip()

        # Parse risk level
        risk_level = self._parse_risk_level(
            fields.get('risk_level'),
            file_metadata.get('risk_level'),
            content
        )

        # Parse lifecycle states
        lifecycle_states = self._parse_list_field(fields.get('lifecycle_states'))

        # Parse depends_on (list of rule IDs)
        depends_on = self._extract_rule_ids(fields.get('depends_on', ''))

        # Parse impacts
        impacts = self._parse_list_field(fields.get('impacts'))

        # Parse keywords
        keywords = self._parse_list_field(fields.get('keywords'))

        # Infer additional keywords from content
        keywords.extend(self._extract_keywords_from_text(content, rule_name))
        keywords = list(set(keywords))  # Deduplicate

        # Get domain and module from file metadata
        domain = file_metadata.get('module', '')
        module = file_metadata.get('rule_type', '')

        # Infer from source file path if not in metadata
        if not domain:
            domain = self._infer_domain_from_path(source_file)
        if not module:
            module = self._infer_module_from_path(source_file)

        return Rule(
            rule_id=rule_id,
            domain=domain,
            module=module,
            risk_level=risk_level,
            lifecycle_states=lifecycle_states,
            depends_on=depends_on,
            impacts=impacts,
            description=rule_name,
            condition=fields.get('condition', ''),
            validation=self._clean_validation(fields.get('validation', '')),
            error_message=fields.get('error_message', ''),
            keywords=keywords,
            source_file=source_file,
        )

    def _parse_legacy_rules(
        self,
        content: str,
        file_metadata: Dict[str, Any],
        source_file: str
    ) -> List[Rule]:
        """
        Parse legacy format rules.

        Formats supported:
        - FIN-REF-001: Description text
        - RULE-ENT-001: Description text
        - DEP-EP-001: Description text
        """
        rules: List[Rule] = []

        # Pattern: "- FIN-XXX-NNN: Description" or bullet variations
        legacy_pattern = r'[-*]\s*((?:FIN|RULE|DEP)-[A-Z]{1,5}-\d{3})[:\s]+(.+?)(?=\n[-*]\s*(?:FIN|RULE|DEP)|$)'

        matches = re.findall(legacy_pattern, content, re.DOTALL)

        for rule_id, description in matches:
            rule_id = rule_id.upper()
            description = description.strip()

            # Skip if already found as enhanced format
            if not description:
                continue

            # Extract first line as name
            lines = description.split('\n')
            rule_name = lines[0].strip()[:200]

            # Infer risk level from content
            risk_level = self._infer_risk_level(description)

            # Extract any rule ID references as dependencies
            depends_on = self._extract_rule_ids(description)
            # Remove self-reference
            depends_on = [d for d in depends_on if d != rule_id]

            # Get domain and module
            domain = file_metadata.get('module', self._infer_domain_from_path(source_file))
            module = file_metadata.get('rule_type', self._infer_module_from_path(source_file))

            rules.append(Rule(
                rule_id=rule_id,
                domain=domain,
                module=module,
                risk_level=risk_level,
                lifecycle_states=[],
                depends_on=depends_on,
                impacts=[],
                description=rule_name,
                condition='',
                validation=description,
                error_message='',
                keywords=self._extract_keywords_from_text(description, rule_name),
                source_file=source_file,
            ))

        return rules

    def _parse_risk_level(
        self,
        field_value: Optional[str],
        file_default: Optional[str],
        content: str
    ) -> RiskLevel:
        """Parse risk level from various sources."""
        # Priority: explicit field > file metadata > content inference
        if field_value:
            return RiskLevel.from_string(field_value)

        if file_default:
            return RiskLevel.from_string(file_default)

        return self._infer_risk_level(content)

    def _infer_risk_level(self, content: str) -> RiskLevel:
        """Infer risk level from content keywords."""
        content_lower = content.lower()

        critical_words = ['critical', 'must', 'required', 'block', 'immediately', 'all rewards expire']
        high_words = ['high', 'important', 'expire', 'invalid', 'financial', 'payment']
        low_words = ['low', 'optional', 'may', 'minor']

        if any(word in content_lower for word in critical_words):
            return RiskLevel.CRITICAL
        if any(word in content_lower for word in high_words):
            return RiskLevel.HIGH
        if any(word in content_lower for word in low_words):
            return RiskLevel.LOW

        return RiskLevel.MEDIUM

    def _parse_list_field(self, value: Optional[str]) -> List[str]:
        """Parse comma or newline separated list."""
        if not value:
            return []

        # Split by comma, semicolon, or newline
        items = re.split(r'[,;\n]', value)
        return [item.strip() for item in items if item.strip()]

    def _extract_rule_ids(self, text: str) -> List[str]:
        """Extract all rule IDs from text."""
        if not text:
            return []

        pattern = r'((?:FIN|RULE|DEP)-[A-Z]{1,5}-\d{3})'
        matches = re.findall(pattern, text.upper())
        return list(set(matches))

    def _extract_keywords_from_text(self, text: str, name: str) -> List[str]:
        """Extract keywords from text content."""
        # Combine name and text
        combined = f"{name} {text}".lower()

        # Remove markdown
        clean = re.sub(r'[#*`\[\](){}|]', '', combined)

        # Extract meaningful words (4+ chars)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', clean)

        # Filter stop words
        stop_words = {
            'this', 'that', 'with', 'from', 'have', 'been', 'will',
            'when', 'must', 'should', 'could', 'would', 'then',
            'given', 'condition', 'validation', 'error', 'rule',
            'true', 'false', 'null', 'none', 'example',
        }

        keywords = [w for w in words if w not in stop_words]

        # Return unique, limited to top 15
        from collections import Counter
        counts = Counter(keywords)
        return [word for word, _ in counts.most_common(15)]

    def _clean_validation(self, validation: str) -> str:
        """Clean validation text."""
        if not validation:
            return ''

        # Remove extra whitespace
        validation = re.sub(r'\n+', ' ', validation)
        validation = re.sub(r'\s+', ' ', validation)

        # Truncate if too long
        return validation.strip()[:1000]

    def _infer_domain_from_path(self, source_file: str) -> str:
        """Infer domain from file path."""
        path = Path(source_file)

        # Check parent directory name
        if path.parent.name in ['atomic_rules', 'financial_logic', 'state_machines', 'cross_dependencies', 'modules']:
            # Use file name as domain hint
            return path.stem.replace('_rules', '').replace('_logic', '').replace('_deps', '')

        return ''

    def _infer_module_from_path(self, source_file: str) -> str:
        """Infer module type from file path."""
        path = Path(source_file)
        parent = path.parent.name

        module_mapping = {
            'atomic_rules': 'atomic_rule',
            'financial_logic': 'financial_logic',
            'state_machines': 'state_machine',
            'cross_dependencies': 'cross_dependency',
            'modules': 'module',
        }

        return module_mapping.get(parent, 'unknown')
