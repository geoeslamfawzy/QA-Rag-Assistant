"""
Ollama Text Generator Module

Uses Ollama's /api/generate endpoint for text generation.
Follows the same patterns as OllamaEmbedder for consistency.
"""
import logging
from typing import Optional

import httpx

from rag.config import RAGConfig

logger = logging.getLogger(__name__)


class OllamaGenerator:
    """
    Text generation using local Ollama instance.

    Uses the same connection pattern as OllamaEmbedder.
    """

    DEFAULT_MODEL = "mistral"
    DEFAULT_TIMEOUT = 120  # Generation takes longer than embeddings

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize OllamaGenerator.

        Args:
            model: Model name (default: mistral)
            base_url: Ollama server URL (default: from config)
            timeout: Request timeout in seconds
        """
        self.model = model or self.DEFAULT_MODEL
        self.base_url = base_url or RAGConfig.OLLAMA_BASE_URL
        self.timeout = timeout
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

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> str:
        """
        Generate text using Ollama.

        Args:
            prompt: Input prompt
            temperature: Creativity level (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text, or empty string on failure
        """
        try:
            response = self.client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except httpx.ConnectError as e:
            logger.error("Cannot connect to Ollama at %s: %s", self.base_url, e)
            return ""
        except httpx.RequestError as e:
            logger.error("Ollama generation failed: %s", e)
            return ""
        except Exception as e:
            logger.error("Unexpected error during generation: %s", e)
            return ""

    def check_connection(self) -> bool:
        """Check if Ollama server is accessible."""
        try:
            response = self.client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def check_model_available(self) -> bool:
        """Check if generation model is available."""
        try:
            response = self.client.get("/api/tags")
            if response.status_code != 200:
                return False
            models = response.json().get("models", [])
            return any(
                m.get("name", "").startswith(self.model)
                for m in models
            )
        except Exception:
            return False

    def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
