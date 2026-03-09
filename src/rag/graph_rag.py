"""Knowledge graph enhanced retrieval using NetworkX for entity-relation discovery.

Extracts entity-relation triples from crypto research report chunks using structured
LLM output, builds an incremental knowledge graph, and provides graph-augmented
retrieval via BFS traversal to surface related projects and relationships.
"""

import json
from collections import defaultdict
from pathlib import Path

import networkx as nx
import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from pydantic import BaseModel, Field

from src.config import settings

logger = structlog.get_logger(__name__)

# Chinese → English relation normalization
RELATION_MAP: dict[str, str] = {
    "竞争关系": "competes_with",
    "竞争": "competes_with",
    "竞品": "competes_with",
    "合作关系": "partners_with",
    "合作": "partners_with",
    "投资": "invested_in",
    "投资了": "invested_in",
    "孵化": "incubated",
    "基于": "built_on",
    "构建于": "built_on",
    "部署在": "deployed_on",
    "分叉自": "forked_from",
    "fork自": "forked_from",
    "集成": "integrates",
    "集成了": "integrates",
    "使用": "uses",
    "依赖": "depends_on",
    "属于": "belongs_to",
    "收购": "acquired",
    "收购了": "acquired",
    "生态项目": "ecosystem_of",
    "Layer2": "l2_of",
    "L2": "l2_of",
}

# Generic relations to filter out (too vague to be useful)
GENERIC_RELATIONS: set[str] = {"相关", "有关系", "有关", "涉及", "关联", "related"}

EXTRACTION_PROMPT = """你是一个加密货币领域的知识图谱构建专家。请从以下文本中提取实体和关系三元组。

要求：
1. 实体应该是具体的项目名、协议名、公司名、人名或技术概念
2. 关系应该是具体的（如"竞争关系"、"投资了"、"基于"），不要使用模糊的"相关"
3. 每个三元组必须有明确的 subject、relation 和 object
4. subject_type 和 object_type 应为: project, protocol, company, person,
   technology, chain, token, concept
5. 优先提取项目间的竞争、合作、依赖、投资等关系

文本：
{text}

请提取所有有价值的三元组。如果文本中没有明确的实体关系，返回空列表。"""

MAX_TRIPLES_PER_REPORT = 50


class Triple(BaseModel):
    """A single entity-relation-entity triple extracted from text."""

    subject: str = Field(description="Source entity name")
    subject_type: str = Field(description="Type of the source entity")
    relation: str = Field(description="Relationship between entities")
    object: str = Field(description="Target entity name")
    object_type: str = Field(description="Type of the target entity")


class ExtractionResult(BaseModel):
    """Collection of triples extracted from a text chunk."""

    triples: list[Triple] = Field(default_factory=list, description="Extracted triples")


