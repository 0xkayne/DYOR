"""Document loading and chunking pipeline for ingesting research reports.

Handles markdown parsing, image caption replacement, YAML front matter extraction,
and intelligent chunking with metadata preservation.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

import structlog
import yaml
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import settings
from src.rag.embeddings import BGEEmbeddings
from src.rag.vectorstore import VectorStore

logger = structlog.get_logger(__name__)

# Markdown-aware separators for recursive splitting
_MARKDOWN_SEPARATORS = [
    "\n# ",       # H1
    "\n## ",      # H2
    "\n### ",     # H3
    "\n#### ",    # H4
    "\n\n",       # Paragraph break
    "\n",         # Line break
    " ",          # Word break
]

# Regex patterns
_YAML_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_IMAGE_MD_RE = re.compile(r"!\[([^\]]*)\]\([^\)]+\)")
_IMAGE_HTML_RE = re.compile(r'<img[^>]*alt=["\']([^"\']*)["\'][^>]*/?>|<img[^>]*/?>',re.IGNORECASE)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _extract_yaml_front_matter(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML front matter from markdown content.

    Args:
        content: Raw markdown content.

    Returns:
        Tuple of (metadata dict, content without front matter).
    """
    match = _YAML_FRONT_MATTER_RE.match(content)
    if match:
        try:
            metadata = yaml.safe_load(match.group(1)) or {}
            remaining = content[match.end():]
            return metadata, remaining
        except yaml.YAMLError as exc:
            logger.warning("yaml_parse_error", error=str(exc))
    return {}, content


def _infer_metadata_from_filename(filename: str) -> dict[str, str]:
    """Infer basic metadata from the filename.

    Args:
        filename: Name of the markdown file.

    Returns:
        Dictionary with inferred metadata fields.
    """
    stem = Path(filename).stem
    # Convert snake_case filename to project name
    parts = stem.replace("_research_report", "").replace("_report", "").split("_")
    project_name = " ".join(p.capitalize() for p in parts)
    return {"project_name": project_name}


def _infer_metadata_from_content(content: str) -> dict[str, Any]:
    """Infer metadata from document content.

    Args:
        content: Markdown content (without front matter).

    Returns:
        Dictionary with inferred metadata.
    """
    metadata: dict[str, Any] = {}

    # Try to extract date from content
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", content)
    if date_match:
        metadata["date"] = date_match.group(1)

    # Try to extract author
    author_match = re.search(r"[Aa]nalyst:\s*(.+?)[\n*]", content)
    if author_match:
        metadata["author"] = author_match.group(1).strip()

    # Detect language
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
    total_chars = len(content)
    if total_chars > 0:
        ratio = chinese_chars / total_chars
        if ratio > 0.3:
            metadata["language"] = "zh"
        elif ratio > 0.05:
            metadata["language"] = "mixed"
        else:
            metadata["language"] = "en"

    return metadata


def _replace_images(content: str) -> str:
    """Replace image references with unavailable placeholders.

    Since we cannot access local images or URLs at ingest time without
    a multimodal LLM configured, we insert placeholder captions.

    Args:
        content: Markdown content with image references.

    Returns:
        Content with images replaced by placeholder captions.
    """
    # Replace markdown images: ![alt](url)
    def _replace_md_image(match: re.Match[str]) -> str:
        alt_text = match.group(1) or "image"
        return f"[图片不可用: {alt_text}]"

    content = _IMAGE_MD_RE.sub(_replace_md_image, content)

    # Replace HTML img tags
    def _replace_html_image(match: re.Match[str]) -> str:
        alt_text = match.group(1) if match.group(1) else "image"
        return f"[图片不可用: {alt_text}]"

    content = _IMAGE_HTML_RE.sub(_replace_html_image, content)
    return content


def _extract_section_title(text: str, full_content: str, chunk_start: int) -> str:
    """Extract the nearest heading above a chunk position.

    Args:
        text: The chunk text.
        full_content: The full document content.
        chunk_start: Approximate start position of the chunk in the full content.

    Returns:
        The nearest section title or empty string.
    """
    # Look for headings within the chunk first
    headings = _HEADING_RE.findall(text)
    if headings:
        return headings[0][1].strip()

    # Look for the nearest heading before this chunk in the full content
    preceding = full_content[:chunk_start]
    headings = _HEADING_RE.findall(preceding)
    if headings:
        return headings[-1][1].strip()

    return ""


