import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import logging

class Settings(BaseSettings):
    """Configuration settings for RAG service"""
    
    # Azure OpenAI
    azure_openai_api_key: str = Field(..., description="Azure OpenAI API key")
    azure_openai_endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    azure_openai_api_version: str = Field(default="2024-02-15-preview", description="Azure OpenAI API version")
    azure_openai_deployment_name: str = Field(..., description="Azure OpenAI deployment name")
    azure_openai_embeddings_deployment: str = Field(..., description="Azure OpenAI embeddings deployment name")
    
    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase API key")
    
    # RAG Configuration
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Similarity threshold for RAG")
    max_similarity_results: int = Field(default=15, ge=1, le=100, description="Maximum similarity results")
    embedding_batch_size: int = Field(default=15, ge=1, le=50, description="Embedding batch size")
    
    # Cache Configuration
    cache_ttl_embeddings: int = Field(default=3600, ge=60, description="Cache TTL for embeddings in seconds")
    cache_ttl_analysis: int = Field(default=1800, ge=60, description="Cache TTL for analysis in seconds")
    cache_max_size: int = Field(default=1000, ge=10, description="Maximum cache size")
    
    # Performance
    max_file_size_kb: int = Field(default=100, ge=1, description="Maximum file size in KB")
    max_content_tokens: int = Field(default=6000, ge=100, description="Maximum content tokens")
    
    # Error Handling
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, ge=0.1, description="Retry delay in seconds")
    circuit_breaker_threshold: int = Field(default=5, ge=1, description="Circuit breaker failure threshold")
    circuit_breaker_timeout: float = Field(default=60.0, ge=1.0, description="Circuit breaker timeout in seconds")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    
    # Feature Flags
    enable_ado_integration: bool = Field(default=False, description="Enable Azure DevOps integration")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_request_logging: bool = Field(default=True, description="Enable request logging")
    
    @validator('azure_openai_endpoint')
    def validate_endpoint_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Azure OpenAI endpoint must be a valid URL')
        return v
    
    @validator('supabase_url')
    def validate_supabase_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Supabase URL must be a valid URL')
        return v
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=self.log_format
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
settings.setup_logging()