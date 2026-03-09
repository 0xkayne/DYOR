# Embedding 模型选型参考

## 推荐模型对比

| 模型 | 维度 | 中文 | 英文 | Dense | Sparse | 大小 | 推荐场景 |
|------|------|------|------|-------|--------|------|----------|
| BAAI/bge-m3 | 1024 | ✅ | ✅ | ✅ | ✅ | ~2.3GB | 首选，支持 hybrid search |
| BAAI/bge-large-zh-v1.5 | 1024 | ✅ | ❌ | ✅ | ❌ | ~1.3GB | 纯中文场景 |
| BAAI/bge-small-zh-v1.5 | 512 | ✅ | ❌ | ✅ | ❌ | ~95MB | 资源受限 |
| all-MiniLM-L6-v2 | 384 | ❌ | ✅ | ✅ | ❌ | ~80MB | 纯英文轻量 |
| jina-embeddings-v3 | 1024 | ✅ | ✅ | ✅ | ❌ | ~570MB | API 方式使用 |

## BGE-M3 使用方式

```python
# 方式 1: FlagEmbedding (推荐，支持 dense + sparse)
from FlagEmbedding import BGEM3FlagModel
model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
output = model.encode(["text"], return_dense=True, return_sparse=True)

# 方式 2: sentence-transformers (仅 dense)
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-m3")
embeddings = model.encode(["text"])

# 方式 3: LangChain wrapper
from langchain_community.embeddings import HuggingFaceEmbeddings
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
```

## 选型决策树

```
需要中英文混合？
├── 是 → 有 GPU？
│       ├── 是 → BGE-M3 (首选)
│       └── 否 → BGE-M3 + use_fp16=True，或退化到 bge-small-zh
└── 否 → 纯中文？
        ├── 是 → bge-large-zh-v1.5 (有 GPU) / bge-small-zh-v1.5 (无 GPU)
        └── 否 → all-MiniLM-L6-v2
```
