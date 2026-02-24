# LOCAL RAG-ENHANCED QA SYSTEM - Architecture Document

## Overview

This document outlines the transformation of the existing Jira QA tool into a **LOCAL RAG-ENHANCED QA SYSTEM** that operates 100% locally without any cloud AI dependencies.

---

## 1. UPDATED PROJECT FOLDER STRUCTURE

```
AI-Demo/
├── .env                              # Jira credentials (existing)
├── .env.example.txt                  # Template (existing)
├── .gitignore                        # Updated with new ignores
├── requirements.txt                  # Updated dependencies
├── README.md                         # Updated documentation
│
├── # ===== EXISTING FILES (UNCHANGED) =====
├── main.py                           # Main CLI entry point (extended)
├── jira_client.py                    # Jira API connection (unchanged)
├── analyzer.py                       # Story analysis engine (unchanged)
├── tc_generator.py                   # Test case generation (unchanged)
├── analyze                           # Bash wrapper (unchanged)
├── generate-tc                       # Bash wrapper (unchanged)
│
├── # ===== NEW: RAG BRAIN =====
├── rag/
│   ├── __init__.py
│   ├── config.py                     # RAG configuration constants
│   ├── embeddings.py                 # Ollama embedding integration
│   ├── indexer.py                    # Vector index builder & persistence
│   ├── retriever.py                  # Hybrid retrieval (cosine + BM25 + RRF)
│   ├── story_pre_analyzer.py         # Intent detection & domain classification
│   └── prompt_builder.py             # Structured prompt assembly
│
├── # ===== NEW: VALIDATORS =====
├── validators/
│   ├── __init__.py
│   ├── base_validator.py             # Abstract base validator
│   ├── state_validator.py            # State machine validation
│   ├── financial_validator.py        # Financial logic validation
│   ├── rule_engine.py                # Atomic rule matching
│   └── cross_dep_checker.py          # Cross-module dependency detection
│
├── # ===== NEW: KNOWLEDGE BASE =====
├── knowledge-base/
│   ├── modules/                      # Module-specific knowledge
│   │   ├── user_management.md
│   │   ├── payment_processing.md
│   │   ├── subscription.md
│   │   ├── referral_system.md
│   │   ├── gift_cards.md
│   │   └── invoicing.md
│   │
│   ├── atomic_rules/                 # Testable business rules
│   │   ├── user_rules.md
│   │   ├── payment_rules.md
│   │   ├── subscription_rules.md
│   │   └── validation_rules.md
│   │
│   ├── financial_logic/              # Financial calculations & constraints
│   │   ├── pricing.md
│   │   ├── discounts.md
│   │   ├── refunds.md
│   │   └── tax_rules.md
│   │
│   ├── state_machines/               # State transition definitions
│   │   ├── user_lifecycle.md
│   │   ├── subscription_states.md
│   │   ├── order_states.md
│   │   └── payment_states.md
│   │
│   └── cross_dependencies/           # Inter-module relationships
│       ├── user_subscription_deps.md
│       ├── payment_order_deps.md
│       └── referral_gift_deps.md
│
├── # ===== NEW: VECTOR INDEX =====
├── .index/
│   ├── vector-index.json             # Persisted embeddings with metadata
│   ├── bm25-index.json               # BM25 inverted index
│   └── index-metadata.json           # Index version & checksum info
│
├── # ===== NEW: RAG CLI =====
├── rag-brain                         # New bash wrapper for RAG operations
├── build-index                       # Index builder script
│
├── # ===== EXISTING OUTPUT DIRECTORIES =====
├── analysis/                         # Analysis reports (existing)
├── test-suite/                       # Test cases (existing)
│
├── # ===== NEW: RAG OUTPUT =====
├── prompts/                          # Generated structured prompts
│   └── .gitkeep
│
├── # ===== EXISTING QA ASSISTANT =====
├── qa-assistant/                     # Existing prompts (unchanged)
│   ├── qa-system.prompt.md
│   ├── analyze.prompt.md
│   ├── generate-tc.prompt.md
│   ├── qa-guidelines.md
│   └── project-context.md
│
└── venv/                             # Virtual environment
```

---

