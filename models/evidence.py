"""
Evidence Result Model for Deterministic QA Brain

Provides verified evidence tracking to prevent fabrication of rule matches.
Evidence must be explicitly verified through keyword matching or semantic analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EvidenceResult:
    """
    Result of evidence verification for a rule match.

    This is a CRITICAL integrity component. Evidence must be VERIFIED
    before claiming a rule matches a story. No fabrication is allowed.

    Attributes:
        is_verified: Whether the evidence is verified (keyword match found)
        matched_keywords: List of keywords that matched the story
        matched_snippet: The story excerpt containing the match
        semantic_score: Semantic similarity score (0-1)
        unverified_reason: Reason if evidence is not verified
    """

    is_verified: bool
    matched_keywords: List[str] = field(default_factory=list)
    matched_snippet: Optional[str] = None
    semantic_score: float = 0.0
    unverified_reason: Optional[str] = None

    # Verification thresholds
    MIN_KEYWORD_MATCHES: int = 1
    MIN_SEMANTIC_SCORE: float = 0.3

    @classmethod
    def verified(
        cls,
        keywords: List[str],
        snippet: str,
        score: float = 1.0
    ) -> "EvidenceResult":
        """
        Create a verified evidence result.

        Args:
            keywords: List of matched keywords
            snippet: Story excerpt containing the match
            score: Semantic similarity score (0-1)

        Returns:
            EvidenceResult with is_verified=True
        """
        return cls(
            is_verified=True,
            matched_keywords=keywords,
            matched_snippet=snippet,
            semantic_score=score,
            unverified_reason=None
        )

    @classmethod
    def unverified(cls, reason: str = "No keyword overlap") -> "EvidenceResult":
        """
        Create an unverified evidence result.

        CRITICAL: This prevents fabrication. When evidence cannot be
        verified, we explicitly mark it as unverified with a reason.

        Args:
            reason: Explanation of why evidence couldn't be verified

        Returns:
            EvidenceResult with is_verified=False
        """
        return cls(
            is_verified=False,
            matched_keywords=[],
            matched_snippet=None,
            semantic_score=0.0,
            unverified_reason=reason
        )

    def get_evidence_text(self) -> str:
        """
        Get the evidence text for use in reasoning chains.

        Returns:
            Verified snippet or explicit unverified marker (NEVER fabricated)
        """
        if self.is_verified and self.matched_snippet:
            return self.matched_snippet
        else:
            return f"[UNVERIFIED - {self.unverified_reason or 'No direct keyword match in story'}]"

    def to_dict(self) -> dict:
        """Export for serialization."""
        return {
            "is_verified": self.is_verified,
            "matched_keywords": self.matched_keywords,
            "matched_snippet": self.matched_snippet,
            "semantic_score": self.semantic_score,
            "unverified_reason": self.unverified_reason,
        }

    def __str__(self) -> str:
        if self.is_verified:
            return f"Verified({len(self.matched_keywords)} keywords, score={self.semantic_score:.2f})"
        else:
            return f"Unverified({self.unverified_reason})"
