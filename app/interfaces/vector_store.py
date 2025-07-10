from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models.analysis import IndexingResult

class VectorStore(ABC):
    """Abstract interface for vector storage operations"""
    
    @abstractmethod
    async def store_embeddings(self, embeddings: List[float], metadata: Dict[str, Any], 
                             content: str, file_path: str, code_type: str) -> Any:
        """Store embeddings with metadata"""
        pass
    
    @abstractmethod
    async def search_similar(self, query_embedding: List[float], 
                           limit: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar embeddings"""
        pass
    
    @abstractmethod
    async def search_by_content(self, query: str, file_paths: List[str]) -> Dict[str, Any]:
        """Search for content references"""
        pass

class EmbeddingService(ABC):
    """Abstract interface for embedding generation"""
    
    @abstractmethod
    async def get_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        pass
    
    @abstractmethod
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch"""
        pass