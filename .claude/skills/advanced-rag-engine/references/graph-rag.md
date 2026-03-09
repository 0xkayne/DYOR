# Graph RAG — 知识图谱增强检索

## 概述

Graph RAG 从文档中抽取实体和关系构建知识图谱，检索时沿图谱边发现关联文档，
解决 naive RAG "只检索直接相关文档、忽略间接关联" 的问题。

## NetworkX 实现

```python
import json
import networkx as nx
import structlog
from pathlib import Path

logger = structlog.get_logger()


class GraphRAG:
    """基于 NetworkX 的知识图谱增强检索。"""
    
    # 节点类型
    NODE_TYPES = {"Project", "Track", "Investor", "Person", "Protocol"}
    
    # 关系类型
    EDGE_TYPES = {
        "competes_with",    # 竞争关系
        "invested_by",      # 投资关系
        "built_on",         # 构建在某链上
        "ecosystem_of",     # 属于某生态
        "team_member_of",   # 团队成员
        "forked_from",      # Fork 关系
        "partners_with",    # 合作关系
    }
    
    def __init__(self, graph_path: str = "data/knowledge_graph/graph.json"):
        self.graph_path = Path(graph_path)
        self.graph = nx.DiGraph()
        if self.graph_path.exists():
            self.load_graph()
    
    async def build_graph(self, chunks: list, llm) -> None:
        """从文档 chunks 中抽取实体和关系，构建知识图谱。"""
        for chunk in chunks:
            triples = await self._extract_triples(chunk.page_content, llm)
            for subj, rel, obj in triples:
                # 添加节点
                self.graph.add_node(subj, type=self._infer_type(subj))
                self.graph.add_node(obj, type=self._infer_type(obj))
                # 添加边
                self.graph.add_edge(subj, obj, relation=rel)
                logger.debug("Added triple", subj=subj, rel=rel, obj=obj)
        
        self.save_graph()
        logger.info("Graph built", nodes=self.graph.number_of_nodes(),
                    edges=self.graph.number_of_edges())
    
    async def find_related(self, query: str, existing_results: list,
                           max_hops: int = 2, max_results: int = 5) -> list:
        """从已检索文档中的实体出发，沿图谱发现关联项目的文档。
        
        Args:
            query: 用户查询
            existing_results: 已检索到的文档列表
            max_hops: 最大图遍历跳数
            max_results: 最多返回的关联文档数
        
        Returns:
            关联项目的 Document 列表
        """
        if self.graph.number_of_nodes() == 0:
            return []
        
        # 从已有结果中提取项目名
        project_names = set()
        for doc in existing_results:
            name = doc.metadata.get("project_name", "")
            if name and name in self.graph:
                project_names.add(name)
        
        if not project_names:
            return []
        
        # BFS 遍历找邻居
        related_entities = set()
        for name in project_names:
            neighbors = self._bfs_neighbors(name, max_hops)
            related_entities.update(neighbors)
        
        # 排除已经检索到的项目
        related_entities -= project_names
        
        logger.info("Graph found related entities",
                    source=project_names, related=related_entities)
        
        return list(related_entities)[:max_results]
    
    def _bfs_neighbors(self, start: str, max_hops: int) -> set:
        """BFS 遍历获取 N 跳内的邻居节点。"""
        visited = set()
        queue = [(start, 0)]
        
        while queue:
            node, depth = queue.pop(0)
            if depth > max_hops:
                continue
            if node in visited:
                continue
            visited.add(node)
            
            for neighbor in list(self.graph.successors(node)) + \
                           list(self.graph.predecessors(node)):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        
        visited.discard(start)
        return visited
    
    async def _extract_triples(self, text: str, llm) -> list[tuple]:
        """用 LLM 从文本中抽取 (subject, relation, object) 三元组。"""
        prompt = f"""从以下加密货币研究文本中抽取实体关系三元组。

实体类型: Project, Track/Sector, Investor, Person, Protocol
关系类型: competes_with, invested_by, built_on, ecosystem_of, team_member_of, forked_from, partners_with

文本: {text[:1500]}

输出 JSON 数组（每个元素是 [subject, relation, object]）:
[["Arbitrum", "competes_with", "Optimism"], ["Arbitrum", "built_on", "Ethereum"]]

只抽取明确表述的关系，不要推测。如果没有可抽取的关系，输出空数组 []。"""
        
        try:
            result = await llm.ainvoke(prompt)
            triples = json.loads(result.strip().strip("```json").strip("```"))
            return [tuple(t) for t in triples if len(t) == 3]
        except Exception as e:
            logger.warning("Triple extraction failed", error=str(e))
            return []
    
    def _infer_type(self, entity_name: str) -> str:
        """简单启发式推断实体类型。"""
        tracks = {"DeFi", "NFT", "GameFi", "Layer1", "Layer2", "Infrastructure"}
        if entity_name in tracks:
            return "Track"
        return "Project"  # 默认
    
    def save_graph(self) -> None:
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self.graph)
        self.graph_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    
    def load_graph(self) -> None:
        data = json.loads(self.graph_path.read_text())
        self.graph = nx.node_link_graph(data)
        logger.info("Graph loaded", nodes=self.graph.number_of_nodes(),
                    edges=self.graph.number_of_edges())
```
