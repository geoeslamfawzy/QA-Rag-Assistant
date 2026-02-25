"""
Hybrid Retriever Module

Implements hybrid retrieval combining:
- Dense retrieval (cosine similarity with embeddings)
- Sparse retrieval (BM25 keyword matching)
- RRF (Reciprocal Rank Fusion) for rank combination
- Metadata boosting for domain/rule type alignment
"""

import math
import re
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field

import numpy as np
from rank_bm25 import BM25Okapi

from .config import RAGConfig, DEFAULT_CONFIG
from .embeddings import OllamaEmbedder
from .indexer import IndexBuilder, DocumentChunk


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    chunk: DocumentChunk
    final_score: float
    cosine_score: float = 0.0
    bm25_score: float = 0.0
    metadata_boost: float = 1.0
    cosine_rank: int = 0
    bm25_rank: int = 0
    rrf_score: float = 0.0
    explanation: str = ""


@dataclass
class StoryContext:
    """Context extracted from a story for retrieval."""
    text: str
    detected_domains: List[str] = field(default_factory=list)
    priority_rule_types: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


class HybridRetriever:
    """
    Hybrid retrieval system combining dense and sparse methods.

    Scoring Formula:
    final_score = (
        cosine_weight * normalized_cosine_score +
        bm25_weight * normalized_bm25_score +
        metadata_weight * metadata_boost
    ) * rrf_fusion_factor

    Features:
    - Dense cosine similarity via embeddings
    - BM25 keyword scoring
    - Reciprocal Rank Fusion
    - Metadata boosting for domain alignment
    - Score explanation for debugging
    """

    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Initialize the hybrid retriever.

        Args:
            config: RAG configuration. Uses default if not provided.
        """
        self.config = config or DEFAULT_CONFIG
        self.embedder = OllamaEmbedder(self.config)
        self.index_builder = IndexBuilder(self.config)
        self.chunks: List[DocumentChunk] = []
        self.bm25: Optional[BM25Okapi] = None
        self._loaded = False

    def load_index(self) -> bool:
        """
        Load the vector index and build BM25 index.

        Returns:
            True if loaded successfully.
        """
        if self._loaded:
            return True

        if not self.index_builder.load_index():
            return False

        self.chunks = self.index_builder.chunks

        # Build BM25 index
        self._build_bm25_index()

        self._loaded = True
        return True

    def _build_bm25_index(self):
        """Build BM25 index from loaded chunks."""
        if not self.chunks:
            return

        # Tokenize documents for BM25
        tokenized_docs = []
        for chunk in self.chunks:
            tokens = self._tokenize(chunk.content)
            tokenized_docs.append(tokens)

        self.bm25 = BM25Okapi(tokenized_docs)

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25.

        Args:
            text: Input text.

        Returns:
            List of tokens.
        """
        # Lowercase and extract words
        text = text.lower()
        tokens = re.findall(r'\b[a-zA-Z0-9]+\b', text)

        # Remove very short tokens
        tokens = [t for t in tokens if len(t) > 2]

        return tokens

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Cosine similarity score (0-1).
        """
        if not vec1 or not vec2:
            return 0.0

        a = np.array(vec1)
        b = np.array(vec2)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def dense_search(
        self,
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Perform dense retrieval using cosine similarity.

        Args:
            query_embedding: Query embedding vector.
            top_k: Number of results to return.

        Returns:
            List of (chunk_index, similarity_score) tuples.
        """
        similarities = []

        for i, chunk in enumerate(self.chunks):
            if chunk.embedding:
                score = self.cosine_similarity(query_embedding, chunk.embedding)
                similarities.append((i, score))

        # Sort by score descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def sparse_search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Perform sparse retrieval using BM25.

        Args:
            query: Query text.
            top_k: Number of results to return.

        Returns:
            List of (chunk_index, bm25_score) tuples.
        """
        if self.bm25 is None:
            return []

        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)

        # Get top-k indices
        indexed_scores = [(i, score) for i, score in enumerate(scores)]
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        return indexed_scores[:top_k]

    def rrf_fusion(
        self,
        dense_results: List[Tuple[int, float]],
        sparse_results: List[Tuple[int, float]],
        k: int = 60
    ) -> Dict[int, float]:
        """
        Combine rankings using Reciprocal Rank Fusion.

        RRF formula: score = sum(1 / (k + rank_i))

        Args:
            dense_results: Results from dense search.
            sparse_results: Results from sparse search.
            k: RRF constant (default 60).

        Returns:
            Dictionary mapping chunk_index to RRF score.
        """
        rrf_scores = {}

        # Process dense results
        for rank, (idx, _) in enumerate(dense_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (k + rank + 1)

        # Process sparse results
        for rank, (idx, _) in enumerate(sparse_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (k + rank + 1)

        return rrf_scores

    def calculate_metadata_boost(
        self,
        chunk: DocumentChunk,
        story_context: StoryContext
    ) -> float:
        """
        Calculate metadata boost for a chunk based on story context.

        Args:
            chunk: Document chunk.
            story_context: Story analysis context.

        Returns:
            Boost multiplier (1.0 = no boost).
        """
        boost = 1.0
        metadata = chunk.metadata

        # Domain alignment boost
        chunk_module = metadata.get("module", "").lower().replace(" ", "_")
        for domain in story_context.detected_domains:
            if domain.lower() in chunk_module or chunk_module in domain.lower():
                boost += self.config.DOMAIN_MATCH_BOOST
                break

        # Rule type priority boost
        chunk_rule_type = metadata.get("rule_type", "")
        if chunk_rule_type in story_context.priority_rule_types:
            boost += self.config.RULE_TYPE_MATCH_BOOST

        # High risk boost
        chunk_risk = metadata.get("risk_level", "medium")
        if chunk_risk == "high" and story_context.risk_flags:
            boost += self.config.HIGH_RISK_BOOST

        # Keyword overlap boost
        chunk_keywords = set(metadata.get("keywords", []))
        query_keywords = set(story_context.keywords)
        if chunk_keywords and query_keywords:
            overlap = len(chunk_keywords & query_keywords)
            if overlap > 0:
                boost += min(0.15, overlap * 0.05)

        return boost

    def retrieve(
        self,
        query: str,
        story_context: Optional[StoryContext] = None,
        top_k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        Perform hybrid retrieval.

        Args:
            query: Query text.
            story_context: Optional story analysis context.
            top_k: Number of results to return.

        Returns:
            List of RetrievalResult objects sorted by score.
        """
        if not self.load_index():
            return []

        top_k = top_k or self.config.TOP_K

        # Default story context if not provided
        if story_context is None:
            story_context = StoryContext(
                text=query,
                keywords=self._tokenize(query)
            )

        # Generate query embedding
        query_embedding = self.embedder.embed_text(query)

        # Dense search
        dense_results = self.dense_search(query_embedding, top_k * 2)

        # Sparse search
        sparse_results = self.sparse_search(query, top_k * 2)

        # RRF fusion
        rrf_scores = self.rrf_fusion(
            dense_results,
            sparse_results,
            k=self.config.RRF_K
        )

        # Create result objects with full scoring
        dense_scores = {idx: score for idx, score in dense_results}
        sparse_scores = {idx: score for idx, score in sparse_results}
        dense_ranks = {idx: rank for rank, (idx, _) in enumerate(dense_results)}
        sparse_ranks = {idx: rank for rank, (idx, _) in enumerate(sparse_results)}

        # Normalize BM25 scores
        max_bm25 = max((score for _, score in sparse_results), default=1.0)
        if max_bm25 == 0:
            max_bm25 = 1.0

        results = []
        for idx, rrf_score in rrf_scores.items():
            chunk = self.chunks[idx]

            cosine_score = dense_scores.get(idx, 0.0)
            bm25_score = sparse_scores.get(idx, 0.0)
            normalized_bm25 = bm25_score / max_bm25

            metadata_boost = self.calculate_metadata_boost(chunk, story_context)

            # Calculate final score
            final_score = (
                self.config.COSINE_WEIGHT * cosine_score +
                self.config.BM25_WEIGHT * normalized_bm25 +
                self.config.METADATA_WEIGHT * (metadata_boost - 1.0)
            )

            # Apply RRF as multiplier
            final_score *= (1 + rrf_score)

            # Generate explanation
            explanation = self._generate_explanation(
                cosine_score=cosine_score,
                bm25_score=bm25_score,
                normalized_bm25=normalized_bm25,
                metadata_boost=metadata_boost,
                rrf_score=rrf_score,
                final_score=final_score
            )

            result = RetrievalResult(
                chunk=chunk,
                final_score=final_score,
                cosine_score=cosine_score,
                bm25_score=bm25_score,
                metadata_boost=metadata_boost,
                cosine_rank=dense_ranks.get(idx, -1),
                bm25_rank=sparse_ranks.get(idx, -1),
                rrf_score=rrf_score,
                explanation=explanation
            )
            results.append(result)

        # Sort by final score
        results.sort(key=lambda x: x.final_score, reverse=True)

        # Filter by threshold
        results = [
            r for r in results
            if r.cosine_score >= self.config.MIN_SIMILARITY_THRESHOLD
        ]

        return results[:top_k]

    def _generate_explanation(
        self,
        cosine_score: float,
        bm25_score: float,
        normalized_bm25: float,
        metadata_boost: float,
        rrf_score: float,
        final_score: float
    ) -> str:
        """Generate human-readable scoring explanation."""
        parts = []
        parts.append(f"Cosine: {cosine_score:.3f} (weight: {self.config.COSINE_WEIGHT})")
        parts.append(f"BM25: {bm25_score:.2f} -> norm: {normalized_bm25:.3f} (weight: {self.config.BM25_WEIGHT})")
        parts.append(f"Metadata boost: {metadata_boost:.2f}")
        parts.append(f"RRF score: {rrf_score:.4f}")
        parts.append(f"Final: {final_score:.4f}")
        return " | ".join(parts)

    def explain_scores(self, results: List[RetrievalResult]) -> str:
        """
        Generate detailed score explanation for results.

        Args:
            results: List of retrieval results.

        Returns:
            Formatted explanation string.
        """
        lines = ["=" * 60, "RETRIEVAL SCORE BREAKDOWN", "=" * 60]

        for i, result in enumerate(results):
            lines.append(f"\n[{i + 1}] {result.chunk.id}")
            lines.append(f"    Module: {result.chunk.metadata.get('module', 'N/A')}")
            lines.append(f"    Rule Type: {result.chunk.metadata.get('rule_type', 'N/A')}")
            lines.append(f"    Risk Level: {result.chunk.metadata.get('risk_level', 'N/A')}")
            lines.append(f"    ---")
            lines.append(f"    Cosine Similarity: {result.cosine_score:.4f} (rank: {result.cosine_rank})")
            lines.append(f"    BM25 Score: {result.bm25_score:.4f} (rank: {result.bm25_rank})")
            lines.append(f"    Metadata Boost: {result.metadata_boost:.2f}x")
            lines.append(f"    RRF Score: {result.rrf_score:.4f}")
            lines.append(f"    ---")
            lines.append(f"    FINAL SCORE: {result.final_score:.4f}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def retrieve_by_rule_type(
        self,
        query: str,
        rule_types: List[str],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        Retrieve chunks filtered by rule type.

        Args:
            query: Query text.
            rule_types: List of rule types to filter by.
            top_k: Number of results per rule type.

        Returns:
            List of filtered results.
        """
        all_results = self.retrieve(query, top_k=top_k * 3)

        filtered = []
        for result in all_results:
            chunk_rule_type = result.chunk.metadata.get("rule_type", "")
            if chunk_rule_type in rule_types:
                filtered.append(result)

        return filtered[:top_k]

    def retrieve_by_module(
        self,
        query: str,
        modules: List[str],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        Retrieve chunks filtered by module.

        Args:
            query: Query text.
            modules: List of module names to filter by.
            top_k: Number of results.

        Returns:
            List of filtered results.
        """
        all_results = self.retrieve(query, top_k=top_k * 3)

        modules_lower = [m.lower().replace("_", " ") for m in modules]

        filtered = []
        for result in all_results:
            chunk_module = result.chunk.metadata.get("module", "").lower()
            if any(m in chunk_module or chunk_module in m for m in modules_lower):
                filtered.append(result)

        return filtered[:top_k]

    def retrieve_with_rules(
        self,
        query: str,
        story_context: Optional[StoryContext] = None,
        top_k: Optional[int] = None,
        ensure_rule_types: Optional[List[str]] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve chunks ensuring certain rule types are always included.

        This method addresses the retrieval bias where general module content
        outranks specific atomic rules in similarity search. It ensures that
        atomic_rule, state_machine, and financial_logic chunks are always
        included in the results.

        GROUNDING ENFORCEMENT:
        This method now also checks the KEYWORD_RULE_MAPPING configuration
        to force retrieval of specific rules when keyword combinations match.
        This prevents grounding failures like CMB-35293 where FIN-REF-012
        should have been cited for "referral + plan switch + expire".

        Args:
            query: Query text.
            story_context: Optional story analysis context.
            top_k: Number of regular results to return.
            ensure_rule_types: Rule types to always include (default: atomic_rule, state_machine, financial_logic).

        Returns:
            List of RetrievalResult objects with guaranteed rule type coverage.
        """
        if not self.load_index():
            return []

        top_k = top_k or self.config.TOP_K

        # Default rule types to always include
        if ensure_rule_types is None:
            ensure_rule_types = ["atomic_rule", "state_machine", "financial_logic"]

        # Step 1: Regular retrieval (similarity-based)
        regular_results = self.retrieve(query, story_context, top_k)

        # Step 2: GROUNDING ENFORCEMENT - Check keyword-to-rule mapping
        forced_rules = self._get_forced_rules_from_keywords(query, story_context)

        # Step 3: Get chunks for each ensured rule type
        # Use direct filtering from all chunks instead of re-running similarity
        seen_ids = {r.chunk.id for r in regular_results}
        additional_results = []

        for rule_type in ensure_rule_types:
            # Find chunks of this rule type that weren't in regular results
            type_chunks = [
                chunk for chunk in self.chunks
                if chunk.metadata.get("rule_type") == rule_type
                and chunk.id not in seen_ids
            ]

            if not type_chunks:
                continue

            # Generate query embedding if not already done
            query_embedding = self.embedder.embed_text(query)

            # Score these chunks by cosine similarity
            scored = []
            for chunk in type_chunks:
                if chunk.embedding:
                    score = self.cosine_similarity(query_embedding, chunk.embedding)
                    scored.append((chunk, score))

            # Sort by score and take top matches for this rule type
            scored.sort(key=lambda x: x[1], reverse=True)

            # Add top 3 of each rule type (or fewer if not available)
            for chunk, cosine_score in scored[:3]:
                if chunk.id not in seen_ids:
                    # Create a RetrievalResult for this chunk
                    result = RetrievalResult(
                        chunk=chunk,
                        final_score=cosine_score * 0.8,  # Slightly lower than regular results
                        cosine_score=cosine_score,
                        bm25_score=0.0,
                        metadata_boost=1.5,  # Boosted because it's a guaranteed rule type
                        cosine_rank=-1,  # Not from regular ranking
                        bm25_rank=-1,
                        rrf_score=0.0,
                        explanation=f"[Ensured {rule_type}] Cosine: {cosine_score:.3f}"
                    )
                    additional_results.append(result)
                    seen_ids.add(chunk.id)

        # Step 4: Force-retrieve chunks containing mandatory rules from keyword mapping
        forced_results = self._retrieve_forced_rule_chunks(forced_rules, seen_ids)
        additional_results.extend(forced_results)

        # Step 5: Merge results - regular first, then additional
        merged = regular_results + additional_results

        return merged

    def _get_forced_rules_from_keywords(
        self,
        query: str,
        story_context: Optional[StoryContext] = None
    ) -> List[str]:
        """
        Check keyword-to-rule mapping and return rules that MUST be retrieved.

        This implements the grounding enforcement mechanism to ensure
        critical business rules are always cited when relevant keywords appear.

        Args:
            query: Query text.
            story_context: Optional story context.

        Returns:
            List of rule IDs that must be included (e.g., ['FIN-REF-012', 'FIN-B2B-011']).
        """
        if not hasattr(self.config, 'KEYWORD_RULE_MAPPING'):
            return []

        query_lower = query.lower()

        # Also include keywords from story context
        all_text = query_lower
        if story_context and story_context.keywords:
            all_text += " " + " ".join(story_context.keywords).lower()

        forced_rules = []

        for mapping_name, mapping in self.config.KEYWORD_RULE_MAPPING.items():
            keywords = mapping.get("keywords", [])
            min_matches = mapping.get("min_matches", 2)
            rules = mapping.get("rules", [])

            # Count how many keywords match
            match_count = sum(1 for kw in keywords if kw.lower() in all_text)

            # If we meet the minimum match threshold, force these rules
            if match_count >= min_matches:
                forced_rules.extend(rules)

        return list(set(forced_rules))  # Deduplicate

    def _retrieve_forced_rule_chunks(
        self,
        rule_ids: List[str],
        seen_ids: set
    ) -> List[RetrievalResult]:
        """
        Retrieve chunks that contain specific rule IDs.

        This ensures grounding enforcement - if a rule ID is required,
        we find chunks mentioning that rule regardless of similarity score.

        Args:
            rule_ids: List of rule IDs to force-retrieve (e.g., ['FIN-REF-012']).
            seen_ids: Set of chunk IDs already in results.

        Returns:
            List of RetrievalResults for chunks containing the forced rules.
        """
        if not rule_ids:
            return []

        results = []

        for chunk in self.chunks:
            if chunk.id in seen_ids:
                continue

            content_upper = chunk.content.upper()

            # Check if this chunk contains any of the required rule IDs
            for rule_id in rule_ids:
                if rule_id in content_upper:
                    result = RetrievalResult(
                        chunk=chunk,
                        final_score=0.95,  # High score - forced retrieval
                        cosine_score=0.0,
                        bm25_score=0.0,
                        metadata_boost=2.0,  # Maximum boost for grounding enforcement
                        cosine_rank=-1,
                        bm25_rank=-1,
                        rrf_score=0.0,
                        explanation=f"[GROUNDING ENFORCEMENT] Contains required rule: {rule_id}"
                    )
                    results.append(result)
                    seen_ids.add(chunk.id)
                    break  # Only add chunk once even if multiple rules match

        return results

    def close(self):
        """Close resources."""
        self.embedder.close()


# Convenience functions

def quick_retrieve(query: str, top_k: int = 5) -> List[RetrievalResult]:
    """
    Quick retrieval without creating a context.

    Args:
        query: Query text.
        top_k: Number of results.

    Returns:
        List of retrieval results.
    """
    retriever = HybridRetriever()
    results = retriever.retrieve(query, top_k=top_k)
    retriever.close()
    return results


if __name__ == "__main__":
    # Quick test
    print("Testing Hybrid Retriever...")

    retriever = HybridRetriever()

    if retriever.load_index():
        print(f"Loaded {len(retriever.chunks)} chunks")

        # Test query
        results = retriever.retrieve(
            "subscription plan upgrade payment",
            top_k=5
        )

        if results:
            print("\nTop Results:")
            print(retriever.explain_scores(results))
        else:
            print("No results found")
    else:
        print("Failed to load index. Run build_index first.")

    retriever.close()
