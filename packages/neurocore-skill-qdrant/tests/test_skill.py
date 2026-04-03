"""Tests for QdrantSkill."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

from neurocore_skill_qdrant import QdrantSkill


class TestQdrantSkillMetadata:
    def test_skill_meta_is_set(self):
        assert hasattr(QdrantSkill, "skill_meta")
        assert isinstance(QdrantSkill.skill_meta, SkillMeta)

    def test_skill_meta_name(self):
        assert QdrantSkill.skill_meta.name == "qdrant"

    def test_skill_provides(self):
        assert "qdrant_results" in QdrantSkill.skill_meta.provides

    def test_skill_consumes(self):
        assert "qdrant_query_vector" in QdrantSkill.skill_meta.consumes
        assert "qdrant_points" in QdrantSkill.skill_meta.consumes

    def test_is_async_skill(self):
        assert issubclass(QdrantSkill, AsyncSkill)


class TestQdrantSkillConfig:
    def test_config_requires_url_and_collection(self):
        skill = QdrantSkill()
        skill.init({})
        errors = skill.validate_config()
        assert any("url" in e for e in errors)
        assert any("collection" in e for e in errors)

    def test_valid_config(self):
        skill = QdrantSkill()
        skill.init({"url": "http://localhost:6333", "collection": "test"})
        errors = skill.validate_config()
        assert errors == []


class TestQdrantSkillSearch:
    def _make_skill(self, **extra_config) -> QdrantSkill:
        skill = QdrantSkill()
        config = {"url": "http://localhost:6333", "collection": "test", **extra_config}
        skill.init(config)
        return skill

    def _make_context(self, **kwargs) -> FlowContext:
        ctx = FlowContext()
        for key, value in kwargs.items():
            ctx.set(key, value)
        return ctx

    def test_search_empty_vector_returns_empty(self):
        skill = self._make_skill()
        ctx = self._make_context(qdrant_query_vector=[])

        mock_hit = MagicMock()
        mock_hit.id = "1"
        mock_hit.score = 0.9
        mock_hit.payload = {}

        with patch("neurocore_skill_qdrant.AsyncQdrantClient", create=True) as MockClient:
            instance = AsyncMock()
            instance.search = AsyncMock(return_value=[mock_hit])
            instance.close = AsyncMock()
            MockClient.return_value = instance

            # Patch the import inside the module
            import sys
            mock_qdrant = MagicMock()
            mock_qdrant.AsyncQdrantClient = MockClient
            mock_qdrant.models = MagicMock()
            mock_qdrant.models.PointStruct = MagicMock()
            mock_qdrant.models.Filter = MagicMock()

            with patch.dict(sys.modules, {
                "qdrant_client": mock_qdrant,
                "qdrant_client.models": mock_qdrant.models,
            }):
                result = asyncio.run(skill.process(ctx))

        assert result.get("qdrant_results") == []

    def test_search_with_vector(self):
        skill = self._make_skill(top_k=3)
        ctx = self._make_context(qdrant_query_vector=[0.1, 0.2, 0.3])

        mock_hit = MagicMock()
        mock_hit.id = "abc"
        mock_hit.score = 0.95
        mock_hit.payload = {"title": "paper"}

        import sys
        mock_models = MagicMock()
        mock_models.PointStruct = MagicMock()
        mock_models.Filter = MagicMock(return_value=None)

        mock_client_instance = AsyncMock()
        mock_client_instance.search = AsyncMock(return_value=[mock_hit])
        mock_client_instance.close = AsyncMock()

        mock_qdrant_module = MagicMock()
        mock_qdrant_module.AsyncQdrantClient = MagicMock(return_value=mock_client_instance)
        mock_qdrant_module.models = mock_models

        with patch.dict(sys.modules, {
            "qdrant_client": mock_qdrant_module,
            "qdrant_client.models": mock_models,
        }):
            result = asyncio.run(skill.process(ctx))

        results = result.get("qdrant_results")
        assert isinstance(results, list)

    def test_upsert_mode_empty_points(self):
        skill = self._make_skill(mode="upsert")
        ctx = self._make_context(qdrant_points=[])

        import sys
        mock_models = MagicMock()
        mock_models.PointStruct = MagicMock()
        mock_models.Filter = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.upsert = AsyncMock()
        mock_client_instance.close = AsyncMock()

        mock_qdrant_module = MagicMock()
        mock_qdrant_module.AsyncQdrantClient = MagicMock(return_value=mock_client_instance)
        mock_qdrant_module.models = mock_models

        with patch.dict(sys.modules, {
            "qdrant_client": mock_qdrant_module,
            "qdrant_client.models": mock_models,
        }):
            result = asyncio.run(skill.process(ctx))

        mock_client_instance.upsert.assert_not_called()

    def test_failed_connection_never_raises(self):
        skill = self._make_skill()
        ctx = self._make_context(qdrant_query_vector=[0.1, 0.2])

        import sys
        mock_models = MagicMock()
        mock_models.PointStruct = MagicMock()
        mock_models.Filter = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.search = AsyncMock(side_effect=ConnectionError("refused"))
        mock_client_instance.close = AsyncMock()

        mock_qdrant_module = MagicMock()
        mock_qdrant_module.AsyncQdrantClient = MagicMock(return_value=mock_client_instance)
        mock_qdrant_module.models = mock_models

        with patch.dict(sys.modules, {
            "qdrant_client": mock_qdrant_module,
            "qdrant_client.models": mock_models,
        }):
            # Must not raise
            result = asyncio.run(skill.process(ctx))

        assert result.get("qdrant_results") == []
