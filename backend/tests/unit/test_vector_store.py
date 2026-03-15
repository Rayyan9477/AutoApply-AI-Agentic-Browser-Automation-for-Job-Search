"""Unit tests for app.core.matching.vector_store.VectorStore."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.core.matching.vector_store import VectorStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_index_dir(tmp_path: Path) -> Path:
    d = tmp_path / "indices"
    d.mkdir()
    return d


@pytest.fixture()
def mock_faiss() -> MagicMock:
    """Mock the faiss module with essential classes and functions."""
    faiss = MagicMock()
    # IndexFlatIP returns a mock index
    mock_index = MagicMock()
    mock_index.ntotal = 0
    mock_index.d = 384
    faiss.IndexFlatIP.return_value = mock_index
    faiss.read_index.return_value = mock_index
    faiss.normalize_L2 = MagicMock()
    return faiss


@pytest.fixture()
def mock_encoder() -> MagicMock:
    """Mock SentenceTransformer.encode returning float32 arrays."""
    encoder = MagicMock()
    encoder.encode.return_value = np.random.rand(1, 384).astype(np.float32)
    return encoder


@pytest.fixture()
def store(tmp_index_dir: Path, mock_encoder: MagicMock) -> VectorStore:
    vs = VectorStore(index_dir=tmp_index_dir)
    vs._model = mock_encoder  # bypass lazy loading
    return vs


# ---------------------------------------------------------------------------
# create_index
# ---------------------------------------------------------------------------


class TestCreateIndex:
    async def test_create_index_returns_true_on_success(
        self, store: VectorStore, mock_faiss: MagicMock
    ) -> None:
        with patch.dict("sys.modules", {"faiss": mock_faiss}):
            with patch("app.core.matching.vector_store.VectorStore._save_index_sync"):
                result = await store.create_index("jobs")
        assert result is True

    async def test_create_index_returns_false_if_exists(
        self, store: VectorStore
    ) -> None:
        # Create the file so the index "already exists"
        store._index_path("jobs").touch()
        result = await store.create_index("jobs")
        assert result is False


# ---------------------------------------------------------------------------
# add_items
# ---------------------------------------------------------------------------


class TestAddItems:
    async def test_add_items_invalidates_cache(
        self, store: VectorStore, mock_faiss: MagicMock, mock_encoder: MagicMock
    ) -> None:
        # Pre-populate cache
        mock_index = MagicMock()
        mock_index.ntotal = 0
        store._index_cache["jobs"] = (mock_index, [])

        mock_encoder.encode.return_value = np.random.rand(2, 384).astype(np.float32)

        with patch.dict("sys.modules", {"faiss": mock_faiss}):
            mock_faiss.read_index.return_value = mock_index
            with patch.object(store, "_save_index_sync"):
                with patch.object(store, "_load_index_sync", return_value=(mock_index, [])):
                    count = await store.add_items("jobs", ["text1", "text2"])

        assert count == 2
        # Cache should have been invalidated after add
        assert "jobs" not in store._index_cache

    async def test_add_items_returns_zero_for_empty_list(
        self, store: VectorStore
    ) -> None:
        result = await store.add_items("jobs", [])
        assert result == 0

    async def test_add_items_raises_on_mismatched_ids(
        self, store: VectorStore
    ) -> None:
        with pytest.raises(ValueError, match="ids length"):
            await store.add_items("jobs", ["a", "b"], ids=["id1"])


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSearch:
    async def test_search_returns_results(
        self, store: VectorStore, mock_faiss: MagicMock, mock_encoder: MagicMock
    ) -> None:
        mock_index = MagicMock()
        mock_index.ntotal = 2
        mock_index.search.return_value = (
            np.array([[0.95, 0.80]], dtype=np.float32),
            np.array([[0, 1]], dtype=np.int64),
        )
        ids = ["doc_a", "doc_b"]

        with patch.dict("sys.modules", {"faiss": mock_faiss}):
            mock_faiss.read_index.return_value = mock_index
            with patch.object(store, "_load_index_sync", return_value=(mock_index, ids)):
                results = await store.search("jobs", "python developer", top_k=2)

        assert len(results) == 2
        assert results[0]["id"] == "doc_a"
        assert results[0]["score"] == pytest.approx(0.95, abs=0.01)
        assert results[0]["rank"] == 1


# ---------------------------------------------------------------------------
# delete_index
# ---------------------------------------------------------------------------


class TestDeleteIndex:
    async def test_delete_index_invalidates_cache(
        self, store: VectorStore
    ) -> None:
        idx_path = store._index_path("jobs")
        idx_path.touch()
        store._index_cache["jobs"] = (MagicMock(), [])

        result = await store.delete_index("jobs")
        assert result is True
        assert "jobs" not in store._index_cache
        assert not idx_path.exists()

    async def test_delete_index_returns_false_if_missing(
        self, store: VectorStore
    ) -> None:
        result = await store.delete_index("nonexistent")
        assert result is False


# ---------------------------------------------------------------------------
# get_index_info
# ---------------------------------------------------------------------------


class TestGetIndexInfo:
    async def test_returns_none_for_missing_index(self, store: VectorStore) -> None:
        result = await store.get_index_info("nonexistent")
        assert result is None

    async def test_returns_info_dict(
        self, store: VectorStore, mock_faiss: MagicMock
    ) -> None:
        idx_path = store._index_path("jobs")
        idx_path.touch()

        mock_index = MagicMock()
        mock_index.ntotal = 5
        mock_index.d = 384

        with patch.dict("sys.modules", {"faiss": mock_faiss}):
            with patch.object(
                store, "_load_index_sync", return_value=(mock_index, ["a", "b", "c", "d", "e"])
            ):
                info = await store.get_index_info("jobs")

        assert info is not None
        assert info["name"] == "jobs"
        assert info["vectors"] == 5
        assert info["dimension"] == 384
        assert info["id_count"] == 5


# ---------------------------------------------------------------------------
# Model lazy loading
# ---------------------------------------------------------------------------


class TestModelLazyLoading:
    def test_model_property_returns_cached(self, store: VectorStore, mock_encoder: MagicMock) -> None:
        # _model already set by fixture
        assert store.model is mock_encoder

    def test_model_loads_on_first_access(self, tmp_index_dir: Path) -> None:
        vs = VectorStore(index_dir=tmp_index_dir)
        mock_st = MagicMock()
        mock_module = MagicMock()
        mock_module.SentenceTransformer.return_value = mock_st
        with patch.dict("sys.modules", {"sentence_transformers": mock_module}):
            result = vs.model
        assert result is mock_st


# ---------------------------------------------------------------------------
# Cache invalidation
# ---------------------------------------------------------------------------


class TestCacheInvalidation:
    def test_invalidate_removes_from_cache(self, store: VectorStore) -> None:
        store._index_cache["test"] = (MagicMock(), ["id1"])
        store._invalidate_index_cache("test")
        assert "test" not in store._index_cache

    def test_invalidate_nonexistent_is_noop(self, store: VectorStore) -> None:
        store._invalidate_index_cache("nonexistent")  # should not raise


# ---------------------------------------------------------------------------
# Search edge cases
# ---------------------------------------------------------------------------


class TestSearchEdgeCases:
    async def test_search_empty_index_returns_empty(
        self, store: VectorStore, mock_faiss: MagicMock, mock_encoder: MagicMock
    ) -> None:
        mock_index = MagicMock()
        mock_index.ntotal = 0

        with patch.dict("sys.modules", {"faiss": mock_faiss}):
            with patch.object(store, "_load_index_sync", return_value=(mock_index, [])):
                results = await store.search("jobs", "python dev", top_k=5)

        assert results == []
