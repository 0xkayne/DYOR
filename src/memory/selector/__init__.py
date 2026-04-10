"""Memory Selector package for intelligent context compression and recall.

Exports:
    ContextAssembler: Full context assembly pipeline
    Summarizer: Message history compression via LLM
    SimilarityRecall: ChromaDB-backed session similarity search
    AbstractMemorySelector: Abstract base class
"""

from src.memory.selector.context_assembler import ContextAssembler
from src.memory.selector.recall import SimilarityRecall
from src.memory.selector.summarizer import Summarizer

__all__ = [
    "AbstractMemorySelector",
    "ContextAssembler",
    "SimilarityRecall",
    "Summarizer",
]
