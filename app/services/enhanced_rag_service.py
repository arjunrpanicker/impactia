import os
import asyncio
from typing import Dict, Any, List
from ..interfaces.embedding_provider import EmbeddingProvider, VectorStore, DependencyAnalyzer
from .cache_service import CacheService, MemoryCache
from .dependency_analyzers import CompositeDependencyAnalyzer, MethodCallAnalyzer, ImportAnalyzer, DataFlowAnalyzer
from ..models.analysis import CodeChange

class EnhancedRAGService:
    """Enhanced RAG service with dependency injection and modular architecture"""
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        cache_service: CacheService,
        dependency_analyzer: DependencyAnalyzer
    ):
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.cache_service = cache_service
        self.dependency_analyzer = dependency_analyzer
        
        # Configuration
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
        self.max_results = int(os.getenv("MAX_SIMILARITY_RESULTS", "15"))
        self.batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "15"))
    
    async def get_related_code(self, changes: List[CodeChange]) -> Dict[str, Any]:
        """Get related code with enhanced analysis"""
        try:
            # Step 1: Prepare change data
            change_data = [
                {
                    'file_path': change.file_path,
                    'content': change.content or '',
                    'change_type': change.change_type
                }
                for change in changes
            ]
            
            # Step 2: Generate embeddings for changes
            combined_text = self._combine_changes_text(changes)
            change_embedding = await self._get_cached_embedding(combined_text)
            
            # Step 3: Search for similar code
            similar_code = await self.vector_store.search_similar(
                change_embedding, 
                limit=self.max_results, 
                threshold=self.similarity_threshold
            )
            
            # Step 4: Analyze dependencies
            dependencies = await self.dependency_analyzer.analyze_dependencies(change_data)
            
            # Step 5: Search for direct references
            reference_results = await self._search_references([change.file_path for change in changes])
            
            return {
                "changed_files": [change.file_path for change in changes],
                "direct_dependencies": {
                    "incoming": reference_results.get("incoming_refs", []),
                    "outgoing": reference_results.get("outgoing_refs", [])
                },
                "dependency_chains": reference_results.get("dependency_chains", []),
                "dependency_visualization": reference_results.get("dependency_visualization", []),
                "enhanced_dependencies": dependencies,
                "similar_code": self._format_similar_code(similar_code)
            }
            
        except Exception as e:
            raise Exception(f"Failed to get related code: {str(e)}")
    
    async def _get_cached_embedding(self, text: str) -> List[float]:
        """Get embedding with caching"""
        import hashlib
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        
        # Check cache first
        cached_embedding = await self.cache_service.get_embedding(text_hash)
        if cached_embedding:
            return cached_embedding
        
        # Generate new embedding
        embedding = await self.embedding_provider.get_embeddings(text)
        
        # Cache the result
        await self.cache_service.set_embedding(text_hash, embedding)
        
        return embedding
    
    def _combine_changes_text(self, changes: List[CodeChange]) -> str:
        """Combine changes into a single text for embedding"""
        combined = []
        for change in changes:
            text = f"File: {change.file_path}\n"
            if change.diff:
                text += f"Diff:\n{change.diff}\n"
            elif change.content:
                text += f"Content:\n{change.content}\n"
            combined.append(text)
        return "\n\n".join(combined)
    
    def _format_similar_code(self, similar_code: List[Dict]) -> Dict[str, Any]:
        """Format similar code results"""
        return {
            "files": [
                {
                    "path": item["metadata"].get("path", ""),
                    "content": item["content"],
                    "similarity": item["similarity"],
                    "methods": item["metadata"].get("methods", [])
                }
                for item in similar_code
                if item["metadata"].get("type") == "file"
            ],
            "methods": [
                {
                    "name": item["metadata"].get("name", ""),
                    "file_path": item["metadata"].get("path", ""),
                    "content": item["content"],
                    "similarity": item["similarity"]
                }
                for item in similar_code
                if item["metadata"].get("type") == "method"
            ]
        }
    
    async def _search_references(self, file_paths: List[str]) -> Dict[str, Any]:
        """Search for direct references - placeholder for now"""
        # This would be implemented based on the vector store interface
        return {
            "incoming_refs": [],
            "outgoing_refs": [],
            "dependency_chains": [],
            "dependency_visualization": []
        }

# Factory function for creating the enhanced service
def create_enhanced_rag_service() -> EnhancedRAGService:
    """Factory function to create enhanced RAG service with all dependencies"""
    from .azure_openai_service import AzureOpenAIService
    from .supabase_vector_store import SupabaseVectorStore
    
    # Create cache service
    cache_providers = {
        'memory': MemoryCache(max_size=1000, default_ttl=3600)
    }
    cache_service = CacheService(cache_providers)
    
    # Create dependency analyzer
    analyzers = [
        MethodCallAnalyzer(),
        ImportAnalyzer(),
        DataFlowAnalyzer()
    ]
    dependency_analyzer = CompositeDependencyAnalyzer(analyzers)
    
    # Create embedding provider
    embedding_provider = AzureOpenAIService()
    
    # Create vector store
    vector_store = SupabaseVectorStore()
    
    return EnhancedRAGService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        cache_service=cache_service,
        dependency_analyzer=dependency_analyzer
    )