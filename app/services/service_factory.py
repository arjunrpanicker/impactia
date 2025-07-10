from typing import Dict, Any
from ..interfaces.embedding_provider import EmbeddingProvider, VectorStore, DependencyAnalyzer
from .azure_openai_service import AzureOpenAIService
from .supabase_vector_store import SupabaseVectorStore
from .cache_service import CacheService, MemoryCache
from .dependency_analyzers import CompositeDependencyAnalyzer, MethodCallAnalyzer, ImportAnalyzer, DataFlowAnalyzer
from .enhanced_rag_service import EnhancedRAGService
from ..config.settings import settings

class ServiceFactory:
    """Factory for creating service instances with proper dependency injection"""
    
    @staticmethod
    def create_embedding_provider() -> EmbeddingProvider:
        """Create embedding provider instance"""
        return AzureOpenAIService()
    
    @staticmethod
    def create_vector_store() -> VectorStore:
        """Create vector store instance"""
        return SupabaseVectorStore(
            url=settings.supabase_url,
            key=settings.supabase_key
        )
    
    @staticmethod
    def create_cache_service() -> CacheService:
        """Create cache service instance"""
        providers = {
            'memory': MemoryCache(
                max_size=settings.cache_max_size,
                default_ttl=settings.cache_ttl_embeddings
            )
        }
        return CacheService(providers)
    
    @staticmethod
    def create_dependency_analyzer() -> DependencyAnalyzer:
        """Create dependency analyzer instance"""
        analyzers = [
            MethodCallAnalyzer(),
            ImportAnalyzer(),
            DataFlowAnalyzer()
        ]
        return CompositeDependencyAnalyzer(analyzers)
    
    @staticmethod
    def create_rag_service() -> EnhancedRAGService:
        """Create fully configured RAG service"""
        return EnhancedRAGService(
            embedding_provider=ServiceFactory.create_embedding_provider(),
            vector_store=ServiceFactory.create_vector_store(),
            cache_service=ServiceFactory.create_cache_service(),
            dependency_analyzer=ServiceFactory.create_dependency_analyzer()
        )

# Singleton instances
_rag_service_instance = None

def get_rag_service() -> EnhancedRAGService:
    """Get singleton RAG service instance"""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = ServiceFactory.create_rag_service()
    return _rag_service_instance