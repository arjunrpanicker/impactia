import os
import asyncio
from typing import List, Dict, Any
from openai import AzureOpenAI
from ..interfaces.vector_store import EmbeddingService

class AzureEmbeddingService(EmbeddingService):
    """Azure OpenAI implementation of embedding service with batching and caching"""
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.embeddings_deployment = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME")
        self.cache = {}  # Simple in-memory cache
        self.max_batch_size = 16  # Azure OpenAI batch limit
    
    async def get_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for a single text with caching"""
        # Simple hash-based caching
        text_hash = hash(text)
        if text_hash in self.cache:
            return self.cache[text_hash]
        
        try:
            response = self.client.embeddings.create(
                model=self.embeddings_deployment,
                input=text
            )
            embeddings = response.data[0].embedding
            self.cache[text_hash] = embeddings
            return embeddings
        except Exception as e:
            raise Exception(f"Failed to generate embeddings: {str(e)}")
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in optimized batches"""
        if not texts:
            return []
        
        # Check cache first
        cached_results = {}
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            text_hash = hash(text)
            if text_hash in self.cache:
                cached_results[i] = self.cache[text_hash]
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Process uncached texts in batches
        all_embeddings = [None] * len(texts)
        
        # Fill cached results
        for i, embeddings in cached_results.items():
            all_embeddings[i] = embeddings
        
        # Process uncached texts
        for i in range(0, len(uncached_texts), self.max_batch_size):
            batch = uncached_texts[i:i + self.max_batch_size]
            batch_indices = uncached_indices[i:i + self.max_batch_size]
            
            try:
                response = self.client.embeddings.create(
                    model=self.embeddings_deployment,
                    input=batch
                )
                
                for j, embedding_data in enumerate(response.data):
                    embeddings = embedding_data.embedding
                    original_index = batch_indices[j]
                    all_embeddings[original_index] = embeddings
                    
                    # Cache the result
                    text_hash = hash(batch[j])
                    self.cache[text_hash] = embeddings
                    
            except Exception as e:
                # Fallback to individual processing for this batch
                for j, text in enumerate(batch):
                    try:
                        embeddings = await self.get_embeddings(text)
                        original_index = batch_indices[j]
                        all_embeddings[original_index] = embeddings
                    except Exception:
                        # Set empty embedding as fallback
                        all_embeddings[batch_indices[j]] = [0.0] * 1536
        
        return all_embeddings