def _chunk_document(
    content: str,
    metadata: dict[str, Any],
    source: str,
) -> list[Document]:
    """Split document content into chunks with metadata.

    Uses RecursiveCharacterTextSplitter with markdown-aware separators.
    Chunk size: settings.chunk_size, overlap: 64 tokens (hardcoded override).

    Args:
        content: Preprocessed markdown content.
        metadata: Document-level metadata.
        source: Source filename.

    Returns:
        List of Document chunks with metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=64,  # Hardcoded override per spec
        separators=_MARKDOWN_SEPARATORS,
        keep_separator=True,
        is_separator_regex=False,
    )

    texts = splitter.split_text(content)
    documents: list[Document] = []

    # Track position for section title extraction
    search_start = 0
    for i, text in enumerate(texts):
        # Find approximate position of this chunk in original content
        pos = content.find(text[:50], search_start)
        if pos == -1:
            pos = search_start

        section_title = _extract_section_title(text, content, pos)

        chunk_metadata = {
            **metadata,
            "source": source,
            "chunk_index": i,
            "section_title": section_title,
        }

        documents.append(
            Document(
                page_content=text.strip(),
                metadata=chunk_metadata,
            )
        )
        search_start = pos + len(text[:50]) if pos >= 0 else search_start

    logger.info("document_chunked", source=source, chunks=len(documents))
    return documents


async def ingest_single_report(file_path: str) -> int:
    """Ingest a single markdown report into the vector store.

    Parses the document, extracts metadata, chunks the content,
    generates embeddings, and stores everything in ChromaDB.

    Args:
        file_path: Path to the markdown report file.

    Returns:
        Number of chunks created.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error("file_not_found", path=file_path)
        return 0

    logger.info("ingesting_report", file=path.name)

    # Read content
    content = path.read_text(encoding="utf-8")

    # Extract YAML front matter
    yaml_metadata, content = _extract_yaml_front_matter(content)

    # Infer metadata from filename and content
    filename_metadata = _infer_metadata_from_filename(path.name)
    content_metadata = _infer_metadata_from_content(content)

    # Merge metadata: YAML front matter takes priority
    metadata: dict[str, Any] = {
        "project_name": "",
        "track": "",
        "date": "",
        "author": "",
        "data_source": path.name,
        "keywords": "",
        "language": "en",
    }
    metadata.update(filename_metadata)
    metadata.update(content_metadata)
    metadata.update({k: v for k, v in yaml_metadata.items() if v is not None})

    # Convert list values to strings for ChromaDB
    for key, value in metadata.items():
        if isinstance(value, list):
            metadata[key] = ", ".join(str(v) for v in value)
        elif value is None:
            metadata[key] = ""

    # Replace images with placeholders
    content = _replace_images(content)

    # Chunk the document
    chunks = _chunk_document(content, metadata, path.name)

    if not chunks:
        logger.warning("no_chunks_created", file=path.name)
        return 0

    # Generate embeddings
    embedder = BGEEmbeddings()
    texts = [doc.page_content for doc in chunks]
    embeddings = embedder.embed_documents(texts)

    # Store in vector database
    store = VectorStore()
    store.add_documents(chunks, embeddings)

    stats = store.get_collection_stats()
    logger.info(
        "report_ingested",
        file=path.name,
        chunks=len(chunks),
        total_documents=stats["document_count"],
    )
    return len(chunks)


async def ingest_reports(report_dir: str = "data/reports") -> int:
    """Ingest all markdown reports from a directory.

    Args:
        report_dir: Directory containing markdown report files.

    Returns:
        Total number of chunks created across all files.
    """
    report_path = Path(report_dir)
    if not report_path.exists():
        logger.error("report_dir_not_found", path=report_dir)
        return 0

    md_files = list(report_path.glob("*.md"))
    if not md_files:
        logger.warning("no_markdown_files_found", path=report_dir)
        return 0

    logger.info("ingesting_reports", count=len(md_files), dir=report_dir)

    total_chunks = 0
    for md_file in md_files:
        chunks = await ingest_single_report(str(md_file))
        total_chunks += chunks

    logger.info("all_reports_ingested", total_chunks=total_chunks)
    return total_chunks


if __name__ == "__main__":
    async def main() -> None:
        """Run ingestion and test queries."""
        print("=" * 60)
        print("DYOR RAG Ingest Pipeline")
        print("=" * 60)

        # Clear existing data for clean run
        store = VectorStore()
        store.delete_collection()

        # Ingest reports
        total = await ingest_reports()
        print(f"\nIngested {total} chunks total.")

        # Run test queries
        test_queries = [
            "Arbitrum 的团队背景",
            "ARB 代币经济学",
            "Arbitrum 的竞争对手有哪些",
            "Optimistic Rollup 技术原理",
            "Arbitrum 的风险因素",
        ]

        embedder = BGEEmbeddings()
        store = VectorStore()

        print("\n" + "=" * 60)
        print("Test Queries")
        print("=" * 60)

        for query in test_queries:
            print(f"\nQuery: {query}")
            print("-" * 40)
            query_emb = embedder.embed_query(query)
            results = store.similarity_search(query_emb, k=3)
            for i, doc in enumerate(results):
                score = doc.metadata.get("score", 0.0)
                section = doc.metadata.get("section_title", "N/A")
                print(f"  [{i+1}] score={score:.4f} section='{section}'")
                print(f"      {doc.page_content[:120]}...")

    asyncio.run(main())
