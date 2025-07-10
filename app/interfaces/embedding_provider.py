from abc import ABC, abstractmethod
from typing import List, Dict, Any

class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers"""
    
    @abstractmethod
    async def get_embeddings(self, text: str) -> List[float]:
        """Get embeddings for a single text"""
        pass
    
    @abstractmethod
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts"""
        pass

class VectorStore(ABC):
    """Abstract interface for vector storage"""
    
    @abstractmethod
    async def store_embeddings(self, embeddings: List[float], metadata: Dict[str, Any]) -> str:
        """Store embeddings and return ID"""
        pass
    
    @abstractmethod
    async def search_similar(self, query_embedding: List[float], limit: int, threshold: float) -> List[Dict]:
        """Search for similar embeddings"""
        pass

class DependencyAnalyzer(ABC):
    """Abstract interface for dependency analysis strategies"""
    
    @abstractmethod
    async def analyze_dependencies(self, code_changes: List[Dict]) -> Dict[str, Any]:
        """Analyze dependencies for code changes"""
        pass