import os
from typing import List, Dict, Any
from supabase import create_client, Client
from ..interfaces.embedding_provider import VectorStore
from ..utils.error_handling import handle_errors, VectorSearchError

class SupabaseVectorStore(VectorStore):
    """Supabase implementation of vector store interface"""
    
    def __init__(self, url: str = None, key: str = None):
        self.supabase: Client = create_client(
            url or os.getenv("SUPABASE_URL", ""),
            key or os.getenv("SUPABASE_KEY", "")
        )
    
    @handle_errors(VectorSearchError)
    async def store_embeddings(self, embeddings: List[float], metadata: Dict[str, Any]) -> str:
        """Store embeddings and return ID"""
        try:
            result = self.supabase.table("code_embeddings").insert({
                "embedding": embeddings,
                "metadata": metadata,
                "content": metadata.get("content", ""),
                "file_path": metadata.get("file_path", ""),
                "code_type": metadata.get("code_type", "file"),
                "repository": metadata.get("repository", "main"),
                "content_hash": metadata.get("content_hash")
            }).execute()
            
            return str(result.data[0]["id"])
            
        except Exception as e:
            raise VectorSearchError(f"Failed to store embeddings: {str(e)}")
    
    @handle_errors(VectorSearchError)
    async def search_similar(self, query_embedding: List[float], limit: int, threshold: float) -> List[Dict]:
        """Search for similar embeddings"""
        try:
            result = self.supabase.rpc(
                "match_code_embeddings",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": limit
                }
            ).execute()
            
            return result.data or []
            
        except Exception as e:
            raise VectorSearchError(f"Failed to search similar embeddings: {str(e)}")