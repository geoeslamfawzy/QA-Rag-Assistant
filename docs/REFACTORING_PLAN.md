# LOCAL RAG-ENHANCED QA SYSTEM - Step-by-Step Refactoring Plan

## Overview

This document provides a detailed step-by-step plan to transform the existing Jira QA tool into a LOCAL RAG-ENHANCED QA SYSTEM.

---

## PHASE 1: FOUNDATION SETUP

### Step 1.1: Update Dependencies
**File:** `requirements.txt`

Add new dependencies:
```txt
httpx==0.27.0           # Async HTTP client for Ollama
numpy==1.26.4           # Vector operations
rank-bm25==0.2.2        # BM25 scoring
pyyaml==6.0.1           # YAML parsing
```

**Action:**
```bash
pip install httpx numpy rank-bm25 pyyaml
pip freeze > requirements.txt
```

### Step 1.2: Create Directory Structure
**Actions:**
```bash
mkdir -p rag
mkdir -p validators
mkdir -p knowledge-base/modules
mkdir -p knowledge-base/atomic_rules
mkdir -p knowledge-base/financial_logic
mkdir -p knowledge-base/state_machines
mkdir -p knowledge-base/cross_dependencies
mkdir -p .index
mkdir -p prompts
touch rag/__init__.py
touch validators/__init__.py
```

### Step 1.3: Update .gitignore
**Add:**
```gitignore
# RAG Index (can be large)
.index/

# Generated prompts (optional to track)
prompts/*.md

# Ollama cache
.ollama_cache/
```

---

## PHASE 2: RAG CORE IMPLEMENTATION

### Step 2.1: Create RAG Configuration
**File:** `rag/config.py`

