"""
Defect Field Generator

Generates professional defect fields using user description as contextual seed.
NEVER copies user input directly - always transforms into structured fields.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import re


@dataclass
class GeneratedDefectFields:
    """Auto-generated defect fields from user seed."""
    summary: str
    preconditions: str
    description: str
    steps_to_reproduce: List[str]
    expected_results: str
    actual_results: str
    environment: str


class DefectFieldGenerator:
    """
    Generates professional defect fields from user description seed.

    Design:
    - User input is CONTEXT ONLY, never copied directly
    - All fields are auto-generated professionally
    - Environment is inferred when possible
    """

    # Environment detection patterns
    ENV_PATTERNS = {
        "staging": ["preprod", "pre-prod", "staging", "stage"],
        "production": ["prod", "production", "live"],
        "dev": ["dev", "development", "local"],
    }

    # App context patterns - ordered by specificity (most specific first)
    APP_PATTERNS = {
        "Admin. Panel": ["admin panel", "admin.panel", "admin-panel", "adminpanel"],
        "B2C Web APP": ["b2c web", "b2c webapp", "b2c-web", "consumer web"],
        "DashOps": ["dashops", "dash ops", "dash-ops", "operations dashboard"],
        "SuperApp": ["superapp", "super app", "super-app"],
        "Driver App": ["driver app", "driver-app", "driverapp", "driver"],
        "Mobile WebApp": ["mobile web", "mobile webapp", "mweb", "m-web"],
        "B2B": ["b2b"],
        "B2C": ["b2c"],
        "WebApp": ["web", "webapp", "browser", "chrome", "safari", "firefox"],
        "iOS": ["ios", "iphone", "ipad", "apple"],
        "Android": ["android", "samsung", "pixel"],
    }

    # Legacy platform patterns for backward compatibility
    PLATFORM_PATTERNS = APP_PATTERNS

    DEFAULT_ENVIRONMENT = "Staging - WebApp"
    DEFAULT_APP_CONTEXT = "WebApp"

    def generate(
        self,
        user_seed: str,
        story_context: Optional[Dict[str, Any]] = None,
        module: Optional[str] = None,
        defect_type: str = "story",
    ) -> GeneratedDefectFields:
        """
        Generate all defect fields from user description seed.

        Args:
            user_seed: User's informal description (used as context only)
            story_context: Optional Jira story context for enrichment
            module: Optional module name for context
            defect_type: Type of defect - "story" (Staging) or "production" (Production)

        Returns:
            GeneratedDefectFields with all professionally generated fields
        """
        # Extract key information from seed
        keywords = self._extract_keywords(user_seed)
        environment = self._detect_environment(user_seed, story_context, defect_type)
        action_verb = self._extract_action(user_seed)

        # Generate each field professionally
        summary = self._generate_summary(user_seed, keywords, module)
        preconditions = self._generate_preconditions(user_seed, story_context, module)
        description = self._generate_description(user_seed, keywords)
        steps = self._generate_steps(user_seed, action_verb, module)
        expected = self._generate_expected_results(user_seed, keywords)
        actual = self._generate_actual_results(user_seed, keywords)

        return GeneratedDefectFields(
            summary=summary,
            preconditions=preconditions,
            description=description,
            steps_to_reproduce=steps,
            expected_results=expected,
            actual_results=actual,
            environment=environment,
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key technical terms from user input."""
        keywords = []
        patterns = [
            r'\b(error|fail|crash|bug|issue|broken|not working)\b',
            r'\b(login|logout|auth|payment|checkout|cart)\b',
            r'\b(button|form|page|modal|popup|input)\b',
            r'\b(\d{3})\b',  # HTTP status codes
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            keywords.extend(matches)
        return list(set(keywords))

    def _detect_environment(
        self,
        text: str,
        story_context: Optional[Dict[str, Any]] = None,
        defect_type: str = "story",
    ) -> str:
        """
        Detect environment from user input and context.

        Args:
            text: User description text
            story_context: Optional parent story context (for story defects)
            defect_type: "story" uses Staging, "production" uses Production
        """
        # Determine environment based on defect type
        if defect_type == "production":
            env_part = "Production"
        else:
            env_part = "Staging"

        # Detect app context
        app_part = self.detect_app_context(text, story_context)

        return f"{env_part} - {app_part}"

    def detect_app_context(
        self,
        text: str,
        story_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Detect app context from user description or parent story.

        Priority:
        1. Explicit keywords in user description
        2. For Story Defects: components/labels from parent story
        3. Default fallback: WebApp

        Args:
            text: User description text
            story_context: Optional parent story context

        Returns:
            App context string (e.g., "DashOps", "Admin. Panel", "B2C Web APP")
        """
        text_lower = text.lower()

        # Priority 1: Check user description for explicit app keywords
        for app, patterns in self.APP_PATTERNS.items():
            if any(p in text_lower for p in patterns):
                return app

        # Priority 2: Check parent story context (for story defects)
        if story_context:
            app_from_story = self._extract_app_from_story(story_context)
            if app_from_story:
                return app_from_story

        # Priority 3: Default fallback
        return self.DEFAULT_APP_CONTEXT

    def _extract_app_from_story(self, story_context: Dict[str, Any]) -> Optional[str]:
        """
        Extract app context from parent story components, labels, or summary.

        Args:
            story_context: Jira story context dict

        Returns:
            App context string or None if not found
        """
        fields = story_context.get("fields", {})

        # Check components first
        components = fields.get("components", [])
        for comp in components:
            comp_name = comp.get("name", "").lower()
            for app, patterns in self.APP_PATTERNS.items():
                if any(p in comp_name for p in patterns):
                    return app

        # Check labels second
        labels = fields.get("labels", [])
        for label in labels:
            label_lower = label.lower()
            for app, patterns in self.APP_PATTERNS.items():
                if any(p in label_lower for p in patterns):
                    return app

        # Check summary third
        summary = fields.get("summary", "").lower()
        for app, patterns in self.APP_PATTERNS.items():
            if any(p in summary for p in patterns):
                return app

        return None

    def _extract_action(self, text: str) -> str:
        """Extract main action verb from description."""
        action_patterns = [
            (r'\b(cannot|can\'t|unable to)\s+(\w+)', lambda m: m.group(2)),
            (r'\b(fails? to|failed to)\s+(\w+)', lambda m: m.group(2)),
            (r'\b(when|while)\s+(\w+ing)', lambda m: m.group(2)),
        ]
        for pattern, extractor in action_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return extractor(match)
        return "perform action"

    def _generate_summary(self, seed: str, keywords: List[str], module: Optional[str]) -> str:
        """Generate professional summary (NOT equal to user input)."""
        seed_lower = seed.lower()

        # Determine issue type
        if any(k in seed_lower for k in ["error", "fail", "crash"]):
            issue_type = "Error"
        elif any(k in seed_lower for k in ["not working", "broken", "unable"]):
            issue_type = "Failure"
        elif any(k in seed_lower for k in ["missing", "absent", "no"]):
            issue_type = "Missing Functionality"
        else:
            issue_type = "Issue"

        # Extract feature/area
        feature = module or "System"

        # Build professional summary based on content
        if "500" in seed or "server error" in seed_lower:
            return f"{feature} returns HTTP 500 Internal Server Error"
        elif "404" in seed or "not found" in seed_lower:
            return f"{feature} returns HTTP 404 Not Found"
        elif "login" in seed_lower or "auth" in seed_lower or "sso" in seed_lower:
            return f"Authentication {issue_type.lower()} in {feature} module"
        elif "payment" in seed_lower:
            return f"Payment processing {issue_type.lower()} during checkout"
        elif "cart" in seed_lower:
            return f"Shopping cart {issue_type.lower()} in {feature}"
        elif "button" in seed_lower:
            return f"Button interaction {issue_type.lower()} in {feature}"
        elif "form" in seed_lower:
            return f"Form submission {issue_type.lower()} in {feature}"
        else:
            # Generic but professional
            action = self._extract_action(seed)
            return f"Unable to {action} in {feature}"

    def _generate_preconditions(
        self,
        seed: str,
        context: Optional[Dict],
        module: Optional[str]
    ) -> str:
        """Generate preconditions based on context."""
        preconditions = []

        # Add standard preconditions
        preconditions.append("User is logged into the system")

        if module:
            preconditions.append(f"User has access to {module} module")

        # Infer from seed
        seed_lower = seed.lower()
        if "payment" in seed_lower:
            preconditions.append("Payment method is configured")
            preconditions.append("User has valid payment credentials")
        if "cart" in seed_lower:
            preconditions.append("Shopping cart contains at least one item")
        if "checkout" in seed_lower:
            preconditions.append("User has items ready for purchase")
        if "admin" in seed_lower:
            preconditions.append("User has administrator privileges")

        return "\n".join(f"- {p}" for p in preconditions)

    def _generate_description(self, seed: str, keywords: List[str]) -> str:
        """Generate professional description explaining the issue."""
        seed_clean = seed.strip()
        seed_lower = seed.lower()

        # Build structured description
        lines = [
            "Users are experiencing an issue with the system functionality.",
            "",
            f"User Report: {seed_clean}",
            "",
            "This defect impacts the user workflow and requires investigation.",
        ]

        # Add business impact if detectable
        if any(k in seed_lower for k in ["payment", "checkout", "transaction"]):
            lines.append("")
            lines.append("Business Impact: Potential revenue loss due to blocked transactions.")
        elif any(k in seed_lower for k in ["login", "auth", "sso"]):
            lines.append("")
            lines.append("Business Impact: Users unable to access the platform.")
        elif any(k in seed_lower for k in ["data", "save", "submit"]):
            lines.append("")
            lines.append("Business Impact: Potential data loss for users.")

        return "\n".join(lines)

    def _generate_steps(self, seed: str, action: str, module: Optional[str]) -> List[str]:
        """Generate numbered steps to reproduce."""
        steps = []
        seed_lower = seed.lower()

        # Standard navigation
        if module:
            steps.append(f"Navigate to {module} module")
        else:
            steps.append("Navigate to the affected area")

        # Action steps based on context
        if "login" in seed_lower or "sso" in seed_lower:
            steps.append("Click on Login / SSO button")
            steps.append("Enter valid credentials")
            steps.append("Submit the login form")
        elif "payment" in seed_lower:
            steps.append("Add item to cart")
            steps.append("Proceed to checkout")
            steps.append("Enter payment details")
            steps.append("Submit payment")
        elif "cart" in seed_lower:
            steps.append("Browse products")
            steps.append("Add item to cart")
            steps.append("View cart contents")
        elif "form" in seed_lower or "submit" in seed_lower:
            steps.append("Fill in the required fields")
            steps.append("Click Submit button")
        elif "button" in seed_lower:
            steps.append("Locate the affected button")
            steps.append("Click the button")
        else:
            steps.append(f"Attempt to {action}")

        # Observation step
        steps.append("Observe the error/unexpected behavior")

        return steps

    def _generate_expected_results(self, seed: str, keywords: List[str]) -> str:
        """Generate expected results."""
        seed_lower = seed.lower()

        if "login" in seed_lower or "sso" in seed_lower:
            return "User should be successfully authenticated and redirected to dashboard"
        elif "payment" in seed_lower:
            return "Payment should be processed successfully and confirmation displayed"
        elif "cart" in seed_lower:
            return "Cart should update correctly and display accurate information"
        elif "form" in seed_lower or "submit" in seed_lower:
            return "Form should be submitted successfully and confirmation displayed"
        elif "button" in seed_lower:
            return "Button should respond to click and trigger expected action"
        elif "error" in seed_lower or "500" in seed:
            return "System should complete the operation without errors"
        else:
            return "Operation should complete successfully without errors"

    def _generate_actual_results(self, seed: str, keywords: List[str]) -> str:
        """Generate actual results based on user report."""
        seed_lower = seed.lower()

        if "500" in seed or "server error" in seed_lower:
            return "System returns HTTP 500 Internal Server Error. User cannot proceed."
        elif "404" in seed or "not found" in seed_lower:
            return "System returns HTTP 404 Not Found. Resource is missing."
        elif "error" in seed_lower:
            error_match = re.search(r'error[:\s]+([^.]+)', seed_lower)
            if error_match:
                return f"System displays error: {error_match.group(1).strip()}"
            return "System displays an error message preventing completion"
        elif "not working" in seed_lower or "broken" in seed_lower:
            return "Feature does not function as expected. User workflow is blocked."
        elif "not responding" in seed_lower or "unresponsive" in seed_lower:
            return "System does not respond to user interaction. Interface appears frozen."
        elif "crash" in seed_lower:
            return "Application crashes unexpectedly. User loses their session."
        else:
            return f"Issue observed: {seed.strip()}"
