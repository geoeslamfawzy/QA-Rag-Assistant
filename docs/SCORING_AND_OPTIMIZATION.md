# Scoring Logic & Optimization Guide

## Overview

This document explains the scoring algorithms used in the Local RAG Brain system and provides optimization tips for best performance.

---

## 1. HYBRID RETRIEVAL SCORING

The retrieval system combines three scoring methods:

### 1.1 Cosine Similarity (Dense Retrieval)

**Weight:** 50% (`COSINE_WEIGHT = 0.50`)

Cosine similarity measures the angle between embedding vectors:

```python
cosine_similarity = dot(A, B) / (||A|| * ||B||)
```

- Range: -1 to 1 (normalized to 0-1 for our use)
- Higher = more semantically similar
- Uses 768-dimensional embeddings from `nomic-embed-text`

**When Cosine Works Best:**
- Semantically similar but different wording
- Paraphrased content
- Conceptual matches

**Limitations:**
- May miss exact keyword matches
- Can overweight common terms

### 1.2 BM25 Scoring (Sparse Retrieval)

**Weight:** 30% (`BM25_WEIGHT = 0.30`)

BM25 (Best Match 25) is a probabilistic keyword-based ranking:

```python
BM25(q, d) = Σ IDF(qi) * (tf(qi, d) * (k1 + 1)) / (tf(qi, d) + k1 * (1 - b + b * |d|/avgdl))
```

Where:
- `IDF` = Inverse Document Frequency
- `tf` = Term Frequency
- `k1` = 1.2 (term frequency saturation)
- `b` = 0.75 (length normalization)

**When BM25 Works Best:**
- Exact keyword matches
- Technical terms
- Unique identifiers

**Limitations:**
- No semantic understanding
- Word order ignored

### 1.3 Metadata Boosting

**Weight:** 20% (`METADATA_WEIGHT = 0.20`)

Boosts based on alignment between document metadata and story context:

```python
boost = 1.0  # Base multiplier

# Domain alignment
if chunk.module in story.detected_domains:
    boost += 0.3

# Rule type priority
if chunk.rule_type in story.priority_rule_types:
    boost += 0.2

# High risk content for risky stories
if chunk.risk_level == "high" and story.has_risk_flags:
    boost += 0.2

# Keyword overlap
overlap = len(chunk.keywords & story.keywords)
boost += min(0.15, overlap * 0.05)
```

### 1.4 RRF Fusion (Reciprocal Rank Fusion)

Combines rankings from different methods:

```python
RRF_score = Σ (1 / (k + rank_i))
```

- `k = 60` (standard RRF constant)
- Rewards documents that rank highly in multiple methods
- More robust than simple score averaging

### 1.5 Final Score Calculation

```python
final_score = (
    COSINE_WEIGHT * cosine_score +
    BM25_WEIGHT * normalized_bm25_score +
    METADATA_WEIGHT * (metadata_boost - 1.0)
) * (1 + rrf_score)
```

---

## 2. VALIDATION SCORING

### 2.1 State Validator Score

```python
total_checks = max(len(states) + len(transitions), 1)
errors = count(ERROR or CRITICAL findings)
score = max(0, 1 - (errors / total_checks))
```

### 2.2 Financial Validator Score

```python
errors = count(ERROR or CRITICAL findings)
warnings = count(WARNING findings)
score = max(0, 1 - (errors * 0.2) - (warnings * 0.05))
```

### 2.3 Rule Engine Coverage Score

```python
# Weight rules by priority
priority_weights = {
    "critical": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.3
}

total_weight = sum(weight[r.priority] for r in all_rules)
matched_weight = sum(weight[m.rule.priority] * m.relevance for m in matches)
coverage_score = min(1.0, matched_weight / total_weight)
```

### 2.4 Cross-Dependency Score

```python
risk_count = len(dependency_risks)
score = max(0, 1 - (risk_count * 0.15))
```

---

## 3. PERFORMANCE OPTIMIZATION

### 3.1 Index Building

**Current Performance:**
- ~0.5-1s per document embedding
- Full index build: ~30s for 50 documents

**Optimizations:**

1. **Batch Embedding**
   ```python
   # Instead of one-by-one
   for text in texts:
       embed(text)

   # Use batching
   embeddings = embed_batch(texts, batch_size=10)
   ```

2. **Incremental Updates**
   ```bash
   ./build-index --incremental  # Only re-embed changed files
   ```

3. **Parallel Processing**
   ```python
   # Future: Use multiprocessing for parsing
   from multiprocessing import Pool
   with Pool(4) as p:
       chunks = p.map(parse_document, files)
   ```

### 3.2 Retrieval Speed

**Current Performance:**
- Index load: ~50-100ms
- Query embedding: ~100-200ms
- Retrieval: ~50-100ms

**Optimizations:**

1. **Index Preloading**
   - Load index once at startup
   - Keep in memory for multiple queries

2. **Embedding Caching**
   ```python
   # Cache frequently used query embeddings
   query_cache = {}
   if query in query_cache:
       embedding = query_cache[query]
   ```

3. **Top-K Pruning**
   - Use smaller initial retrieval set
   - Apply expensive operations only to candidates

### 3.3 Memory Optimization

**Index Size Estimation:**
```
Per chunk:
- Content: ~1KB avg
- Embedding: 768 * 4 bytes = 3KB
- Metadata: ~0.5KB
Total per chunk: ~4.5KB

100 chunks = ~450KB
1000 chunks = ~4.5MB
```

