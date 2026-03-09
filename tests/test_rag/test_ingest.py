"""Tests for the document ingestion pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.rag.ingest import (
    _chunk_document,
    _extract_section_title,
    _extract_yaml_front_matter,
    _infer_metadata_from_content,
    _infer_metadata_from_filename,
    _replace_images,
    ingest_single_report,
)


class TestExtractYamlFrontMatter:
    def test_valid_yaml(self):
        content = '---\nproject_name: Arbitrum\ntrack: Layer2\n---\n\n# Report'
        metadata, remaining = _extract_yaml_front_matter(content)
        assert metadata["project_name"] == "Arbitrum"
        assert metadata["track"] == "Layer2"
        assert "# Report" in remaining
        assert "---" not in remaining

    def test_no_front_matter(self):
        content = "# Just a heading\n\nSome content."
        metadata, remaining = _extract_yaml_front_matter(content)
        assert metadata == {}
        assert remaining == content

    def test_malformed_yaml(self):
        content = '---\n[invalid: yaml: {{{\n---\n\nContent'
        metadata, remaining = _extract_yaml_front_matter(content)
        assert metadata == {}
        assert remaining == content


class TestInferMetadataFromFilename:
    def test_snake_case_report(self):
        result = _infer_metadata_from_filename("arbitrum_research_report.md")
        assert result["project_name"] == "Arbitrum"

    def test_multi_word(self):
        result = _infer_metadata_from_filename("my_cool_project_report.md")
        assert result["project_name"] == "My Cool Project"

    def test_simple_name(self):
        result = _infer_metadata_from_filename("bitcoin.md")
        assert result["project_name"] == "Bitcoin"


class TestInferMetadataFromContent:
    def test_chinese_language_detection(self):
        content = "这是一份关于 Arbitrum 的深度研究报告，分析了项目的各个方面。" * 10
        result = _infer_metadata_from_content(content)
        assert result["language"] == "zh"

    def test_english_language_detection(self):
        content = "This is a research report about Arbitrum and its ecosystem." * 10
        result = _infer_metadata_from_content(content)
        assert result["language"] == "en"

    def test_mixed_language_detection(self):
        # Need >5% but <=30% Chinese chars
        content = "Arbitrum project overview. 项目概述 end." * 5
        result = _infer_metadata_from_content(content)
        assert result["language"] == "mixed"

    def test_date_extraction(self):
        content = "Report date: 2024-01-15\nSome analysis content."
        result = _infer_metadata_from_content(content)
        assert result["date"] == "2024-01-15"

    def test_author_extraction(self):
        content = "Some intro.\nAnalyst: John Smith\nMore content."
        result = _infer_metadata_from_content(content)
        assert result["author"] == "John Smith"

    def test_no_metadata_found(self):
        content = "Just some plain text without any metadata patterns."
        result = _infer_metadata_from_content(content)
        assert "date" not in result
        assert "author" not in result


class TestReplaceImages:
    def test_markdown_image(self):
        content = "Before ![arch diagram](images/arch.png) after"
        result = _replace_images(content)
        assert "[图片不可用: arch diagram]" in result
        assert "![" not in result

    def test_html_img_with_alt(self):
        content = 'Before <img src="photo.jpg" alt="team photo" /> after'
        result = _replace_images(content)
        assert "[图片不可用: team photo]" in result
        assert "<img" not in result

    def test_preserves_normal_content(self):
        content = "No images here, just text."
        result = _replace_images(content)
        assert result == content

    def test_multiple_images(self):
        content = "![a](1.png) text ![b](2.png)"
        result = _replace_images(content)
        assert "[图片不可用: a]" in result
        assert "[图片不可用: b]" in result


class TestExtractSectionTitle:
    def test_heading_in_chunk(self):
        text = "## 技术分析\n\nSome analysis content."
        result = _extract_section_title(text, text, 0)
        assert result == "技术分析"

    def test_heading_before_chunk(self):
        full_content = (
            "## 项目概述\n\nIntro content.\n\n"
            "## 技术分析\n\nAnalysis here.\n\nMore text about the technology."
        )
        # Chunk starts after "技术分析" section
        chunk_start = full_content.index("More text")
        chunk_text = "More text about the technology."
        result = _extract_section_title(chunk_text, full_content, chunk_start)
        assert result == "技术分析"

    def test_no_heading(self):
        text = "Just plain text without any headings."
        result = _extract_section_title(text, text, 0)
        assert result == ""


class TestChunkDocument:
    def test_produces_chunks(self):
        content = (
            "## Section A\n\n" + "Content A. " * 50
            + "\n\n## Section B\n\n" + "Content B. " * 50
        )
        metadata = {"project_name": "Test", "language": "en"}
        with patch("src.rag.ingest.settings") as mock_settings:
            mock_settings.chunk_size = 200
            chunks = _chunk_document(content, metadata, "test.md")
        assert len(chunks) > 1

    def test_metadata_preserved(self):
        content = "## Heading\n\n" + "Some content. " * 30
        metadata = {"project_name": "Arbitrum", "language": "zh"}
        with patch("src.rag.ingest.settings") as mock_settings:
            mock_settings.chunk_size = 200
            chunks = _chunk_document(content, metadata, "arb.md")
        for chunk in chunks:
            assert chunk.metadata["project_name"] == "Arbitrum"
            assert chunk.metadata["source"] == "arb.md"
            assert "chunk_index" in chunk.metadata

    def test_chunk_indices_sequential(self):
        content = "## H\n\n" + "Word. " * 100
        metadata = {"project_name": "Test"}
        with patch("src.rag.ingest.settings") as mock_settings:
            mock_settings.chunk_size = 100
            chunks = _chunk_document(content, metadata, "t.md")
        indices = [c.metadata["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))


class TestIngestSingleReport:
    @pytest.mark.asyncio
    async def test_successful_ingest(self, sample_markdown_file):
        mock_embedder = MagicMock()
        mock_embedder.embed_documents.return_value = [[0.1] * 10] * 20

        mock_store = MagicMock()
        mock_store.get_collection_stats.return_value = {"document_count": 10}

        with patch("src.rag.ingest.BGEEmbeddings", return_value=mock_embedder), \
             patch("src.rag.ingest.VectorStore", return_value=mock_store):
            count = await ingest_single_report(str(sample_markdown_file))

        assert count > 0
        mock_embedder.embed_documents.assert_called_once()
        mock_store.add_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_not_found(self):
        count = await ingest_single_report("/nonexistent/path/report.md")
        assert count == 0

    @pytest.mark.asyncio
    async def test_yaml_metadata_priority(self, tmp_path):
        """YAML front matter should override filename-inferred metadata."""
        content = '---\nproject_name: CustomName\n---\n\n# Report\n\nContent here. ' * 5
        file_path = tmp_path / "different_name_report.md"
        file_path.write_text(content, encoding="utf-8")

        mock_embedder = MagicMock()
        mock_embedder.embed_documents.return_value = [[0.1] * 10] * 5

        mock_store = MagicMock()
        mock_store.get_collection_stats.return_value = {"document_count": 5}

        with patch("src.rag.ingest.BGEEmbeddings", return_value=mock_embedder), \
             patch("src.rag.ingest.VectorStore", return_value=mock_store):
            await ingest_single_report(str(file_path))

        # Check that chunks have YAML-specified project_name
        call_args = mock_store.add_documents.call_args
        chunks = call_args[0][0]
        for chunk in chunks:
            assert chunk.metadata["project_name"] == "CustomName"
