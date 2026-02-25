"""
Vector Index Builder Module

Builds and persists the vector index from the knowledge base.
Supports incremental updates based on file checksums.
"""

import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict

import yaml

from .config import RAGConfig, DEFAULT_CONFIG
from .embeddings import OllamaEmbedder, OllamaConnectionError


@dataclass
class DocumentChunk:
    """A chunk of a document with metadata."""
    id: str
    content: str
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        # Ensure metadata values are JSON serializable
        serializable_metadata = {}
        for key, value in self.metadata.items():
            if hasattr(value, 'isoformat'):  # Handle date/datetime objects
                serializable_metadata[key] = value.isoformat()
            else:
                serializable_metadata[key] = value

        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": serializable_metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DocumentChunk':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            embedding=data.get("embedding", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class IndexMetadata:
    """Metadata about the vector index."""
    version: str = "1.0.0"
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768
    total_documents: int = 0
    total_chunks: int = 0
    last_built: str = ""
    source_checksums: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'IndexMetadata':
        """Create from dictionary."""
        return cls(
            version=data.get("version", "1.0.0"),
            embedding_model=data.get("embedding_model", "nomic-embed-text"),
            embedding_dimension=data.get("embedding_dimension", 768),
            total_documents=data.get("total_documents", 0),
            total_chunks=data.get("total_chunks", 0),
            last_built=data.get("last_built", ""),
            source_checksums=data.get("source_checksums", {})
        )