## 2. COMPONENT RESPONSIBILITIES

### 2.1 RAG Module (`rag/`)

| File | Responsibility |
|------|----------------|
| `config.py` | Configuration constants (embedding model, similarity thresholds, weights) |
| `embeddings.py` | Ollama integration for `nomic-embed-text` embeddings |
| `indexer.py` | Build, persist, and load vector index with metadata |
| `retriever.py` | Hybrid retrieval with cosine similarity, BM25, and RRF ranking |
| `story_pre_analyzer.py` | Detect intents, domains, and risk flags from story content |
| `prompt_builder.py` | Assemble structured prompt files for manual paste |

### 2.2 Validators Module (`validators/`)

| File | Responsibility |
|------|----------------|
| `base_validator.py` | Abstract base class for all validators |
| `state_validator.py` | Validate state transitions against state machine definitions |
| `financial_validator.py` | Check financial logic (calculations, constraints) |
| `rule_engine.py` | Match story content against atomic rules |
| `cross_dep_checker.py` | Detect cross-module dependencies and risks |

### 2.3 Knowledge Base (`knowledge-base/`)

| Directory | Content Type |
|-----------|--------------|
| `modules/` | High-level module documentation and context |
| `atomic_rules/` | Specific, testable business rules with IDs |
| `financial_logic/` | Financial calculations, pricing, discounts |
| `state_machines/` | State definitions and valid transitions |
| `cross_dependencies/` | Inter-module relationships and impacts |

---

## 3. DATA FLOW ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER WORKFLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   1. Jira Story Key (e.g., CMB-35047)                                        │
│              │                                                                │
│              ▼                                                                │
│   ┌─────────────────────┐                                                    │
│   │    Jira Client      │  ← Existing, fetches story details                 │
│   └─────────────────────┘                                                    │
│              │                                                                │
│              ▼                                                                │
│   ┌─────────────────────┐                                                    │
│   │ Story Pre-Analyzer  │  ← NEW: Detect intents, domains, risk flags       │
│   └─────────────────────┘                                                    │
│              │                                                                │
│              ├──────────────────────────────────────────┐                    │
│              ▼                                          ▼                    │
│   ┌─────────────────────┐                    ┌─────────────────────┐        │
│   │  Hybrid Retriever   │                    │     Validators      │        │
│   │  (Cosine + BM25)    │                    │  ┌───────────────┐  │        │
│   │       + RRF         │                    │  │ State         │  │        │
│   └─────────────────────┘                    │  │ Financial     │  │        │
│              │                               │  │ Rule Engine   │  │        │
│              │ Retrieved                     │  │ Cross-Dep     │  │        │
│              │ Knowledge                     │  └───────────────┘  │        │
│              │ Chunks                        └─────────────────────┘        │
│              │                                          │                    │
│              │                                          │ Validation         │
│              │                                          │ Results            │
│              ▼                                          ▼                    │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                       PROMPT BUILDER                              │      │
│   │  Assembles:                                                       │      │
│   │  - Jira story details                                            │      │
│   │  - Retrieved knowledge context                                    │      │
│   │  - Matched atomic rules                                          │      │
│   │  - State validation results                                       │      │
│   │  - Financial validation results                                   │      │
│   │  - Cross-module risk flags                                       │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│              │                                                                │
│              ▼                                                                │
│   ┌─────────────────────┐                                                    │
│   │  prompts/           │                                                    │
│   │  prompt-CMB-35047.md│  ← Structured prompt file saved                   │
│   └─────────────────────┘                                                    │
│              │                                                                │
│              ▼                                                                │
│   ┌─────────────────────┐                                                    │
│   │  Manual Paste to    │  ← User manually copies to Claude Pro             │
│   │  Claude Pro Browser │                                                    │
│   └─────────────────────┘                                                    │
│              │                                                                │
│              ▼                                                                │
│   ┌─────────────────────┐                                                    │
│   │  QA Analysis +      │  ← Claude Pro generates analysis                   │
│   │  Test Cases Output  │                                                    │
│   └─────────────────────┘                                                    │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. VECTOR INDEX SCHEMA

### 4.1 Index Entry Structure