Define all configuration constants:
- Ollama server URL (default: http://localhost:11434)
- Embedding model: `nomic-embed-text`
- Embedding dimension: 768
- Similarity thresholds
- Retrieval weights (cosine, BM25, metadata)
- RRF constant (k=60)
- Top-k retrieval count

### Step 2.2: Implement Ollama Embedding Integration
**File:** `rag/embeddings.py`

Implement:
1. `OllamaEmbedder` class
2. `embed_text(text: str) -> List[float]` - Single text embedding
3. `embed_batch(texts: List[str]) -> List[List[float]]` - Batch embedding
4. `check_connection()` - Verify Ollama is running
5. Error handling for connection failures

### Step 2.3: Implement Vector Index Builder
**File:** `rag/indexer.py`

Implement:
1. `IndexBuilder` class
2. `scan_knowledge_base()` - Find all markdown files
3. `parse_document(path)` - Extract chunks with metadata
4. `compute_checksum(content)` - SHA256 for change detection
5. `build_index()` - Full index build
6. `incremental_update()` - Update only changed files
7. `save_index(path)` - Persist to JSON
8. `load_index(path)` - Load from JSON

**Chunk Extraction Strategy:**
- Split by `## ` headers (level 2)
- Preserve metadata from YAML frontmatter
- Track source file and line numbers

### Step 2.4: Implement Hybrid Retriever
**File:** `rag/retriever.py`

Implement:
1. `HybridRetriever` class
2. `cosine_similarity(vec1, vec2)` - Dense similarity
3. `bm25_search(query, top_k)` - Sparse keyword search
4. `rrf_fusion(dense_ranks, sparse_ranks, k=60)` - Rank fusion
5. `metadata_boost(doc, story_context)` - Apply boosts
6. `retrieve(query, story_context, top_k)` - Main retrieval
7. `explain_scores(results)` - Debug scoring breakdown

---

## PHASE 3: STORY PRE-ANALYZER

### Step 3.1: Implement Intent Detection
**File:** `rag/story_pre_analyzer.py`

Implement:
1. `StoryPreAnalyzer` class
2. `detect_intents(story_text)` - Pattern matching for intents
3. `classify_domains(story_text)` - Map to knowledge modules
4. `identify_risk_flags(intents, domains)` - Risk assessment
5. `analyze(story)` - Main entry point returning:
   - `detected_domains`
   - `priority_rule_types`
   - `risk_flags`
   - `confidence_scores`

**Intent Patterns:**
```python
INTENT_PATTERNS = {
    "plan_switch": ["upgrade", "downgrade", "change plan", "switch subscription"],
    "referral": ["referral", "refer", "invite", "bonus", "reward"],
    "gift_card": ["gift card", "voucher", "redeem", "gift code"],
    "financial_update": ["payment", "billing", "invoice", "charge", "refund"],
    "role_change": ["role", "permission", "admin", "access level"],
    "lifecycle_change": ["activate", "deactivate", "suspend", "terminate"],
    "deletion": ["delete", "remove", "cancel", "purge"],
    "activation": ["activate", "enable", "create account", "register"]
}
```

---

## PHASE 4: VALIDATORS LAYER

### Step 4.1: Create Base Validator
**File:** `validators/base_validator.py`

Implement:
1. `BaseValidator` abstract class
2. `validate(story, knowledge_context)` - Abstract method
3. `format_results()` - Standard output format
4. Common utility methods

### Step 4.2: Implement State Validator
**File:** `validators/state_validator.py`

Implement:
1. `StateValidator(BaseValidator)` class
2. `load_state_machines()` - Parse state machine definitions
3. `extract_state_mentions(story)` - Find state references
4. `validate_transitions(story, state_machines)` - Check validity
5. `find_missing_states(story, state_machines)` - Coverage gaps
6. `validate()` - Main entry point

### Step 4.3: Implement Financial Validator
**File:** `validators/financial_validator.py`

Implement:
1. `FinancialValidator(BaseValidator)` class
2. `load_financial_rules()` - Parse financial logic
3. `detect_calculations(story)` - Find calculation mentions
4. `check_constraints(story, rules)` - Constraint violations
5. `generate_recommendations(story)` - Improvement suggestions
6. `validate()` - Main entry point

### Step 4.4: Implement Rule Engine
**File:** `validators/rule_engine.py`

Implement:
1. `RuleEngine` class
2. `load_atomic_rules()` - Parse rule definitions
3. `match_rules(story, rules)` - Semantic + keyword matching
4. `calculate_coverage(matched, total)` - Coverage score
5. `find_critical_unmatched(story, rules)` - Missing critical rules
6. `execute(story)` - Main entry point

### Step 4.5: Implement Cross-Dependency Checker
**File:** `validators/cross_dep_checker.py`

Implement:
1. `CrossDepChecker` class
2. `load_dependency_map()` - Parse dependency definitions
3. `detect_affected_modules(story)` - Module impact analysis
4. `identify_dependency_risks(modules)` - Risk chains
5. `find_integration_points(modules)` - API/webhook touchpoints
6. `check(story)` - Main entry point

---

## PHASE 5: PROMPT BUILDER

### Step 5.1: Implement Structured Prompt Builder
**File:** `rag/prompt_builder.py`

Implement:
1. `PromptBuilder` class
2. `set_story(story_data)` - Set Jira story context
3. `set_retrieved_context(chunks)` - Add retrieved knowledge
4. `set_validation_results(results)` - Add validator outputs
5. `set_pre_analysis(analysis)` - Add intent/domain analysis
6. `build()` - Assemble final prompt
7. `save(output_path)` - Write to file
8. `to_clipboard()` - Optional: copy to clipboard

---

## PHASE 6: CLI INTEGRATION

### Step 6.1: Create RAG Brain Entry Point
**File:** `rag_brain.py`

Implement:
1. Main CLI entry point
2. `handle_build_index()` - Index building command
3. `handle_generate_prompt(story_key)` - Main workflow
4. `handle_status()` - Index status display
5. Argument parsing
6. Error handling

### Step 6.2: Create Bash Wrappers
**Files:** `rag-brain`, `build-index`

```bash
#!/bin/bash
# rag-brain
exec "$(dirname "$0")/venv/bin/python3" "$(dirname "$0")/rag_brain.py" "$@"
```

```bash
#!/bin/bash
# build-index
exec "$(dirname "$0")/venv/bin/python3" "$(dirname "$0")/rag_brain.py" build-index "$@"
```

### Step 6.3: Update main.py (Optional Integration)
**File:** `main.py`

Add optional integration:
- New command: `rag` - Invoke RAG brain
- Link from existing `analyze` command

---

## PHASE 7: KNOWLEDGE BASE TEMPLATES

### Step 7.1: Create Template Files

**File:** `knowledge-base/modules/template.md`
```markdown
---
module: module_name
version: 1.0
last_updated: YYYY-MM-DD
dependencies:
  - other_module
---

# Module Name

## Overview
[Module description]

## Key Concepts
[Core concepts]

## Business Rules
[High-level rules]

## Integration Points
[APIs, webhooks, events]
```

**File:** `knowledge-base/atomic_rules/template.md`
```markdown
---
rule_type: atomic_rule
module: module_name
risk_level: high|medium|low
---

# Atomic Rules: [Domain]

## RULE-001: [Rule Name]
**Condition:** [When this applies]
**Validation:** [What must be true]
**Error:** [Expected error if violated]
**Priority:** high|medium|low

## RULE-002: [Rule Name]
...
```

**File:** `knowledge-base/state_machines/template.md`
```markdown
---
state_machine: entity_name
module: module_name
---

# State Machine: [Entity]

## States
| State | Description | Entry Conditions |
|-------|-------------|------------------|
| state_1 | ... | ... |

## Transitions
| From | To | Trigger | Validations |
|------|-----|---------|-------------|
| state_1 | state_2 | action | ... |

## Invalid Transitions
- state_a → state_b: [Reason]
```

---

## PHASE 8: TESTING & VALIDATION

### Step 8.1: Manual Testing Checklist

1. **Ollama Connection**
   ```bash
   ollama run nomic-embed-text "test"
   ```

2. **Index Building**
   ```bash
   ./build-index
   # Verify .index/vector-index.json created
   ```

3. **Prompt Generation**
   ```bash
   ./rag-brain CMB-35047
   # Verify prompts/prompt-CMB-35047.md created
   ```

4. **Retrieval Quality**
   ```bash
   ./rag-brain CMB-35047 --verbose
   # Review retrieval scores
   ```

### Step 8.2: Performance Validation

1. Index build time < 30 seconds for 100 documents
2. Retrieval time < 500ms per query
3. Memory usage < 500MB for loaded index

---

## PHASE 9: DOCUMENTATION

### Step 9.1: Update README.md

Add sections:
- RAG Brain usage
- Knowledge base structure
- Index management
- Troubleshooting

### Step 9.2: Create Sample Knowledge Base

Populate `knowledge-base/` with example content:
- 2-3 module documents
- 10-15 atomic rules
- 2-3 state machines
- 5-10 financial rules
- 2-3 cross-dependency maps

---

## EXECUTION ORDER SUMMARY

| Phase | Steps | Effort |
|-------|-------|--------|
| 1. Foundation | 1.1-1.3 | Setup |
| 2. RAG Core | 2.1-2.4 | Core |
| 3. Pre-Analyzer | 3.1 | Analysis |
| 4. Validators | 4.1-4.5 | Validation |
| 5. Prompt Builder | 5.1 | Output |
| 6. CLI | 6.1-6.3 | Integration |
| 7. Knowledge Base | 7.1 | Templates |
| 8. Testing | 8.1-8.2 | QA |
| 9. Documentation | 9.1-9.2 | Docs |

---

## ROLLBACK STRATEGY

All changes are additive:
- Existing `main.py`, `analyzer.py`, `tc_generator.py` unchanged
- New modules in separate directories (`rag/`, `validators/`)
- New CLI scripts (`rag-brain`, `build-index`)

To rollback:
```bash
rm -rf rag/ validators/ .index/ prompts/ knowledge-base/
rm rag_brain.py rag-brain build-index
# Restore original requirements.txt
```

---

*Plan Version: 1.0*
*Estimated Implementation: Self-paced*