class GraphRAG:
    """Knowledge graph enhanced retrieval engine.

    Builds and maintains a directed knowledge graph from crypto research reports,
    extracts entity-relation triples via structured LLM output, and provides
    graph-augmented retrieval through BFS traversal.

    Args:
        graph_path: Path to the graph JSON persistence file.
    """

    def __init__(self, graph_path: str = "data/knowledge_graph/graph.json") -> None:
        self.graph_path = Path(graph_path)
        self.graph = nx.DiGraph()

        # Load entity aliases
        aliases_path = Path("data/knowledge_graph/aliases.json")
        if aliases_path.exists():
            with open(aliases_path) as f:
                self._aliases: dict[str, str] = json.load(f)
        else:
            self._aliases = {}
            logger.warning("aliases_file_not_found", path=str(aliases_path))

        # Build case-insensitive alias lookup
        self._alias_lookup: dict[str, str] = {
            k.lower(): v for k, v in self._aliases.items()
        }

        # Init LLM extractor with structured output
        llm = ChatAnthropic(
            model=settings.llm_model,
            temperature=0.0,
            max_tokens=2048,
        )
        self._extractor = llm.with_structured_output(ExtractionResult)

        self.load_graph()

    def _normalize_entity(self, name: str) -> str:
        """Normalize an entity name using aliases and existing graph nodes.

        Lookup order: alias table (case-insensitive) → existing graph nodes
        (case-insensitive) → return cleaned original.

        Args:
            name: Raw entity name from extraction.

        Returns:
            Normalized entity name.
        """
        cleaned = name.strip().strip('"').strip("'")
        if not cleaned:
            return cleaned

        # Check alias table
        lower = cleaned.lower()
        if lower in self._alias_lookup:
            return self._alias_lookup[lower]

        # Check existing graph nodes (case-insensitive match)
        for node in self.graph.nodes:
            if node.lower() == lower:
                return node

        return cleaned

    def _normalize_relation(self, relation: str) -> str:
        """Normalize a relation string to a canonical English form.

        Args:
            relation: Raw relation from extraction.

        Returns:
            Normalized relation string.
        """
        cleaned = relation.strip()
        if cleaned in RELATION_MAP:
            return RELATION_MAP[cleaned]
        return cleaned

    async def _extract_triples(self, text: str) -> list[Triple]:
        """Extract entity-relation triples from text via structured LLM output.

        Args:
            text: Source text chunk to extract from.

        Returns:
            List of extracted triples.
        """
        try:
            result = await self._extractor.ainvoke(
                EXTRACTION_PROMPT.format(text=text)
            )
            if result and result.triples:
                return result.triples
            return []
        except Exception:
            logger.exception("triple_extraction_failed")
            return []

    async def build_graph(self, chunks: list[Document]) -> None:
        """Incrementally build the knowledge graph from document chunks.

        Groups chunks by source document, extracts triples, filters for quality,
        normalizes entities/relations, and updates the graph. Enforces a per-report
        triple cap to prevent any single report from dominating.

        Args:
            chunks: List of LangChain Document objects with page_content and metadata.
        """
        # Group chunks by source
        source_groups: dict[str, list[Document]] = defaultdict(list)
        for chunk in chunks:
            source = chunk.metadata.get("source", "unknown")
            source_groups[source].append(chunk)

        total_added = 0

        for source, group_chunks in source_groups.items():
            report_triples = 0
            logger.info("processing_source", source=source, chunk_count=len(group_chunks))

            for chunk in group_chunks:
                if report_triples >= MAX_TRIPLES_PER_REPORT:
                    logger.info(
                        "triple_cap_reached",
                        source=source,
                        cap=MAX_TRIPLES_PER_REPORT,
                    )
                    break

                raw_triples = await self._extract_triples(chunk.page_content)

                for triple in raw_triples:
                    if report_triples >= MAX_TRIPLES_PER_REPORT:
                        break

                    # Quality filter: skip empty entities or generic relations
                    if not triple.subject.strip() or not triple.object.strip():
                        continue
                    if triple.relation.strip() in GENERIC_RELATIONS:
                        continue

                    subj = self._normalize_entity(triple.subject)
                    obj = self._normalize_entity(triple.object)
                    rel = self._normalize_relation(triple.relation)

                    if not subj or not obj or subj == obj:
                        continue

                    # Add/update nodes
                    if not self.graph.has_node(subj):
                        self.graph.add_node(subj, type=triple.subject_type)
                    if not self.graph.has_node(obj):
                        self.graph.add_node(obj, type=triple.object_type)

                    # Add/update edge with confidence weight and source tracking
                    edge_exists = (
                        self.graph.has_edge(subj, obj)
                        and self.graph[subj][obj].get("relation") == rel
                    )
                    if edge_exists:
                        self.graph[subj][obj]["weight"] += 1
                        sources = self.graph[subj][obj].get("source_docs", [])
                        if source not in sources:
                            sources.append(source)
                            self.graph[subj][obj]["source_docs"] = sources
                    else:
                        self.graph.add_edge(
                            subj,
                            obj,
                            relation=rel,
                            weight=1,
                            source_docs=[source],
                        )

                    report_triples += 1

            total_added += report_triples
            logger.info(
                "source_processed",
                source=source,
                triples_added=report_triples,
            )

        logger.info(
            "graph_build_complete",
            total_triples_added=total_added,
            total_nodes=self.graph.number_of_nodes(),
            total_edges=self.graph.number_of_edges(),
        )
        self.save_graph()

    async def find_related(
        self,
        query: str,
        existing_results: list[Document],
        max_hops: int = 2,
        max_results: int = 5,
    ) -> list[Document]:
        """Find related entities via BFS traversal on the knowledge graph.

        Identifies seed entities from existing retrieval results and query text,
        then traverses the graph in both directions to discover related projects.

        Args:
            query: User's search query.
            existing_results: Documents already retrieved by vector/hybrid search.
            max_hops: Maximum BFS traversal depth.
            max_results: Maximum number of related documents to return.

        Returns:
            List of synthetic Document objects with relational context.
        """
        if self.graph.number_of_nodes() == 0:
            return []

        # Collect seed entities from existing results metadata
        seed_entities: set[str] = set()
        for doc in existing_results:
            project = doc.metadata.get("project_name", "")
            if project:
                normalized = self._normalize_entity(project)
                if normalized and self.graph.has_node(normalized):
                    seed_entities.add(normalized)

        # Also check query for entity matches via substring
        query_lower = query.lower()
        for node in self.graph.nodes:
            if node.lower() in query_lower or query_lower in node.lower():
                seed_entities.add(node)

        if not seed_entities:
            return []

        logger.info("graph_search_seeds", seeds=list(seed_entities))

        # BFS on both forward and reverse graph
        reversed_graph = self.graph.reverse()
        discovered: dict[str, tuple[int, float]] = {}  # node → (hop_distance, max_confidence)

        for seed in seed_entities:
            for g in [self.graph, reversed_graph]:
                if not g.has_node(seed):
                    continue
                # BFS with depth tracking
                visited = {seed}
                frontier = [(seed, 0)]
                while frontier:
                    current, depth = frontier.pop(0)
                    if depth >= max_hops:
                        continue
                    for neighbor in g.neighbors(current):
                        if neighbor in visited or neighbor in seed_entities:
                            continue
                        visited.add(neighbor)
                        edge_data = g[current][neighbor]
                        weight = edge_data.get("weight", 1)
                        hop = depth + 1
                        if neighbor not in discovered:
                            discovered[neighbor] = (hop, weight)
                        else:
                            prev_hop, prev_weight = discovered[neighbor]
                            discovered[neighbor] = (
                                min(prev_hop, hop),
                                max(prev_weight, weight),
                            )
                        frontier.append((neighbor, hop))

        if not discovered:
            return []

        # Rank by hop distance (ascending) then confidence (descending)
        ranked = sorted(discovered.items(), key=lambda x: (x[1][0], -x[1][1]))

        results: list[Document] = []
        for entity, (hops, confidence) in ranked[:max_results]:
            # Build relational context description
            relations = []
            for seed in seed_entities:
                if self.graph.has_edge(seed, entity):
                    rel = self.graph[seed][entity].get("relation", "related_to")
                    relations.append(f"{seed} --[{rel}]--> {entity}")
                if self.graph.has_edge(entity, seed):
                    rel = self.graph[entity][seed].get("relation", "related_to")
                    relations.append(f"{entity} --[{rel}]--> {seed}")

            if self.graph.has_node(entity):
                node_type = self.graph.nodes[entity].get("type", "unknown")
            else:
                node_type = "unknown"
            context = (
                f"[Graph RAG] Entity: {entity} (type: {node_type})\n"
                f"Relationships: {'; '.join(relations) if relations else 'indirect connection'}\n"
                f"Graph distance: {hops} hop(s), confidence weight: {confidence}"
            )

            results.append(
                Document(
                    page_content=context,
                    metadata={
                        "source": "knowledge_graph",
                        "entity": entity,
                        "entity_type": node_type,
                        "hops": hops,
                        "confidence": confidence,
                    },
                )
            )

        logger.info("graph_search_results", count=len(results))
        return results

    def save_graph(self) -> None:
        """Persist the graph and aliases to disk as JSON."""
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)

        graph_data = nx.node_link_data(self.graph)
        with open(self.graph_path, "w") as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)

        # Also persist any new aliases learned during normalization
        aliases_path = self.graph_path.parent / "aliases.json"
        with open(aliases_path, "w") as f:
            json.dump(self._aliases, f, ensure_ascii=False, indent=2)

        logger.info(
            "graph_saved",
            path=str(self.graph_path),
            nodes=self.graph.number_of_nodes(),
            edges=self.graph.number_of_edges(),
        )

    def load_graph(self) -> None:
        """Load the graph from disk. Handles missing or corrupt files gracefully."""
        if not self.graph_path.exists():
            logger.info("no_existing_graph", path=str(self.graph_path))
            return

        try:
            with open(self.graph_path) as f:
                data = json.load(f)
            self.graph = nx.node_link_graph(data, directed=True)
            logger.info(
                "graph_loaded",
                path=str(self.graph_path),
                nodes=self.graph.number_of_nodes(),
                edges=self.graph.number_of_edges(),
            )
        except (json.JSONDecodeError, nx.NetworkXError, KeyError):
            logger.exception("graph_load_failed", path=str(self.graph_path))
            self.graph = nx.DiGraph()
