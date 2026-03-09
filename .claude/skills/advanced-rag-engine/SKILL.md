---
name: advanced-rag-engine
description: >
  高级 RAG (Retrieval-Augmented Generation) 引擎开发技能。用于构建生产级 RAG 系统，
  包括文档处理 pipeline、语义切分、Embedding 选型、向量存储、Hybrid Search（向量+BM25）、
  Reranking、Agentic RAG（自适应检索循环）、Graph RAG（知识图谱增强）、Self-RAG（检索结果自验证）、
  以及 RAGAS 框架评估。当用户需要以下任务时触发此技能：构建 RAG 系统、实现文档索引、
  实现语义检索、做 hybrid search、添加 reranking、实现知识图谱增强检索、
  评估 RAG 系统质量、优化检索准确率。即使用户只是提到 "RAG"、"检索增强"、"文档问答"、
  "向量检索"、"embedding"、"知识库"、"reranking"、"hybrid search"、"graph rag"、
  "RAGAS"、"faithfulness" 等关键词，也应触发此技能。
  不适用于纯搜索引擎构建或不涉及 LLM 的文本检索任务。
---

# Advanced RAG Engine Skill

构建超越 naive RAG 的生产级检索增强生成系统。本技能涵盖从文档处理到评估的完整 RAG 工程实践。

## 核心理念

Naive RAG（加载文档 → 固定切分 → 向量检索 → 拼接上下文 → 生成回答）在 2025 年已经是基本功。
真正有竞争力的 RAG 系统需要在以下维度做到前沿：

1. **语义切分** — 按内容语义而非固定 token 数切分文档
2. **Hybrid Search** — 向量检索 + BM25 关键词检索融合
3. **Reranking** — 用 cross-encoder 对初检结果重排序
4. **Agentic RAG** — Agent 自主决定是否检索、如何检索、何时重试
5. **Graph RAG** — 知识图谱增强，发现跨文档的实体关联
6. **Self-RAG** — 检索结果自验证，不够就 reformulate 重试

---

## 文档处理 Pipeline

### 文档加载

```python
from langchain_community.document_loaders import (
    TextLoader,         # .txt, .md
    PyPDFLoader,        # .pdf
    UnstructuredMarkdownLoader,  # 复杂 .md
)

def load_document(file_path: str) -> list[Document]:
    ext = Path(file_path).suffix.lower()
    loader_map = {
        ".txt": TextLoader,
        ".md": TextLoader,  # 简单 md 用 TextLoader 即可
        ".pdf": PyPDFLoader,
    }
    loader = loader_map.get(ext, TextLoader)
    return loader(file_path).load()
```

### 语义切分（Semantic Chunking）

不要使用固定 token 大小切分。语义切分根据内容的语义边界来拆分文档。

```python
from langchain_experimental.text_splitter import SemanticChunker

chunker = SemanticChunker(
    embeddings=embedding_model,
    breakpoint_threshold_type="percentile",  # 推荐
    breakpoint_threshold_amount=95,          # 95th percentile
)
chunks = chunker.split_documents(documents)
```

如果 SemanticChunker 不可用或太慢，退化方案：
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Markdown 文档可以先按标题切分
md_splitter = RecursiveCharacterTextSplitter.from_language(
    language="markdown",
    chunk_size=1000,
    chunk_overlap=200,
)
```

### Metadata 增强

每个 chunk 必须携带结构化 metadata，用于后续的 metadata filtering。

```python
REQUIRED_METADATA = {
    "source": "原始文件名",
    "project_name": "从内容提取的项目名",
    "report_date": "报告日期 (ISO8601)",
    "dimension": "team | product | track | tokenomics | valuation | risks | overview",
    "language": "zh | en",
    "chunk_index": 0,  # 在原文中的顺序
}
```

用 LLM 自动提取 metadata：
```python
async def enrich_metadata(chunk: Document, llm) -> Document:
    prompt = f"""从以下文本中提取信息，输出 JSON:
    {{"project_name": "项目名", "dimension": "team|product|track|tokenomics|valuation|risks|overview"}}
    
    文本: {chunk.page_content[:500]}"""
    result = await llm.ainvoke(prompt)
    chunk.metadata.update(parse_json(result))
    return chunk
```

---

## Embedding 模型

### 推荐: BGE-M3

BGE-M3 同时输出 dense、sparse、ColBERT 三种表示，天然适合 hybrid search。

```python
from FlagEmbedding import BGEM3FlagModel

model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
output = model.encode(["查询文本"], return_dense=True, return_sparse=True)
# output["dense_vecs"]: 1024维 dense embedding
# output["lexical_weights"]: 稀疏词权重（可替代 BM25）
```

### 轻量方案
如果资源受限（无 GPU / 内存不足），使用：
- `BAAI/bge-small-zh-v1.5` — 中文，512维，仅 dense
- `sentence-transformers/all-MiniLM-L6-v2` — 英文，384维

详见 `references/embedding-models.md` 获取完整的模型对比表。

---

## 向量存储

### ChromaDB（推荐用于本地开发）

```python
import chromadb