**Optimizations:**

1. **Lazy Loading**
   - Load index only when needed
   - Unload after extended inactivity

2. **Chunking Strategy**
   - Smaller chunks = more chunks but better precision
   - Larger chunks = fewer chunks but less memory

3. **Embedding Quantization** (Future)
   ```python
   # Reduce from float32 to float16
   embedding = np.array(embedding, dtype=np.float16)
   # 50% memory reduction, minimal accuracy loss
   ```

### 3.4 Ollama Optimization

1. **Model Preloading**
   ```bash
   # Keep model loaded
   ollama run nomic-embed-text --keepalive 1h
   ```

2. **Connection Pooling**
   ```python
   # Reuse HTTP connections
   self._client = httpx.Client(http2=True)
   ```

3. **Timeout Tuning**
   ```python
   # Adjust based on hardware
   OLLAMA_TIMEOUT = 30  # Fast machine
   OLLAMA_TIMEOUT = 120  # Slower machine
   ```

---

## 4. KNOWLEDGE BASE OPTIMIZATION

### 4.1 Document Structure

**Best Practices:**

1. **Use YAML Frontmatter**
   ```markdown
   ---
   module: subscription
   rule_type: atomic_rule
   risk_level: high
   ---
   ```

2. **Consistent Headers**
   - Use `## ` (level 2) for chunks
   - Keep header names descriptive

3. **Chunk Size**
   - Target: 200-500 words per chunk
   - Too small: loses context
   - Too large: dilutes relevance

### 4.2 Keyword Optimization

1. **Include Domain Keywords**
   - Add technical terms
   - Include common variations

2. **Cross-References**
   - Mention related modules
   - Link to dependencies

3. **Examples**
   - Include concrete examples
   - Use realistic values

### 4.3 Rule Formatting

**Optimal Rule Format:**
```markdown
## RULE-001: Descriptive Rule Name
**Condition:** When this applies
**Validation:** What must be true
**Error:** Error message if violated
**Priority:** high|medium|low
**Keywords:** keyword1, keyword2, keyword3
```

---

## 5. TUNING PARAMETERS

### 5.1 Retrieval Weights

Adjust in `rag/config.py`:

```python
# More semantic matching
COSINE_WEIGHT = 0.60
BM25_WEIGHT = 0.25
METADATA_WEIGHT = 0.15

# More keyword matching
COSINE_WEIGHT = 0.40
BM25_WEIGHT = 0.45
METADATA_WEIGHT = 0.15

# More domain alignment
COSINE_WEIGHT = 0.45
BM25_WEIGHT = 0.25
METADATA_WEIGHT = 0.30
```

### 5.2 Similarity Thresholds

```python
# Stricter matching (fewer, higher quality results)
MIN_SIMILARITY_THRESHOLD = 0.5

# More lenient (more results, may include noise)
MIN_SIMILARITY_THRESHOLD = 0.2
```

### 5.3 Top-K Settings

```python
# Quick analysis
TOP_K = 5

# Comprehensive analysis
TOP_K = 15

# Maximum for edge cases
MAX_RESULTS = 20
```

### 5.4 Chunk Settings

```python
# Smaller, more precise chunks
MIN_CHUNK_SIZE = 30
MAX_CHUNK_SIZE = 1000

# Larger, more contextual chunks
MIN_CHUNK_SIZE = 100
MAX_CHUNK_SIZE = 3000
```

---

## 6. DEBUGGING RETRIEVAL

### 6.1 Verbose Mode

```bash
./rag-brain CMB-35047 --verbose
```

Shows:
- Retrieval scores breakdown
- Matched keywords
- Ranking details

### 6.2 Test Retrieval

```bash
./rag-brain retrieve "subscription upgrade payment" --verbose --top-k 10
```

### 6.3 Score Explanation

Check the generated prompt for score breakdowns:

```markdown
**[chunk_id]** (Module: subscription)
*Relevance: 85.3%*
```

### 6.4 Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Low scores | All results < 0.3 | Check query quality, add keywords to KB |
| Wrong results | Irrelevant chunks retrieved | Improve metadata, check rule types |
| Missing results | Expected content not found | Verify document is in KB, rebuild index |
| Slow retrieval | > 1s per query | Check Ollama performance, reduce TOP_K |

---

## 7. BENCHMARKING

### 7.1 Measure Performance

```python
import time

start = time.time()
results = retriever.retrieve(query)
elapsed = time.time() - start
print(f"Retrieval took {elapsed:.3f}s")
```

### 7.2 Quality Metrics

- **Precision@K**: % of top-K results that are relevant
- **Recall@K**: % of relevant docs in top-K
- **MRR**: Mean Reciprocal Rank of first relevant result

### 7.3 A/B Testing Weights

1. Create baseline with default weights
2. Test with adjusted weights
3. Compare retrieval quality on test queries
4. Select best configuration

---

## 8. RECOMMENDED DEFAULTS

Based on testing, these defaults work well for QA analysis:

```python
# Balanced retrieval
COSINE_WEIGHT = 0.50
BM25_WEIGHT = 0.30
METADATA_WEIGHT = 0.20

# Good precision/recall tradeoff
MIN_SIMILARITY_THRESHOLD = 0.3
TOP_K = 10

# Reasonable chunk sizes
MIN_CHUNK_SIZE = 50
MAX_CHUNK_SIZE = 2000
CHUNK_OVERLAP = 100

# RRF standard
RRF_K = 60
```

---

*Last Updated: 2024-01-15*
