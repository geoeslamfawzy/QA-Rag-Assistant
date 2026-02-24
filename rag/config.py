"""
RAG Configuration Module

All configuration constants for the Local RAG Brain.
No cloud services, no API keys, 100% local execution.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class RAGConfig:
    """Configuration for the Local RAG Brain."""

    # ===========================================
    # OLLAMA SETTINGS
    # ===========================================

    # Ollama server URL (local installation)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Embedding model - nomic-embed-text is fast and high quality
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # Embedding dimension for nomic-embed-text
    EMBEDDING_DIMENSION: int = 768

    # Request timeout in seconds
    OLLAMA_TIMEOUT: int = 60

    # Batch size for embedding multiple texts
    EMBEDDING_BATCH_SIZE: int = 10

    # ===========================================
    # INDEX SETTINGS
    # ===========================================

    # Index storage directory
    INDEX_DIR: Path = field(default_factory=lambda: Path(".index"))

    # Index file names
    VECTOR_INDEX_FILE: str = "vector-index.json"
    BM25_INDEX_FILE: str = "bm25-index.json"
    INDEX_METADATA_FILE: str = "index-metadata.json"

    # Knowledge base directory
    KNOWLEDGE_BASE_DIR: Path = field(default_factory=lambda: Path("knowledge-base"))

    # Supported file extensions
    SUPPORTED_EXTENSIONS: tuple = (".md", ".txt", ".yaml", ".yml")

    # Chunk settings
    MIN_CHUNK_SIZE: int = 50  # Minimum characters per chunk
    MAX_CHUNK_SIZE: int = 2000  # Maximum characters per chunk
    CHUNK_OVERLAP: int = 100  # Overlap between chunks

    # ===========================================
    # RETRIEVAL SETTINGS
    # ===========================================

    # Default number of results to retrieve
    TOP_K: int = 10

    # Maximum results to return
    MAX_RESULTS: int = 20

    # Minimum similarity threshold (0-1)
    MIN_SIMILARITY_THRESHOLD: float = 0.3

    # ===========================================
    # HYBRID SCORING WEIGHTS
    # ===========================================

    # Dense retrieval (cosine similarity) weight
    COSINE_WEIGHT: float = 0.50

    # Sparse retrieval (BM25) weight
    BM25_WEIGHT: float = 0.30

    # Metadata boost weight
    METADATA_WEIGHT: float = 0.20

    # RRF constant (standard value is 60)
    RRF_K: int = 60

    # ===========================================
    # METADATA BOOST FACTORS
    # ===========================================

    # Boost when document module matches story domain
    DOMAIN_MATCH_BOOST: float = 0.3

    # Boost when rule type matches priority
    RULE_TYPE_MATCH_BOOST: float = 0.2

    # Boost for high-risk documents when story has risk flags
    HIGH_RISK_BOOST: float = 0.2

    # ===========================================
    # OUTPUT SETTINGS
    # ===========================================

    # Output directory for generated prompts
    PROMPTS_DIR: Path = field(default_factory=lambda: Path("output/prompts"))

    # Prompt file prefix
    PROMPT_FILE_PREFIX: str = "prompt-"

    # Include debug scores in output
    INCLUDE_DEBUG_SCORES: bool = False

    # ===========================================
    # INTENT DETECTION PATTERNS
    # ===========================================

    # Yassir Mobility B2B-specific intent patterns
    INTENT_PATTERNS: Dict[str, List[str]] = field(default_factory=lambda: {
        "trip_booking": [
            "book ride", "instant trip", "scheduled trip", "multi-stop",
            "request ride", "book for", "guest booking", "rebook",
            "trip request", "ride request", "book later"
        ],
        "enterprise_management": [
            "enterprise", "activate enterprise", "deactivate enterprise",
            "legal info", "company profile", "business account",
            "enterprise status", "account activation"
        ],
        "program_config": [
            "create program", "program settings", "ride limit",
            "budget per member", "auto-approval", "geofencing",
            "program schedule", "working days", "service restriction"
        ],
        "payment_flow": [
            "prepaid", "postpaid", "top-up", "wallet balance",
            "budget limit", "invoice", "payment plan", "commission",
            "billing", "charge", "refund", "DZD"
        ],
        "gift_card": [
            "gift card", "voucher", "redeem", "revert balance",
            "card template", "gift card purchase", "remaining balance",
            "deactivate card"
        ],
        "referral": [
            "referral", "refer business", "free trips reward",
            "invoice discount", "referral link", "referred enterprise",
            "referral rule", "completed referral"
        ],
        "challenge": [
            "business challenge", "badge", "tier", "discount earned",
            "challenge progress", "copper", "bronze", "silver", "gold", "platinum",
            "upcoming challenge", "ongoing challenge"
        ],
        "user_management": [
            "invite users", "rider", "business admin", "super admin",
            "program moderator", "user role", "group assignment",
            "CSV invite", "bulk invite", "user verification"
        ],
        "group_management": [
            "create group", "delete group", "migrate members",
            "group assignment", "default group"
        ],
        "role_change": [
            "promote", "demote", "super admin", "moderator",
            "permission", "access level", "role assignment"
        ],
        "lifecycle_change": [
            "activate", "deactivate", "suspend", "terminate",
            "enterprise status", "program status", "inactive"
        ],
        "deletion": [
            "delete", "remove", "cancel", "archive",
            "delete enterprise", "delete program", "delete group"
        ]
    })

    # ===========================================
    # DOMAIN MAPPINGS
    # ===========================================

    # Map intents to Yassir Mobility knowledge base modules
    INTENT_TO_DOMAIN: Dict[str, List[str]] = field(default_factory=lambda: {
        "trip_booking": ["trips", "b2b_portal", "programs", "payments"],
        "enterprise_management": ["admin_panel", "enterprises", "b2b_portal"],
        "program_config": ["programs", "b2b_portal", "trips"],
        "payment_flow": ["payments", "b2b_pricing", "admin_panel"],
        "gift_card": ["gift_cards", "gift_card_logic", "payments"],
        "referral": ["referrals", "referral_rewards", "payments"],
        "challenge": ["challenges", "admin_panel", "payments"],
        "user_management": ["programs", "b2b_portal", "admin_panel"],
        "group_management": ["programs", "b2b_portal"],
        "role_change": ["b2b_portal", "admin_panel", "programs"],
        "lifecycle_change": ["enterprises", "admin_panel", "programs"],
        "deletion": ["enterprises", "programs", "admin_panel"]
    })

    # ===========================================
    # RISK LEVEL MAPPINGS
    # ===========================================

    # Risk levels by intent (Yassir Mobility specific)
    INTENT_RISK_LEVELS: Dict[str, str] = field(default_factory=lambda: {
        "trip_booking": "high",
        "enterprise_management": "critical",
        "program_config": "medium",
        "payment_flow": "critical",
        "gift_card": "high",
        "referral": "high",
        "challenge": "medium",
        "user_management": "medium",
        "group_management": "low",
        "role_change": "high",
        "lifecycle_change": "critical",
        "deletion": "critical"
    })

    # ===========================================
    # RULE TYPES
    # ===========================================

    RULE_TYPES: List[str] = field(default_factory=lambda: [
        "atomic_rule",
        "state_machine",
        "financial_logic",
        "cross_dependency",
        "validation_rule",
        "business_rule"
    ])

    def __post_init__(self):
        """Ensure paths are Path objects."""
        if isinstance(self.INDEX_DIR, str):
            self.INDEX_DIR = Path(self.INDEX_DIR)
        if isinstance(self.KNOWLEDGE_BASE_DIR, str):
            self.KNOWLEDGE_BASE_DIR = Path(self.KNOWLEDGE_BASE_DIR)
        if isinstance(self.PROMPTS_DIR, str):
            self.PROMPTS_DIR = Path(self.PROMPTS_DIR)

    @property
    def vector_index_path(self) -> Path:
        """Full path to vector index file."""
        return self.INDEX_DIR / self.VECTOR_INDEX_FILE

    @property
    def bm25_index_path(self) -> Path:
        """Full path to BM25 index file."""
        return self.INDEX_DIR / self.BM25_INDEX_FILE

    @property
    def index_metadata_path(self) -> Path:
        """Full path to index metadata file."""
        return self.INDEX_DIR / self.INDEX_METADATA_FILE

    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.INDEX_DIR.mkdir(parents=True, exist_ok=True)
        self.PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        self.KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)


# Default configuration instance
DEFAULT_CONFIG = RAGConfig()
