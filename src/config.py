"""Global configuration module using pydantic-settings to manage environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"
    llm_model_sonnet: str = "claude-sonnet-4-20250514"
    llm_model_opus: str = "claude-opus-4-20250514"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    # RAG
    chroma_persist_dir: str = "./data/chroma_db"
    embedding_model: str = "BAAI/bge-m3"
    chunk_size: int = 512
    chunk_overlap: int = 50
    retriever_top_k: int = 5
    reranker_top_k: int = 3

    # MCP / External APIs
    coingecko_api_key: str = ""
    coingecko_pro_api_key: str = ""
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    cryptopanic_api_key: str = ""
    cryptopanic_base_url: str = "https://cryptopanic.com/api/developer/v2"

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Agent
    max_revision_count: int = 2
    agent_timeout: int = 30

    # Knowledge Graph
    knowledge_graph_path: str = "./data/knowledge_graph/graph.graphml"


settings = Settings()
