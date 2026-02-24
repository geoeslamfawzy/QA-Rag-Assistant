"""
State Validator Module

Validates state machine transitions mentioned in stories
against defined state machine rules.
"""

import re
from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass

from .base_validator import BaseValidator, ValidationResult, Severity


@dataclass
class StateTransition:
    """A state transition found in the story."""
    from_state: str
    to_state: str
    trigger: Optional[str] = None
    location: Optional[str] = None


@dataclass
class StateMachineDefinition:
    """A state machine definition from knowledge base."""
    name: str
    states: Set[str]
    valid_transitions: List[Tuple[str, str]]  # (from, to)
    invalid_transitions: List[Tuple[str, str]]  # (from, to)
    terminal_states: Set[str]
    source: str


class StateValidator(BaseValidator):
    """
    Validates state transitions in stories.

    Checks:
    - All mentioned states exist in state machine
    - Transitions are valid according to rules
    - No invalid transitions are attempted
    - Terminal states are handled correctly
    - Missing states that should be mentioned
    """

    # Common state names to detect (including Yassir Mobility states)
    STATE_PATTERNS = [
        # General states
        r'\b(active|inactive|pending|suspended|cancelled|completed|failed|expired)\b',
        # Lifecycle states
        r'\b(created|initialized|processing|processed|finished|terminated)\b',
        # Status states
        r'\b(enabled|disabled|locked|unlocked|verified|unverified)\b',
        # Approval states
        r'\b(approved|rejected|draft|submitted|review|reviewed)\b',
        # Payment states
        r'\b(paid|unpaid|refunded|charged|pending_payment|payment_failed)\b',
        # Yassir Trip states
        r'\b(PENDING|ACCEPTED|DRIVER_ARRIVED|STARTED|FINISHED)\b',
        r'\b(DRIVER_CANCELED|RIDER_CANCELED|NO_DRIVER_AVAILABLE)\b',
        r'\b(DRIVER_COMING_CANCELED|DRIVER_COMING_RIDER_CANCELED)\b',
        r'\b(DRIVER_ABANDONED|RIDER_ABANDONED|ADJUSTED)\b',
        r'\b(TRIP_REQUEST_EXPIRED|TRIP_REQUEST_DECLINED|BOOK_ASSIGNED)\b',
        # Yassir Enterprise states
        r'\b(PENDING|ACTIVE|INACTIVE)\b',
        # Yassir Gift Card states
        r'\b(ACTIVE|EXPIRED|DEACTIVATED|REVERTED|EXHAUSTED)\b',
        # Yassir Challenge states
        r'\b(UPCOMING|ONGOING|COMPLETED|EXPIRED|DISABLED)\b',
        # Yassir Tier/Badge states
        r'\b(LOCKED|UNLOCKED)\b',
        # Yassir Referral states
        r'\b(AVAILABLE|USED|EXPIRED|VOIDED)\b',
    ]

    # Transition indicators
    TRANSITION_PATTERNS = [
        r'from\s+(\w+)\s+to\s+(\w+)',
        r'(\w+)\s*->\s*(\w+)',
        r'(\w+)\s*=>\s*(\w+)',
        r'change\s+(?:status|state)\s+(?:from\s+)?(\w+)\s+to\s+(\w+)',
        r'transition\s+(?:from\s+)?(\w+)\s+to\s+(\w+)',
        r'when\s+(\w+)\s+becomes?\s+(\w+)',
        r'status\s+changes?\s+to\s+(\w+)',
    ]

    def __init__(self):
        """Initialize the state validator."""
        super().__init__("StateValidator")
        self._compiled_state_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.STATE_PATTERNS
        ]
        self._compiled_transition_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.TRANSITION_PATTERNS
        ]

    def validate(
        self,
        story: Dict[str, Any],
        knowledge_context: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate state transitions in the story.

        Args:
            story: Story dictionary.
            knowledge_context: Retrieved knowledge chunks.

        Returns:
            ValidationResult with state-related findings.
        """
        result = self._create_result(
            passed=True,
            summary="State validation completed"
        )

        story_text = self._extract_story_text(story)

        # Extract states and transitions from story
        mentioned_states = self._extract_states(story_text)
        mentioned_transitions = self._extract_transitions(story_text)

        # Load state machine definitions from knowledge
        state_machines = self._load_state_machines(knowledge_context)

        result.details["mentioned_states"] = list(mentioned_states)
        result.details["mentioned_transitions"] = [
            {"from": t.from_state, "to": t.to_state}
            for t in mentioned_transitions
        ]
        result.details["state_machines_loaded"] = len(state_machines)

        # Validate states exist
        self._validate_states_exist(
            mentioned_states,
            state_machines,
            result
        )

        # Validate transitions
        self._validate_transitions(
            mentioned_transitions,
            state_machines,
            result
        )

        # Check for missing state handling
        self._check_missing_states(
            story_text,
            mentioned_states,
            state_machines,
            result
        )

        # Calculate score
        total_checks = max(len(mentioned_states) + len(mentioned_transitions), 1)
        errors = result.error_count
        result.score = max(0, 1 - (errors / total_checks))
        result.passed = errors == 0

        if not mentioned_states and not mentioned_transitions:
            result.add_info(
                "No state mentions found in story",
                suggestion="Consider if state transitions are relevant for this feature"
            )

        return result

    def _extract_states(self, text: str) -> Set[str]:
        """Extract state mentions from text."""
        states = set()

        for pattern in self._compiled_state_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    states.update(m.upper() for m in match if m)
                else:
                    states.add(match.upper())

        return states

    def _extract_transitions(self, text: str) -> List[StateTransition]:
        """Extract state transitions from text."""
        transitions = []

        for pattern in self._compiled_transition_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    from_state = match[0].upper()
                    to_state = match[1].upper()
                    transitions.append(StateTransition(
                        from_state=from_state,
                        to_state=to_state
                    ))
                elif isinstance(match, str):
                    # Single state (e.g., "status changes to X")
                    transitions.append(StateTransition(
                        from_state="*",  # Unknown origin
                        to_state=match.upper()
                    ))

        return transitions

    def _load_state_machines(
        self,
        knowledge_context: List[Dict[str, Any]]
    ) -> List[StateMachineDefinition]:
        """Load state machine definitions from knowledge context."""
        state_machines = []

        for chunk in knowledge_context:
            metadata = chunk.get("metadata", {})
            content = chunk.get("content", "")

            if metadata.get("rule_type") != "state_machine":
                continue

            # Parse state machine from content
            sm = self._parse_state_machine(content, chunk.get("id", "unknown"))
            if sm:
                state_machines.append(sm)

        return state_machines

    def _parse_state_machine(
        self,
        content: str,
        source: str
    ) -> Optional[StateMachineDefinition]:
        """Parse a state machine definition from markdown content."""
        states = set()
        valid_transitions = []
        invalid_transitions = []
        terminal_states = set()

        # Extract states from tables or lists
        state_pattern = r'\|\s*(\w+)\s*\|'
        matches = re.findall(state_pattern, content)
        for match in matches:
            if match.upper() not in ['STATE', 'FROM', 'TO', 'TRIGGER', 'DESCRIPTION']:
                states.add(match.upper())

        # Extract transitions from tables
        transition_pattern = r'\|\s*(\w+)\s*\|\s*(\w+)\s*\|'
        matches = re.findall(transition_pattern, content)
        for from_state, to_state in matches:
            from_upper = from_state.upper()
            to_upper = to_state.upper()
            if from_upper not in ['FROM', 'STATE'] and to_upper not in ['TO', 'STATE']:
                valid_transitions.append((from_upper, to_upper))
                states.add(from_upper)
                states.add(to_upper)

        # Extract invalid transitions
        invalid_pattern = r'invalid.*?(\w+)\s*(?:->|=>|to)\s*(\w+)'
        matches = re.findall(invalid_pattern, content, re.IGNORECASE)
        for from_state, to_state in matches:
            invalid_transitions.append((from_state.upper(), to_state.upper()))

        # Detect terminal states
        terminal_pattern = r'terminal.*?:\s*(.+)'
        match = re.search(terminal_pattern, content, re.IGNORECASE)
        if match:
            terminal_names = re.findall(r'\b(\w+)\b', match.group(1))
            terminal_states = set(t.upper() for t in terminal_names)

        if not states:
            return None

        name = source.split("/")[-1] if "/" in source else source

        return StateMachineDefinition(
            name=name,
            states=states,
            valid_transitions=valid_transitions,
            invalid_transitions=invalid_transitions,
            terminal_states=terminal_states,
            source=source
        )

    def _validate_states_exist(
        self,
        mentioned_states: Set[str],
        state_machines: List[StateMachineDefinition],
        result: ValidationResult
    ):
        """Check that mentioned states exist in state machines."""
        all_known_states = set()
        for sm in state_machines:
            all_known_states.update(sm.states)

        if not state_machines:
            # No state machine definitions loaded
            if mentioned_states:
                result.add_warning(
                    f"States mentioned but no state machine definitions found: {mentioned_states}",
                    suggestion="Add state machine definitions to knowledge base"
                )
            return

        for state in mentioned_states:
            if state not in all_known_states:
                result.add_warning(
                    f"State '{state}' not found in any state machine definition",
                    suggestion=f"Verify if '{state}' is a valid state or add it to state machine"
                )

    def _validate_transitions(
        self,
        transitions: List[StateTransition],
        state_machines: List[StateMachineDefinition],
        result: ValidationResult
    ):
        """Validate that mentioned transitions are valid."""
        for transition in transitions:
            if transition.from_state == "*":
                # Unknown origin - just check destination exists
                continue

            is_valid = False
            is_explicitly_invalid = False

            for sm in state_machines:
                # Check if transition is valid
                if (transition.from_state, transition.to_state) in sm.valid_transitions:
                    is_valid = True
                    result.add_info(
                        f"Valid transition: {transition.from_state} -> {transition.to_state}",
                        location=sm.name
                    )
                    break

                # Check if transition is explicitly invalid
                if (transition.from_state, transition.to_state) in sm.invalid_transitions:
                    is_explicitly_invalid = True
                    result.add_error(
                        f"Invalid transition: {transition.from_state} -> {transition.to_state}",
                        suggestion=f"This transition is explicitly marked as invalid in {sm.name}",
                        rule_id=f"SM:{sm.name}"
                    )
                    break

            if not is_valid and not is_explicitly_invalid and state_machines:
                result.add_warning(
                    f"Transition not defined: {transition.from_state} -> {transition.to_state}",
                    suggestion="Verify this transition is valid or add it to state machine"
                )

    def _check_missing_states(
        self,
        story_text: str,
        mentioned_states: Set[str],
        state_machines: List[StateMachineDefinition],
        result: ValidationResult
    ):
        """Check for states that should be mentioned but aren't."""
        story_lower = story_text.lower()

        # Keywords that suggest state handling is needed
        state_keywords = [
            "lifecycle", "status", "state", "transition",
            "activate", "deactivate", "suspend", "cancel"
        ]

        has_state_context = any(kw in story_lower for kw in state_keywords)

        if has_state_context:
            # Check for error/failure state handling
            error_states = {"FAILED", "ERROR", "REJECTED", "CANCELLED"}
            mentioned_error_states = mentioned_states & error_states

            if not mentioned_error_states:
                result.add_warning(
                    "No error/failure states mentioned",
                    suggestion="Consider what happens when the operation fails"
                )

            # Check for terminal state handling
            for sm in state_machines:
                if sm.terminal_states:
                    missing_terminal = sm.terminal_states - mentioned_states
                    if missing_terminal and mentioned_states & sm.states:
                        result.add_info(
                            f"Terminal states not mentioned: {missing_terminal}",
                            suggestion="Consider if terminal states need handling",
                            location=sm.name
                        )


if __name__ == "__main__":
    # Quick test
    validator = StateValidator()

    test_story = {
        "title": "Subscription Status Change",
        "description": """
        When a user upgrades their subscription, the status should change
        from ACTIVE to PENDING_UPGRADE, then to ACTIVE with the new plan.

        The transition CANCELLED -> ACTIVE is not allowed.
        """,
        "acceptance_criteria": [
            "Given subscription is ACTIVE",
            "When user selects upgrade",
            "Then status changes to PENDING_UPGRADE",
            "And after payment, status becomes ACTIVE"
        ]
    }

    # Mock knowledge context
    knowledge = [
        {
            "id": "state_machines/subscription",
            "content": """
            | State | Description |
            | ACTIVE | Active subscription |
            | PENDING_UPGRADE | Waiting for upgrade |
            | CANCELLED | Subscription cancelled |
            | EXPIRED | Subscription expired |

            | From | To |
            | ACTIVE | PENDING_UPGRADE |
            | PENDING_UPGRADE | ACTIVE |
            | ACTIVE | CANCELLED |

            Invalid transitions:
            - CANCELLED -> ACTIVE
            - EXPIRED -> ACTIVE
            """,
            "metadata": {"rule_type": "state_machine"}
        }
    ]

    result = validator.validate(test_story, knowledge)
    print(result.format())
