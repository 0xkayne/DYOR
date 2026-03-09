# Agentic RAG — 自适应检索完整实现

## 核心思想

传统 RAG 是一个固定 pipeline：query → retrieve → generate。
Agentic RAG 让 Agent 自主决定检索策略：是否需要检索？检索什么？结果够不够？要不要换个方式再检索？

## 完整流程图

```
用户查询
    │
    ▼
┌──────────────────┐
│ 1. Query Analysis │  → 判断：能直接回答？需要检索？需要拆分？
└──────────────────┘
    │
    ├─── 直接回答 ──────────────────────▶ 生成回答
    │
    ├─── 需要检索
    │       │
    │       ▼
    │  ┌──────────────────┐
    │  │ 2. Query Decomp  │  → 复杂问题拆为子问题
    │  └──────────────────┘
    │       │
    │       ▼
    │  ┌──────────────────┐
    │  │ 3. Hybrid Search │  → Dense + BM25 + RRF
    │  └──────────────────┘
    │       │
    │       ▼
    │  ┌──────────────────┐
    │  │ 4. Graph Enhance │  → 知识图谱补充关联文档
    │  └──────────────────┘
    │       │
    │       ▼
    │  ┌──────────────────┐
    │  │ 5. Reranking     │  → Cross-encoder 精排
    │  └──────────────────┘
    │       │
    │       ▼
    │  ┌──────────────────┐
    │  │ 6. Self-RAG Check│  → 结果够不够？
    │  └──────────────────┘
    │       │
    │       ├─── 足够 ─────────────────▶ 生成回答
    │       │
    │       └─── 不足够 (max 2次)
    │               │
    │               ▼
    │         Reformulate Query
    │               │
    │               └──────── 回到 Step 3
    │
    └─── 需要拆分 ── 回到 Step 2
```

## 完整代码实现

```python
import structlog
from dataclasses import dataclass

logger = structlog.get_logger()

@dataclass
class RetrievalResult:
    strategy: str           # "direct" | "agentic" | "fallback"
    documents: list         # 检索到的文档
    query_history: list     # 查询历史（含 reformulation）
    retry_count: int        # 重试次数


class AgenticRetriever:
    """自适应检索器：自主决定检索策略并验证结果充分性。"""
    
    MAX_RETRIES = 2
    
    def __init__(self, vectorstore, bm25_retriever, reranker, graph_rag, llm):
        self.vectorstore = vectorstore
        self.bm25 = bm25_retriever
        self.reranker = reranker
        self.graph_rag = graph_rag
        self.llm = llm
    
    async def retrieve(self, query: str) -> RetrievalResult:
        query_history = [query]
        
        # Step 1: Query Analysis
        analysis = await self._analyze_query(query)
        
        if analysis["action"] == "direct_answer":
            logger.info("Query can be answered directly", query=query)
            return RetrievalResult("direct", [], query_history, 0)
        
        # Step 2: Query Decomposition (if needed)
        if analysis["action"] == "decompose":
            sub_queries = await self._decompose_query(query)
        else:
            sub_queries = [query]
        
        # Retrieval loop with self-validation
        for retry in range(self.MAX_RETRIES + 1):
            # Step 3: Hybrid Search
            candidates = []
            for sq in sub_queries:
                dense = self.vectorstore.similarity_search(sq, k=10)
                sparse = self.bm25.search(sq, k=10)
                fused = self._reciprocal_rank_fusion(dense, sparse)
                candidates.extend(fused)
            
            # Step 4: Graph Enhancement
            graph_docs = await self.graph_rag.find_related(query, candidates)
            candidates.extend(graph_docs)
            
            # Deduplicate
            candidates = self._deduplicate(candidates)
            
            # Step 5: Reranking
            reranked = self.reranker.rerank(query, candidates, top_k=5)
            
            # Step 6: Self-RAG Check
            if retry < self.MAX_RETRIES:
                check = await self._check_sufficiency(query, reranked)
                if check["sufficient"]:
                    return RetrievalResult("agentic", reranked, query_history, retry)
                
                # Reformulate and retry
                new_query = check["reformulated_query"]
                logger.info("Reformulating query",
                           original=query, new=new_query, retry=retry+1)
                sub_queries = [new_query]
                query_history.append(new_query)
            else:
                # Max retries reached, return what we have
                return RetrievalResult("agentic", reranked, query_history, retry)
        
        return RetrievalResult("fallback", reranked, query_history, self.MAX_RETRIES)
    
    async def _analyze_query(self, query: str) -> dict:
        """判断查询类型：直接回答 / 需要检索 / 需要拆解"""
        prompt = f"""分析以下查询，判断应该如何处理：
        查询: {query}
        
        输出 JSON:
        {{"action": "direct_answer | retrieve | decompose",
         "reasoning": "一句话理由"}}
        
        - direct_answer: 问的是常识性问题，不需要检索特定文档
        - retrieve: 需要从知识库检索相关信息
        - decompose: 问题复杂，涉及多个维度，需要拆解后分别检索"""
        
        result = await self.llm.ainvoke(prompt)
        return self._parse_json(result)
    
    async def _decompose_query(self, query: str) -> list[str]:
        """将复杂问题拆解为 2-4 个子问题"""
        prompt = f"""将以下问题拆解为 2-4 个独立的子问题：
        问题: {query}
        输出 JSON 数组: ["子问题1", "子问题2", ...]"""
        
        result = await self.llm.ainvoke(prompt)
        return self._parse_json(result)
    
    async def _check_sufficiency(self, query: str, docs: list) -> dict:
        """验证检索结果是否足以回答问题"""
        context = "\n---\n".join([d.page_content[:300] for d in docs])
        prompt = f"""判断以下检索结果是否足以回答用户问题。
        问题: {query}
        检索结果摘要: {context}
        
        输出 JSON:
        {{"sufficient": true/false,
         "missing": "如果不足，说明缺少什么信息",
         "reformulated_query": "如果不足，给出改写后的检索查询"}}"""
        
        result = await self.llm.ainvoke(prompt)
        return self._parse_json(result)
    
    @staticmethod
    def _reciprocal_rank_fusion(list_a, list_b, k=60):
        """RRF 融合两个排序列表"""
        scores = {}
        all_docs = {}
        for rank, doc in enumerate(list_a):
            doc_id = id(doc)
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
            all_docs[doc_id] = doc
        for rank, doc in enumerate(list_b):
            doc_id = id(doc)
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
            all_docs[doc_id] = doc
        sorted_ids = sorted(scores, key=scores.get, reverse=True)
        return [all_docs[did] for did in sorted_ids]
    
    @staticmethod
    def _deduplicate(docs, threshold=0.95):
        """基于内容相似度去重"""
        seen = set()
        unique = []
        for doc in docs:
            key = doc.page_content[:100]  # 简单去重
            if key not in seen:
                seen.add(key)
                unique.append(doc)
        return unique
    
    @staticmethod
    def _parse_json(text: str) -> dict:
        """安全解析 LLM 输出的 JSON"""
        import json
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
```

## Citation Tracking

检索结果必须携带来源信息，供下游 Analyst 引用：

```python
# 在 RAG Agent 中组织返回格式
rag_result = {
    "retrieved_chunks": [
        {
            "content": chunk.page_content,
            "source": chunk.metadata["source"],
            "project_name": chunk.metadata["project_name"],
            "dimension": chunk.metadata["dimension"],
            "relevance_score": score,
        }
        for chunk, score in zip(reranked_docs, scores)
    ],
    "query_history": retrieval_result.query_history,
    "strategy_used": retrieval_result.strategy,
}
```
