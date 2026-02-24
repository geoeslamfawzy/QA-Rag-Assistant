"""
Ollama Embedding Integration Module

Provides local embedding generation using Ollama with nomic-embed-text model.
No cloud services, no API keys, 100% local execution.
"""

import json
import time
from typing import List, Optional
from dataclasses import dataclass

import httpx

from .config import RAGConfig, DEFAULT_CONFIG


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""
    text: str
    embedding: List[float]
    model: str
    duration_ms: float


class OllamaConnectionError(Exception):
    """Raised when Ollama server is not reachable."""
    pass


class OllamaEmbeddingError(Exception):
    """Raised when embedding generation fails."""
    pass


class OllamaEmbedder:
    """
    Local embedding generator using Ollama.

    Uses nomic-embed-text model for high-quality, fast embeddings.
    All processing happens locally - no cloud calls.
    """

    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Initialize the Ollama embedder.

        Args:
            config: RAG configuration. Uses default if not provided.
        """
        self.config = config or DEFAULT_CONFIG
        self.base_url = self.config.OLLAMA_BASE_URL
        self.model = self.config.EMBEDDING_MODEL
        self.timeout = self.config.OLLAMA_TIMEOUT
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-loaded HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client

    def check_connection(self) -> bool:
        """
        Check if Ollama server is running and accessible.

        Returns:
            True if server is accessible, False otherwise.
        """
        try:
            response = self.client.get("/api/tags")
            return response.status_code == 200
        except httpx.RequestError:
            return False

    def check_model_available(self) -> bool:
        """
        Check if the embedding model is available.

        Returns:
            True if model is available, False otherwise.
        """
        try:
            response = self.client.get("/api/tags")
            if response.status_code != 200:
                return False

            data = response.json()
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            return self.model in models or f"{self.model}:latest" in [m.get("name", "") for m in data.get("models", [])]
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def pull_model(self) -> bool:
        """
        Pull the embedding model if not available.

        Returns:
            True if model is now available, False otherwise.
        """
        try:
            print(f"Pulling model: {self.model}...")
            response = self.client.post(
                "/api/pull",
                json={"name": self.model},
                timeout=600  # Model download can take time
            )
            return response.status_code == 200
        except httpx.RequestError as e:
            print(f"Failed to pull model: {e}")
            return False

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed.

        Returns:
            Embedding vector as list of floats.

        Raises:
            OllamaConnectionError: If server is not reachable.
            OllamaEmbeddingError: If embedding generation fails.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            start_time = time.time()

            response = self.client.post(
                "/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text.strip()
                }
            )

            if response.status_code != 200:
                raise OllamaEmbeddingError(
                    f"Embedding request failed with status {response.status_code}: {response.text}"
                )

            data = response.json()
            embedding = data.get("embedding")

            if not embedding:
                raise OllamaEmbeddingError("No embedding returned from Ollama")

            duration_ms = (time.time() - start_time) * 1000

            return embedding

        except httpx.ConnectError:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running: `ollama serve`"
            )
        except httpx.RequestError as e:
            raise OllamaConnectionError(f"Request failed: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.

        Raises:
            OllamaConnectionError: If server is not reachable.
            OllamaEmbeddingError: If embedding generation fails.
        """
        if not texts:
            return []

        embeddings = []
        batch_size = self.config.EMBEDDING_BATCH_SIZE

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                if text and text.strip():
                    embedding = self.embed_text(text)
                    embeddings.append(embedding)
                else:
                    # Empty text gets zero vector
                    embeddings.append([0.0] * self.config.EMBEDDING_DIMENSION)

        return embeddings

    def embed_with_metadata(self, text: str) -> EmbeddingResult:
        """
        Generate embedding with timing metadata.

        Args:
            text: The text to embed.

        Returns:
            EmbeddingResult with embedding and metadata.
        """
        start_time = time.time()
        embedding = self.embed_text(text)
        duration_ms = (time.time() - start_time) * 1000

        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.model,
            duration_ms=duration_ms
        )

    def get_embedding_dimension(self) -> int:
        """
        Get the embedding dimension for the current model.

        Returns:
            Embedding dimension (768 for nomic-embed-text).
        """
        return self.config.EMBEDDING_DIMENSION

    def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def verify_ollama_setup(config: Optional[RAGConfig] = None) -> dict:
    """
    Verify Ollama is properly set up for embeddings.

    Args:
        config: RAG configuration to use.

    Returns:
        Dictionary with setup status and details.
    """
    config = config or DEFAULT_CONFIG
    result = {
        "ollama_running": False,
        "model_available": False,
        "test_embedding_success": False,
        "embedding_dimension": None,
        "errors": []
    }

    embedder = OllamaEmbedder(config)

    # Check if Ollama is running
    if not embedder.check_connection():
        result["errors"].append(
            f"Ollama is not running at {config.OLLAMA_BASE_URL}. "
            "Start it with: `ollama serve`"
        )
        return result

    result["ollama_running"] = True

    # Check if model is available
    if not embedder.check_model_available():
        result["errors"].append(
            f"Model '{config.EMBEDDING_MODEL}' is not available. "
            f"Pull it with: `ollama pull {config.EMBEDDING_MODEL}`"
        )
        return result

    result["model_available"] = True

    # Test embedding
    try:
        test_embedding = embedder.embed_text("Test embedding generation")
        result["test_embedding_success"] = True
        result["embedding_dimension"] = len(test_embedding)
    except (OllamaConnectionError, OllamaEmbeddingError) as e:
        result["errors"].append(f"Test embedding failed: {e}")

    embedder.close()
    return result


if __name__ == "__main__":
    # Quick test
    print("Verifying Ollama setup...")
    status = verify_ollama_setup()

    if status["test_embedding_success"]:
        print(f"SUCCESS: Ollama is ready!")
        print(f"  - Embedding dimension: {status['embedding_dimension']}")
    else:
        print("FAILED: Ollama setup issues:")
        for error in status["errors"]:
            print(f"  - {error}")