```json
{
  "id": "atomic_rules/user_rules/rule_001",
  "content": "User registration requires valid email format and phone verification...",
  "embedding": [0.123, -0.456, ...],  // 768-dimensional nomic-embed-text
  "metadata": {
    "module": "user_management",
    "rule_type": "atomic_rule",
    "risk_level": "high",
    "dependencies": ["payment_processing", "subscription"],
    "keywords": ["registration", "email", "phone", "verification"],
    "source_file": "knowledge-base/atomic_rules/user_rules.md",
    "checksum": "sha256:abc123...",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 4.2 Index Metadata File

```json
{
  "version": "1.0.0",
  "embedding_model": "nomic-embed-text",
  "embedding_dimension": 768,
  "total_documents": 150,
  "last_built": "2024-01-15T10:30:00Z",
  "source_checksums": {
    "modules/": "sha256:...",
    "atomic_rules/": "sha256:...",
    "financial_logic/": "sha256:...",
    "state_machines/": "sha256:...",
    "cross_dependencies/": "sha256:..."
  }
}
```

---

## 5. HYBRID RETRIEVAL SCORING

### 5.1 Scoring Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Cosine Similarity | 0.50 | Dense semantic similarity via embeddings |
| BM25 Score | 0.30 | Sparse keyword matching |
| Metadata Boost | 0.20 | Domain/rule-type alignment boost |

### 5.2 RRF (Reciprocal Rank Fusion) Formula

```
RRF_score = Σ (1 / (k + rank_i))

where:
- k = 60 (constant, standard RRF parameter)
- rank_i = rank of document in retrieval method i
```

### 5.3 Metadata Boost Calculation

```python
boost = 1.0

# Domain alignment boost
if doc.module in story.detected_domains:
    boost += 0.3

# Rule type priority boost
if doc.rule_type in story.priority_rule_types:
    boost += 0.2

# Risk level boost
if doc.risk_level == "high" and story.has_risk_flags:
    boost += 0.2

final_score = base_score * boost
```

---

## 6. STORY PRE-ANALYZER INTENTS

### 6.1 Detected Intent Types

| Intent | Detection Patterns |
|--------|-------------------|
| `plan_switch` | "upgrade", "downgrade", "change plan", "switch subscription" |
| `referral` | "referral", "refer", "invite", "bonus", "reward" |
| `gift_card` | "gift card", "voucher", "redeem", "gift code" |
| `financial_update` | "payment", "billing", "invoice", "charge", "refund" |
| `role_change` | "role", "permission", "admin", "access level" |
| `lifecycle_change` | "activate", "deactivate", "suspend", "terminate" |
| `deletion` | "delete", "remove", "cancel", "purge" |
| `activation` | "activate", "enable", "create account", "register" |

### 6.2 Pre-Analyzer Output

```python
{
    "detected_domains": ["subscription", "payment_processing"],
    "priority_rule_types": ["atomic_rule", "state_machine"],
    "risk_flags": ["financial_impact", "state_transition"],
    "confidence_scores": {
        "plan_switch": 0.85,
        "financial_update": 0.72
    }
}
```

---

## 7. VALIDATION OUTPUTS

### 7.1 State Validator Output

```python
{
    "valid_transitions": ["active → suspended", "active → cancelled"],
    "invalid_transitions": ["cancelled → active"],
    "missing_states": ["pending_verification"],
    "warnings": ["No rollback path defined for 'suspended' state"]
}
```

### 7.2 Financial Validator Output

```python
{
    "calculations_detected": ["proration", "discount_application"],
    "constraints_violated": [],
    "warnings": ["Tax calculation not specified for international users"],
    "recommendations": ["Add refund calculation logic"]
}
```

### 7.3 Rule Engine Output

```python
{
    "matched_rules": [
        {"id": "SUB-001", "content": "...", "relevance": 0.92},
        {"id": "PAY-003", "content": "...", "relevance": 0.87}
    ],
    "unmatched_critical_rules": ["SUB-005"],
    "coverage_score": 0.78
}
```

### 7.4 Cross-Dependency Checker Output

```python
{
    "affected_modules": ["user_management", "notification"],
    "dependency_risks": [
        {
            "from": "subscription",
            "to": "payment_processing",
            "risk": "Payment state must be updated before subscription state"
        }
    ],
    "integration_points": ["webhook_notify", "audit_log"]
}
```

---

## 8. PROMPT BUILDER OUTPUT FORMAT

### 8.1 Structured Prompt Template

```markdown
# QA Analysis Request: [STORY-KEY]

