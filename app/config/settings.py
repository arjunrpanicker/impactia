import os
from typing import Optional
from pydantic import BaseSettings

class RAGSettings(BaseSettings):
    """Configuration settings for RAG service"""
    
    # Azure OpenAI
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    azure_openai_deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    azure_openai_embeddings_deployment: str = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME", "")
    
    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY", "")
    
    # RAG Configuration
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
    max_similarity_results: int = int(os.getenv("MAX_SIMILARITY_RESULTS", "15"))
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "15"))
    
    # Cache Configuration
    cache_ttl_embeddings: int = int(os.getenv("CACHE_TTL_EMBEDDINGS", "3600"))
    cache_ttl_analysis: int = int(os.getenv("CACHE_TTL_ANALYSIS", "1800"))
    cache_max_size: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))
    
    # Performance
    max_file_size_kb: int = int(os.getenv("MAX_FILE_SIZE_KB", "100"))
    max_content_tokens: int = int(os.getenv("MAX_CONTENT_TOKENS", "6000"))
    
    # Error Handling
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_delay: float = float(os.getenv("RETRY_DELAY", "1.0"))
    circuit_breaker_threshold: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    circuit_breaker_timeout: float = float(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60.0"))
    
    class Config:
        env_file = ".env"

# Global settings instance
settings = RAGSettings()