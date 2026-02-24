"""
Validator Pipeline Module

Open/Closed extension point for running multiple validators.

Adding a new validator requires only:
  1. Create a class that extends BaseValidator
  2. Add it to the ValidatorPipeline list at construction time

This module itself never changes when validators are added or removed.
"""
from typing import List, Dict, Any

from .base_validator import BaseValidator, ValidationResult


class ValidatorPipeline:
    """
    Runs an ordered list of validators against a story.

    Open for extension (add validators to the constructor list),
    closed for modification (this class never changes when adding validators).

    Dependencies are injected — never instantiated here (DIP).
    """

    def __init__(self, validators: List[BaseValidator]):
        self._validators = validators

    def run(
        self,
        story: Dict[str, Any],
        knowledge_context: List[Dict[str, Any]],
    ) -> Dict[str, ValidationResult]:
        """Run all validators. Returns results keyed by validator name."""
        return {
            v.name: v.validate(story, knowledge_context)
            for v in self._validators
        }

    def run_as_dicts(
        self,
        story: Dict[str, Any],
        knowledge_context: List[Dict[str, Any]],
    ) -> Dict[str, dict]:
        """Run all validators. Returns serialised dicts keyed by validator name."""
        return {
            name: result.to_dict()
            for name, result in self.run(story, knowledge_context).items()
        }
