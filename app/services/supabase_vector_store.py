import os
from typing import List, Dict, Any
from supabase import create_client, Client
from ..interfaces.vector_store import VectorStore

class SupabaseVectorStore(VectorStore):
    """Supabase implementation of vector store"""
    
    def __init__(self, url: str = None, key: str = None):
        self.supabase: Client = create_client(
            url or os.getenv("SUPABASE_URL", ""),
            key or os.getenv("SUPABASE_KEY", "")
        )
    
    async def store_embeddings(self, embeddings: List[float], metadata: Dict[str, Any], 
                             content: str, file_path: str, code_type: str) -> Any:
        """Store embeddings with metadata in Supabase"""
        try:
            data = {
                "embedding": embeddings,
                "metadata": metadata,
                "content": content,
                "file_path": file_path,
                "code_type": code_type,
                "repository": "main"  # TODO: Make this configurable
            }
            
            result = self.supabase.table("code_embeddings").insert(data).execute()
            return result
            
        except Exception as e:
            raise Exception(f"Failed to store embeddings for {file_path}: {str(e)}")
    
    async def search_similar(self, query_embedding: List[float], 
                           limit: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar embeddings using vector similarity"""
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
            raise Exception(f"Failed to search similar embeddings: {str(e)}")
    
    async def search_by_content(self, query: str, file_paths: List[str]) -> Dict[str, Any]:
        """Search for content references in the database"""
        try:
            # Use text search for direct references
            result = self.supabase.table("code_embeddings")\
                .select("*")\
                .text_search("content", query)\
                .execute()
            
            return {"data": result.data or []}
            
        except Exception as e:
            raise Exception(f"Failed to search content references: {str(e)}")