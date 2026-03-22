"""FAISS-backed vector store with async interface and safe caching.

Provides semantic search over text collections using sentence-transformer
embeddings and FAISS similarity indices. All public methods are async;
FAISS and model calls are dispatched to a thread executor.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class VectorStore:
    """FAISS-backed vector store with async interface and safe caching.

    Args:
        index_dir: Directory where FAISS index files and metadata are persisted.
        model_name: HuggingFace sentence-transformer model identifier.
    """

    def __init__(
        self,
        index_dir: Path,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.index_dir = index_dir
        self.model_name = model_name
        self._model: Any = None
        self._index_cache: dict[str, tuple[Any, list[str]]] = {}
        self.index_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------

    @property
    def model(self) -> Any:
        """Lazily load the SentenceTransformer model on first access."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("loading_embedding_model", model=self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _invalidate_index_cache(self, index_name: str) -> None:
        """Remove a cached index so the next access reloads from disk."""
        self._index_cache.pop(index_name, None)
        logger.debug("index_cache_invalidated", index=index_name)

    def _index_path(self, index_name: str) -> Path:
        return self.index_dir / f"{index_name}.faiss"

    def _meta_path(self, index_name: str) -> Path:
        return self.index_dir / f"{index_name}_meta.json"

    # ------------------------------------------------------------------
    # Synchronous helpers (run inside executor)
    # ------------------------------------------------------------------

    def _load_index_sync(self, index_name: str) -> tuple[Any, list[str]]:
        """Load a FAISS index and its ID list from disk (blocking)."""
        import faiss

        if index_name in self._index_cache:
            return self._index_cache[index_name]

        idx_path = self._index_path(index_name)
        meta_path = self._meta_path(index_name)

        if not idx_path.exists():
            raise FileNotFoundError(f"Index '{index_name}' not found at {idx_path}")

        index = faiss.read_index(str(idx_path))
        ids: list[str] = []
        if meta_path.exists():
            ids = json.loads(meta_path.read_text(encoding="utf-8"))

        self._index_cache[index_name] = (index, ids)
        logger.debug("index_loaded_from_disk", index=index_name, vectors=index.ntotal)
        return index, ids

    def _save_index_sync(
        self, index_name: str, index: Any, ids: list[str]
    ) -> None:
        """Persist a FAISS index and its ID list to disk (blocking)."""
        import faiss

        faiss.write_index(index, str(self._index_path(index_name)))
        self._meta_path(index_name).write_text(
            json.dumps(ids, ensure_ascii=False), encoding="utf-8"
        )
        self._index_cache[index_name] = (index, ids)

    def _encode_sync(self, texts: list[str]) -> np.ndarray:
        """Encode texts to embeddings (blocking)."""
        embeddings: np.ndarray = self.model.encode(
            texts, show_progress_bar=False, convert_to_numpy=True
        )
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        return embeddings.astype(np.float32)

    # ------------------------------------------------------------------
    # Async executor helper
    # ------------------------------------------------------------------

    async def _run_sync(self, func: Any, *args: Any) -> Any:
        """Run a blocking function in the default thread executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def create_index(self, index_name: str, dimension: int = 384) -> bool:
        """Create a new empty FAISS index.

        Args:
            index_name: Unique identifier for the index.
            dimension: Embedding vector dimension (must match model output).

        Returns:
            True if the index was created, False if it already exists.
        """
        if self._index_path(index_name).exists():
            logger.warning("index_already_exists", index=index_name)
            return False

        import faiss

        def _create() -> None:
            index = faiss.IndexFlatIP(dimension)
            self._save_index_sync(index_name, index, [])

        await self._run_sync(_create)
        logger.info("index_created", index=index_name, dimension=dimension)
        return True

    async def delete_index(self, index_name: str) -> bool:
        """Delete a FAISS index and its metadata from disk.

        Args:
            index_name: Name of the index to delete.

        Returns:
            True if deleted, False if the index did not exist.
        """
        idx_path = self._index_path(index_name)
        meta_path = self._meta_path(index_name)

        if not idx_path.exists():
            logger.warning("index_not_found_for_delete", index=index_name)
            return False

        idx_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        self._invalidate_index_cache(index_name)
        logger.info("index_deleted", index=index_name)
        return True

    async def add_items(
        self,
        index_name: str,
        texts: list[str],
        ids: list[str] | None = None,
    ) -> int:
        """Encode texts and add them to an existing index.

        Args:
            index_name: Target index name.
            texts: Raw text strings to embed and store.
            ids: Optional document IDs. Auto-generated UUIDs if omitted.

        Returns:
            Number of vectors added.

        Raises:
            FileNotFoundError: If the index does not exist.
            ValueError: If ids length does not match texts length.
        """
        if not texts:
            return 0

        if ids is not None and len(ids) != len(texts):
            raise ValueError(
                f"ids length ({len(ids)}) must match texts length ({len(texts)})"
            )

        item_ids = ids if ids is not None else [uuid.uuid4().hex for _ in texts]
        embeddings = await self._run_sync(self._encode_sync, texts)

        def _add() -> int:
            import faiss

            faiss.normalize_L2(embeddings)
            index, existing_ids = self._load_index_sync(index_name)
            index.add(embeddings)
            existing_ids.extend(item_ids)
            self._save_index_sync(index_name, index, existing_ids)
            return len(texts)

        count = await self._run_sync(_add)
        self._invalidate_index_cache(index_name)
        logger.info("items_added", index=index_name, count=count)
        return count

    async def search(
        self,
        index_name: str,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Search the index for the most similar items to a query.

        Args:
            index_name: Index to search.
            query: Natural-language query string.
            top_k: Maximum number of results to return.

        Returns:
            List of dicts with keys ``id``, ``score``, and ``rank``.

        Raises:
            FileNotFoundError: If the index does not exist.
        """
        query_vec = await self._run_sync(self._encode_sync, [query])

        def _search() -> list[dict[str, Any]]:
            import faiss

            faiss.normalize_L2(query_vec)
            index, ids = self._load_index_sync(index_name)

            actual_k = min(top_k, index.ntotal)
            if actual_k == 0:
                return []

            distances, indices = index.search(query_vec, actual_k)
            results: list[dict[str, Any]] = []
            for rank, (dist, idx) in enumerate(
                zip(distances[0], indices[0], strict=False), start=1
            ):
                if idx == -1:
                    continue
                doc_id = ids[int(idx)] if int(idx) < len(ids) else str(idx)
                results.append(
                    {"id": doc_id, "score": float(dist), "rank": rank}
                )
            return results

        results = await self._run_sync(_search)
        logger.debug(
            "search_completed",
            index=index_name,
            query_len=len(query),
            results=len(results),
        )
        return results

    async def get_index_info(self, index_name: str) -> dict[str, Any] | None:
        """Return metadata about an index.

        Args:
            index_name: Index to inspect.

        Returns:
            Dict with ``name``, ``vectors``, ``dimension``, and ``file_size_bytes``,
            or None if the index does not exist.
        """
        idx_path = self._index_path(index_name)
        if not idx_path.exists():
            return None

        def _info() -> dict[str, Any]:
            index, ids = self._load_index_sync(index_name)
            return {
                "name": index_name,
                "vectors": index.ntotal,
                "dimension": index.d,
                "id_count": len(ids),
                "file_size_bytes": idx_path.stat().st_size,
            }

        return await self._run_sync(_info)