class IndexBuilder:
    """
    Builds and manages the vector index.

    Features:
    - Scans knowledge base for markdown files
    - Parses YAML frontmatter for metadata
    - Chunks documents by headers
    - Generates embeddings via Ollama
    - Persists index to JSON
    - Supports incremental updates
    """

    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Initialize the index builder.

        Args:
            config: RAG configuration. Uses default if not provided.
        """
        self.config = config or DEFAULT_CONFIG
        self.embedder = OllamaEmbedder(self.config)
        self.chunks: List[DocumentChunk] = []
        self.metadata = IndexMetadata(
            embedding_model=self.config.EMBEDDING_MODEL,
            embedding_dimension=self.config.EMBEDDING_DIMENSION
        )

    def scan_knowledge_base(self) -> List[Path]:
        """
        Scan the knowledge base directory for supported files.

        Returns:
            List of file paths found.
        """
        kb_path = self.config.KNOWLEDGE_BASE_DIR
        if not kb_path.exists():
            print(f"Knowledge base directory not found: {kb_path}")
            return []

        files = []
        for ext in self.config.SUPPORTED_EXTENSIONS:
            files.extend(kb_path.rglob(f"*{ext}"))

        return sorted(files)

    def compute_checksum(self, content: str) -> str:
        """
        Compute SHA256 checksum of content.

        Args:
            content: Text content to hash.

        Returns:
            SHA256 hex digest.
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def compute_file_checksum(self, file_path: Path) -> str:
        """
        Compute checksum of a file.

        Args:
            file_path: Path to file.

        Returns:
            SHA256 hex digest.
        """
        content = file_path.read_text(encoding='utf-8')
        return self.compute_checksum(content)

    def parse_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        Parse YAML frontmatter from markdown content.

        Args:
            content: Full file content.

        Returns:
            Tuple of (metadata dict, remaining content).
        """
        frontmatter = {}
        body = content

        # Check for YAML frontmatter (--- at start)
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                except yaml.YAMLError:
                    pass

        return frontmatter, body

    def chunk_document(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """
        Split document into chunks based on headers.

        Args:
            content: Document content (without frontmatter).
            file_path: Source file path for metadata.

        Returns:
            List of chunk dictionaries.
        """
        chunks = []

        # Split by ## headers (level 2)
        sections = re.split(r'\n(?=## )', content)

        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            # Skip very small chunks
            if len(section) < self.config.MIN_CHUNK_SIZE:
                continue

            # Extract header if present
            header_match = re.match(r'^##\s+(.+?)(?:\n|$)', section)
            header = header_match.group(1) if header_match else f"Section {i + 1}"

            # Handle very large chunks by further splitting
            if len(section) > self.config.MAX_CHUNK_SIZE:
                sub_chunks = self._split_large_chunk(section, file_path, header)
                chunks.extend(sub_chunks)
            else:
                chunks.append({
                    "content": section,
                    "header": header,
                    "section_index": i,
                    "source_file": str(file_path)
                })

        # If no headers found, treat whole content as one chunk
        if not chunks and content.strip():
            if len(content) > self.config.MAX_CHUNK_SIZE:
                chunks = self._split_large_chunk(content, file_path, "Content")
            else:
                chunks.append({
                    "content": content.strip(),
                    "header": "Content",
                    "section_index": 0,
                    "source_file": str(file_path)
                })

        return chunks

    def _split_large_chunk(
        self,
        content: str,
        file_path: Path,
        base_header: str
    ) -> List[Dict[str, Any]]:
        """
        Split a large chunk into smaller pieces.

        Args:
            content: Large content to split.
            file_path: Source file path.
            base_header: Base header name.

        Returns:
            List of smaller chunk dictionaries.
        """
        chunks = []
        max_size = self.config.MAX_CHUNK_SIZE
        overlap = self.config.CHUNK_OVERLAP

        # Split by paragraphs first
        paragraphs = re.split(r'\n\n+', content)

        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            if len(current_chunk) + len(para) < max_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk.strip():
                    chunks.append({
                        "content": current_chunk.strip(),
                        "header": f"{base_header} (part {chunk_index + 1})",
                        "section_index": chunk_index,
                        "source_file": str(file_path)
                    })
                    chunk_index += 1

                # Start new chunk with overlap
                if overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-overlap:]
                    current_chunk = overlap_text + para + "\n\n"
                else:
                    current_chunk = para + "\n\n"

        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                "content": current_chunk.strip(),
                "header": f"{base_header} (part {chunk_index + 1})" if chunk_index > 0 else base_header,
                "section_index": chunk_index,
                "source_file": str(file_path)
            })

        return chunks

    def extract_metadata_from_path(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from file path structure.

        Args:
            file_path: Path to document.

        Returns:
            Metadata dictionary.
        """
        parts = file_path.parts
        kb_index = -1

        # Find knowledge-base in path
        for i, part in enumerate(parts):
            if part == "knowledge-base":
                kb_index = i
                break

        metadata = {
            "source_file": str(file_path),
            "file_name": file_path.name,
            "rule_type": "general",
            "module": "unknown",
            "risk_level": "medium"
        }

        if kb_index >= 0 and kb_index + 1 < len(parts):
            # Get subdirectory (modules, atomic_rules, etc.)
            subdir = parts[kb_index + 1]

            # Map subdirectory to rule type
            subdir_to_rule_type = {
                "modules": "module",
                "atomic_rules": "atomic_rule",
                "financial_logic": "financial_logic",
                "state_machines": "state_machine",
                "cross_dependencies": "cross_dependency"
            }
            metadata["rule_type"] = subdir_to_rule_type.get(subdir, "general")

            # Extract module from filename
            module_name = file_path.stem.replace("_", " ").replace("-", " ")
            metadata["module"] = module_name

        return metadata

    def parse_document(self, file_path: Path) -> List[DocumentChunk]:
        """
        Parse a document into chunks with metadata.

        Args:
            file_path: Path to document.

        Returns:
            List of DocumentChunk objects.
        """
        content = file_path.read_text(encoding='utf-8')

        # Parse frontmatter
        frontmatter, body = self.parse_frontmatter(content)

        # Extract metadata from path
        path_metadata = self.extract_metadata_from_path(file_path)

        # Merge frontmatter with path metadata (frontmatter takes precedence)
        base_metadata = {**path_metadata, **frontmatter}

        # Add checksum
        base_metadata["checksum"] = self.compute_checksum(content)
        base_metadata["created_at"] = datetime.now().isoformat()
        base_metadata["updated_at"] = datetime.now().isoformat()

        # Extract keywords from content
        keywords = self._extract_keywords(body)
        base_metadata["keywords"] = keywords

        # Extract rule IDs from entire document (file-level)
        file_rule_ids = self._extract_rule_ids(body)
        base_metadata["file_rule_ids"] = file_rule_ids

        # Chunk the document
        raw_chunks = self.chunk_document(body, file_path)

        # Create DocumentChunk objects
        doc_chunks = []
        relative_path = file_path.relative_to(self.config.KNOWLEDGE_BASE_DIR)

        for i, chunk_data in enumerate(raw_chunks):
            chunk_id = f"{relative_path.stem}/{chunk_data['header'].lower().replace(' ', '_')}_{i}"

            # Extract rule IDs specific to this chunk's content
            chunk_rule_ids = self._extract_rule_ids(chunk_data["content"])

            chunk_metadata = {
                **base_metadata,
                "header": chunk_data["header"],
                "section_index": chunk_data["section_index"],
                "rule_ids": chunk_rule_ids,  # Chunk-specific rule IDs
            }

            doc_chunk = DocumentChunk(
                id=chunk_id,
                content=chunk_data["content"],
                metadata=chunk_metadata
            )
            doc_chunks.append(doc_chunk)

        return doc_chunks

    def _extract_rule_ids(self, content: str) -> List[str]:
        """
        Extract RULE-XXX-NNN identifiers from content.

        Matches patterns like RULE-ENT-001, RULE-PAY-015, RULE-REF-007, etc.

        Args:
            content: Text content to search.

        Returns:
            List of unique rule IDs found.
        """
        # Match RULE-XXX-NNN pattern (2-5 uppercase letters, 3 digits)
        pattern = r'RULE-[A-Z]{2,5}-\d{3}'
        matches = re.findall(pattern, content)
        return list(set(matches))  # Return unique rule IDs

    def _extract_keywords(self, content: str, max_keywords: int = 20) -> List[str]:
        """
        Extract keywords from content.

        Args:
            content: Text content.
            max_keywords: Maximum number of keywords.

        Returns:
            List of keywords.
        """
        # Remove markdown formatting
        clean = re.sub(r'[#*`\[\](){}]', '', content)
        clean = re.sub(r'\s+', ' ', clean)

        # Extract words (at least 4 characters)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', clean.lower())

        # Count occurrences
        word_counts = {}
        for word in words:
            if word not in ['that', 'this', 'with', 'from', 'have', 'will', 'been', 'were', 'they', 'their']:
                word_counts[word] = word_counts.get(word, 0) + 1

        # Sort by frequency and return top keywords
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_keywords]]

    def build_index(self, force_rebuild: bool = False) -> bool:
        """
        Build the full vector index.

        Args:
            force_rebuild: If True, rebuild even if no changes detected.

        Returns:
            True if index was built successfully.
        """
        print("Building vector index...")

        # Verify Ollama connection
        if not self.embedder.check_connection():
            print("ERROR: Ollama is not running. Start it with: ollama serve")
            return False

        if not self.embedder.check_model_available():
            print(f"Model '{self.config.EMBEDDING_MODEL}' not available. Pulling...")
            if not self.embedder.pull_model():
                print("ERROR: Failed to pull model")
                return False

        # Scan knowledge base
        files = self.scan_knowledge_base()
        if not files:
            print("No files found in knowledge base")
            return False

        print(f"Found {len(files)} files in knowledge base")

        # Parse all documents
        self.chunks = []
        total_chunks = 0

        for file_path in files:
            print(f"  Processing: {file_path.name}")
            try:
                doc_chunks = self.parse_document(file_path)
                self.chunks.extend(doc_chunks)
                total_chunks += len(doc_chunks)
            except Exception as e:
                print(f"    ERROR: {e}")
                continue

        print(f"Created {total_chunks} chunks from {len(files)} documents")

        # Log chunk statistics by rule_type
        rule_type_counts = {}
        total_rule_ids = 0
        for chunk in self.chunks:
            rt = chunk.metadata.get("rule_type", "unknown")
            rule_type_counts[rt] = rule_type_counts.get(rt, 0) + 1
            total_rule_ids += len(chunk.metadata.get("rule_ids", []))

        print("  Chunks by rule_type:")
        for rt, count in sorted(rule_type_counts.items()):
            print(f"    {rt}: {count}")
        print(f"  Total rule IDs extracted: {total_rule_ids}")

        # Generate embeddings
        print("Generating embeddings...")
        for i, chunk in enumerate(self.chunks):
            try:
                chunk.embedding = self.embedder.embed_text(chunk.content)
                if (i + 1) % 10 == 0:
                    print(f"  Embedded {i + 1}/{len(self.chunks)} chunks")
            except OllamaConnectionError as e:
                print(f"ERROR: {e}")
                return False

        print(f"Generated embeddings for {len(self.chunks)} chunks")

        # Update metadata
        self.metadata.total_documents = len(files)
        self.metadata.total_chunks = len(self.chunks)
        self.metadata.last_built = datetime.now().isoformat()

        # Compute source checksums
        for file_path in files:
            rel_path = str(file_path.relative_to(self.config.KNOWLEDGE_BASE_DIR))
            self.metadata.source_checksums[rel_path] = self.compute_file_checksum(file_path)

        # Save index
        self.save_index()

        print(f"Index built successfully!")
        print(f"  Documents: {self.metadata.total_documents}")
        print(f"  Chunks: {self.metadata.total_chunks}")

        return True

    def save_index(self):
        """Save the index to disk."""
        self.config.ensure_directories()

        # Save vector index
        index_data = {
            "chunks": [chunk.to_dict() for chunk in self.chunks]
        }
        with open(self.config.vector_index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)

        # Save metadata
        with open(self.config.index_metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata.to_dict(), f, indent=2)

        print(f"Index saved to {self.config.INDEX_DIR}")

    def load_index(self) -> bool:
        """
        Load the index from disk.

        Returns:
            True if index was loaded successfully.
        """
        if not self.config.vector_index_path.exists():
            print("No index found. Run build_index() first.")
            return False

        try:
            # Load vector index
            with open(self.config.vector_index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            self.chunks = [
                DocumentChunk.from_dict(chunk_data)
                for chunk_data in index_data.get("chunks", [])
            ]

            # Load metadata
            if self.config.index_metadata_path.exists():
                with open(self.config.index_metadata_path, 'r', encoding='utf-8') as f:
                    metadata_data = json.load(f)
                self.metadata = IndexMetadata.from_dict(metadata_data)

            print(f"Index loaded: {len(self.chunks)} chunks")
            return True

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading index: {e}")
            return False

    def get_changed_files(self) -> List[Path]:
        """
        Get list of files that have changed since last index build.

        Returns:
            List of changed file paths.
        """
        if not self.config.index_metadata_path.exists():
            return self.scan_knowledge_base()

        # Load existing metadata
        with open(self.config.index_metadata_path, 'r', encoding='utf-8') as f:
            old_metadata = json.load(f)

        old_checksums = old_metadata.get("source_checksums", {})

        changed = []
        for file_path in self.scan_knowledge_base():
            rel_path = str(file_path.relative_to(self.config.KNOWLEDGE_BASE_DIR))
            current_checksum = self.compute_file_checksum(file_path)

            if rel_path not in old_checksums or old_checksums[rel_path] != current_checksum:
                changed.append(file_path)

        return changed

    def incremental_update(self) -> bool:
        """
        Update only changed files in the index.

        Returns:
            True if update was successful.
        """
        changed_files = self.get_changed_files()

        if not changed_files:
            print("No changes detected. Index is up to date.")
            return True

        print(f"Found {len(changed_files)} changed files")

        # Load existing index
        if not self.load_index():
            return self.build_index()

        # Remove old chunks from changed files
        changed_sources = {str(f) for f in changed_files}
        self.chunks = [
            chunk for chunk in self.chunks
            if chunk.metadata.get("source_file") not in changed_sources
        ]

        # Add new chunks for changed files
        for file_path in changed_files:
            print(f"  Updating: {file_path.name}")
            try:
                doc_chunks = self.parse_document(file_path)

                # Generate embeddings
                for chunk in doc_chunks:
                    chunk.embedding = self.embedder.embed_text(chunk.content)

                self.chunks.extend(doc_chunks)

                # Update checksum
                rel_path = str(file_path.relative_to(self.config.KNOWLEDGE_BASE_DIR))
                self.metadata.source_checksums[rel_path] = self.compute_file_checksum(file_path)

            except Exception as e:
                print(f"    ERROR: {e}")
                continue

        # Update metadata
        self.metadata.total_chunks = len(self.chunks)
        self.metadata.last_built = datetime.now().isoformat()

        # Save updated index
        self.save_index()

        print(f"Index updated successfully!")
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get index status information.

        Returns:
            Status dictionary.
        """
        status = {
            "index_exists": self.config.vector_index_path.exists(),
            "total_chunks": 0,
            "total_documents": 0,
            "last_built": None,
            "embedding_model": self.config.EMBEDDING_MODEL,
            "knowledge_base_files": len(self.scan_knowledge_base()),
            "changed_files": 0
        }

        if self.config.index_metadata_path.exists():
            with open(self.config.index_metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            status["total_chunks"] = metadata.get("total_chunks", 0)
            status["total_documents"] = metadata.get("total_documents", 0)
            status["last_built"] = metadata.get("last_built")

            # Count changed files
            status["changed_files"] = len(self.get_changed_files())

        return status


if __name__ == "__main__":
    # Quick test
    builder = IndexBuilder()
    status = builder.get_status()

    print("Index Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
