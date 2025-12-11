"""Cache manager for expensive pipeline operations."""

import logging
import hashlib
import json
from pathlib import Path
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import diskcache

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Centralized caching for expensive operations.
    
    Features:
    - Persistent disk-based cache using diskcache
    - LRU eviction policy
    - TTL (time-to-live) support
    - Namespace isolation
    - Cache statistics tracking
    """
    
    def __init__(self, cache_dir: Path = None, max_size_mb: int = 500):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache storage (default: .cache/nets)
            max_size_mb: Maximum cache size in megabytes
        """
        if cache_dir is None:
            cache_dir = Path(".cache/nets")
        
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize diskcache with size limit
        self.cache = diskcache.Cache(
            str(self.cache_dir),
            size_limit=max_size_mb * 1024 * 1024,  # Convert MB to bytes
            eviction_policy='least-recently-used'
        )
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0
        }
        
        logger.info(
            f"CacheManager initialized: dir={cache_dir}, "
            f"max_size={max_size_mb}MB"
        )
    
    def _make_key(self, key: str, namespace: str) -> str:
        """
        Create namespaced cache key.
        
        Args:
            key: Base key
            namespace: Namespace (e.g., 'network', 'pathway')
            
        Returns:
            Namespaced key
        """
        return f"{namespace}:{key}"
    
    def _hash_key(self, data: Any) -> str:
        """
        Generate hash key from data.
        
        Args:
            data: Data to hash (will be JSON serialized)
            
        Returns:
            SHA256 hash string
        """
        # Convert to JSON string for consistent hashing
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            Cached value or None if not found/expired
        """
        full_key = self._make_key(key, namespace)
        
        try:
            value = self.cache.get(full_key)
            
            if value is not None:
                self.stats['hits'] += 1
                logger.debug(f"Cache HIT: {namespace}:{key[:16]}...")
                return value
            else:
                self.stats['misses'] += 1
                logger.debug(f"Cache MISS: {namespace}:{key[:16]}...")
                return None
                
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.stats['misses'] += 1
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        ttl_hours: int = 24
    ):
        """
        Store value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            namespace: Cache namespace
            ttl_hours: Time-to-live in hours
        """
        full_key = self._make_key(key, namespace)
        
        try:
            # Calculate expiration time
            expire_time = ttl_hours * 3600  # Convert hours to seconds
            
            # Store in cache with expiration
            self.cache.set(full_key, value, expire=expire_time)
            
            self.stats['sets'] += 1
            logger.debug(
                f"Cache SET: {namespace}:{key[:16]}... "
                f"(TTL: {ttl_hours}h)"
            )
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    def invalidate(self, key: str, namespace: str = "default"):
        """
        Remove specific cache entry.
        
        Args:
            key: Cache key
            namespace: Cache namespace
        """
        full_key = self._make_key(key, namespace)
        
        try:
            self.cache.delete(full_key)
            logger.debug(f"Cache INVALIDATE: {namespace}:{key[:16]}...")
        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
    
    def clear_namespace(self, namespace: str):
        """
        Clear all entries in a namespace.
        
        Args:
            namespace: Namespace to clear
        """
        try:
            # Get all keys with this namespace prefix
            prefix = f"{namespace}:"
            keys_to_delete = [
                key for key in self.cache.iterkeys()
                if key.startswith(prefix)
            ]
            
            for key in keys_to_delete:
                self.cache.delete(key)
            
            logger.info(f"Cleared {len(keys_to_delete)} entries from namespace: {namespace}")
            
        except Exception as e:
            logger.error(f"Cache clear namespace error: {e}")
    
    def clear_all(self):
        """Clear entire cache."""
        try:
            self.cache.clear()
            logger.info("Cache cleared completely")
        except Exception as e:
            logger.error(f"Cache clear all error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (
            self.stats['hits'] / total_requests
            if total_requests > 0
            else 0.0
        )
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'size_bytes': self.cache.volume(),
            'size_mb': self.cache.volume() / (1024 * 1024),
            'entry_count': len(self.cache)
        }
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information.
        
        Returns:
            Dictionary with cache info and statistics
        """
        stats = self.get_stats()
        
        return {
            'cache_dir': str(self.cache_dir),
            'max_size_mb': self.cache.size_limit / (1024 * 1024),
            'eviction_policy': 'LRU',
            **stats
        }
    
    def close(self):
        """Close cache (cleanup)."""
        try:
            self.cache.close()
            logger.info("Cache closed")
        except Exception as e:
            logger.error(f"Cache close error: {e}")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    Get global cache manager instance (singleton).
    
    Returns:
        CacheManager instance
    """
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
    
    return _cache_manager
