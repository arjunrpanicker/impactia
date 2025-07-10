import asyncio
import json
import time
from typing import Any, Dict, Optional, List
from abc import ABC, abstractmethod

class CacheProvider(ABC):
    """Abstract cache provider interface"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        pass

class MemoryCache(CacheProvider):
    """In-memory cache with TTL support"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if entry['expires_at'] and time.time() > entry['expires_at']:
                del self._cache[key]
                return None
            
            return entry['value']
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        async with self._lock:
            # Evict oldest entries if cache is full
            if len(self._cache) >= self._max_size:
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k]['created_at'])
                del self._cache[oldest_key]
            
            expires_at = None
            if ttl or self._default_ttl:
                expires_at = time.time() + (ttl or self._default_ttl)
            
            self._cache[key] = {
                'value': value,
                'created_at': time.time(),
                'expires_at': expires_at
            }
    
    async def delete(self, key: str) -> None:
        async with self._lock:
            self._cache.pop(key, None)

class CacheService:
    """Centralized cache service with multiple providers"""
    
    def __init__(self, providers: Dict[str, CacheProvider]):
        self.providers = providers
        self.default_provider = 'memory'
    
    async def get_embedding(self, text_hash: str) -> Optional[List[float]]:
        """Get cached embedding"""
        return await self.providers[self.default_provider].get(f"embedding:{text_hash}")
    
    async def set_embedding(self, text_hash: str, embedding: List[float], ttl: int = 3600) -> None:
        """Cache embedding"""
        await self.providers[self.default_provider].set(f"embedding:{text_hash}", embedding, ttl)
    
    async def get_analysis(self, prompt_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result"""
        return await self.providers[self.default_provider].get(f"analysis:{prompt_hash}")
    
    async def set_analysis(self, prompt_hash: str, analysis: Dict[str, Any], ttl: int = 1800) -> None:
        """Cache analysis result"""
        await self.providers[self.default_provider].set(f"analysis:{prompt_hash}", analysis, ttl)