client = chromadb.PersistentClient(path="./data/chroma_db")
collection = client.get_or_create_collection(
    name="crypto_reports",
    metadata={"hnsw:space": "cosine"},
)

# 添加文档
collection.add(
    ids=[chunk.metadata["id"] for chunk in chunks],
    documents=[chunk.page_content for chunk in chunks],
    embeddings=[embed(chunk.page_content) for chunk in chunks],
    metadatas=[chunk.metadata for chunk in chunks],
)

# 检索（支持 metadata filter）
results = collection.query(
    query_embeddings=[embed(query)],
    n_results=10,
    where={"project_name": "Arbitrum"},  # metadata 过滤
)
```

---

## 检索策略

### Hybrid Search（必须实现）

单独用 dense retrieval 会丢失关键词匹配的优势，单独用 BM25 又没有语义理解能力。
Hybrid Search 结合两者，用 Reciprocal Rank Fusion 融合排名。

```python
from rank_bm25 import BM25Okapi
import jieba  # 中文分词

class HybridRetriever:
    def __init__(self, vectorstore, documents):
        self.vectorstore = vectorstore
        # BM25 需要预先建索引
        tokenized = [list(jieba.cut(doc.page_content)) for doc in documents]
        self.bm25 = BM25Okapi(tokenized)
        self.documents = documents
    
    def search(self, query: str, k: int = 10) -> list[Document]:
        # Dense retrieval
        dense_results = self.vectorstore.similarity_search(query, k=k)
        
        # Sparse retrieval (BM25)
        tokenized_query = list(jieba.cut(query))
        bm25_scores = self.bm25.get_scores(tokenized_query)
        top_indices = bm25_scores.argsort()[-k:][::-1]
        sparse_results = [self.documents[i] for i in top_indices]
        
        # Reciprocal Rank Fusion
        return self.reciprocal_rank_fusion(dense_results, sparse_results, k=60)
    
    @staticmethod
    def reciprocal_rank_fusion(list_a, list_b, k=60):
        scores = {}
        for rank, doc in enumerate(list_a):
            doc_id = doc.metadata.get("id", doc.page_content[:50])
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
        for rank, doc in enumerate(list_b):
            doc_id = doc.metadata.get("id", doc.page_content[:50])
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
        sorted_ids = sorted(scores, key=scores.get, reverse=True)
        # 返回去重后的 top 文档...
        return sorted_ids
```

### Reranking（必须实现）

初检 top-20 往往噪声很多。用 cross-encoder reranker 精排到 top-5。

```python
from flashrank import Ranker, RerankRequest

ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")

def rerank(query: str, candidates: list[Document], top_k: int = 5):
    rerank_req = RerankRequest(
        query=query,
        passages=[{"text": doc.page_content, "meta": doc.metadata} 
                  for doc in candidates],
    )
    results = ranker.rerank(rerank_req)
    return results[:top_k]
```

### Query Decomposition

对复杂问题拆解为子问题，分别检索后合并：

```python
DECOMPOSE_PROMPT = """将以下投资分析问题拆解为 2-4 个独立子问题，每个聚焦一个分析维度。
问题: {query}
输出 JSON 数组: ["子问题1", "子问题2", ...]"""
```

### Self-RAG（检索自验证）

检索后让 LLM 判断结果是否足够回答问题。不够就改写 query 重试。

```python
SUFFICIENCY_PROMPT = """判断以下检索结果是否足以回答用户问题。
问题: {query}
检索结果: {context}
输出 JSON:
{{"sufficient": true/false, "missing": "缺少什么信息", "reformulated_query": "改写后的查询"}}"""
```

最多重试 2 次，避免无限循环。

详见 `references/agentic-retrieval.md` 获取 Agentic RAG 的完整流程图和代码。

---

## Graph RAG（知识图谱增强）

从文档中抽取实体和关系，构建知识图谱。检索时沿图谱发现关联文档。

详见 `references/graph-rag.md` 获取 NetworkX 实现方案。

---

## 评估（RAGAS）

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

result = evaluate(
    dataset=eval_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision],
)
# 目标: faithfulness > 0.8, answer_relevancy > 0.7, context_precision > 0.7
```

---

## 禁止事项

- ❌ 不要用固定 512/1024 token chunk size（用语义切分）
- ❌ 不要只用 dense retrieval（必须 hybrid search）
- ❌ 不要跳过 reranking
- ❌ 不要丢弃 metadata
- ❌ 不要用同步 API 调用（全部 async）
- ❌ 不要在检索失败时静默返回空结果
- ❌ 中文文档不做分词就直接 BM25