## 1. STORY DETAILS
**Title:** [Story Title]
**Status:** [Status]
**Priority:** [Priority]
**Assignee:** [Assignee]

### Description
[Full description from Jira]

### Acceptance Criteria
[Acceptance criteria from Jira]

---

## 2. RETRIEVED KNOWLEDGE CONTEXT

### Relevant Module Documentation
[Retrieved chunks from modules/]

### Matched Atomic Rules
| Rule ID | Content | Relevance |
|---------|---------|-----------|
| [ID]    | [Content] | [Score] |

### Related State Machines
[Retrieved state definitions]

### Financial Logic Context
[Retrieved financial rules]

---

## 3. VALIDATION RESULTS

### State Validation
- Valid Transitions: [List]
- Invalid Transitions: [List]
- Warnings: [List]

### Financial Validation
- Detected Calculations: [List]
- Constraints: [List]
- Recommendations: [List]

### Cross-Module Dependencies
- Affected Modules: [List]
- Dependency Risks: [List]
- Integration Points: [List]

---

## 4. RISK ASSESSMENT

### Detected Intents
[List of detected intents with confidence]

### Priority Rule Types
[List of priority rule types to check]

### Risk Flags
[List of identified risks]

---

## 5. QA ANALYSIS REQUEST

Based on the above context, please provide:

1. **Gap Analysis**: Identify missing requirements or unclear specifications
2. **Edge Cases**: List edge cases based on the matched rules and state machines
3. **Test Scenarios**: Generate BDD test scenarios covering:
   - Happy path
   - Negative cases
   - Boundary conditions
   - State transitions
   - Financial calculations
4. **Risk Assessment**: Prioritize testing areas based on risk flags
5. **Cross-Module Impact**: Identify tests needed for dependent modules

---

*Generated by Local RAG Brain | [Timestamp]*
```

---

## 9. CLI COMMANDS

### 9.1 New Commands

| Command | Description |
|---------|-------------|
| `./build-index` | Build/rebuild vector index from knowledge base |
| `./rag-brain CMB-35047` | Generate structured prompt for story |
| `./rag-brain CMB-35047 --verbose` | Include debug retrieval scores |
| `./rag-brain --status` | Show index status and statistics |

### 9.2 Existing Commands (Unchanged)

| Command | Description |
|---------|-------------|
| `./analyze CMB-35047` | Basic story analysis (existing) |
| `./generate-tc CMB-35047` | Generate test cases (existing) |

---

## 10. DEPENDENCIES

### 10.1 New Python Dependencies

```txt
# Existing
jira==3.5.2
python-dotenv==1.0.0
rich==13.7.0
tabulate==0.9.0

# NEW: RAG Dependencies
httpx==0.27.0           # Async HTTP client for Ollama
numpy==1.26.4           # Vector operations
rank-bm25==0.2.2        # BM25 scoring
pyyaml==6.0.1           # YAML parsing for knowledge base
```

### 10.2 External Requirements

- **Ollama** installed locally with `nomic-embed-text` model
- No cloud services required
- No API keys for AI services

---

## 11. PERFORMANCE OPTIMIZATIONS

1. **Lazy Loading**: Load index only when needed
2. **Incremental Updates**: Only re-embed changed files
3. **Caching**: Cache embeddings in memory during session
4. **Batch Embedding**: Embed multiple chunks in single Ollama call
5. **Pre-computed BM25**: Persist BM25 index alongside vector index

---

## 12. SECURITY CONSIDERATIONS

1. **No Cloud Calls**: All processing happens locally
2. **No API Keys**: No external AI service credentials
3. **No Auto-Posting**: Never automatically post to Jira
4. **Local Storage**: All data stays on local filesystem
5. **Checksum Verification**: Validate knowledge base integrity

---

*Document Version: 1.0*
*Last Updated: [Auto-generated]*
