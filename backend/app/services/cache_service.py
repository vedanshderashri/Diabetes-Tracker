"""
MedAI Assistant - Cache Service
In-memory TTL cache for web search results to avoid redundant queries.
Supports query-level caching and session-level context reuse for follow-ups.
"""
import hashlib
import logging
import re
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

from cachetools import TTLCache

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class CachedSearchResult:
    """Cached search result with metadata."""
    web_results: list  # list of RetrievedDocument dicts
    evidence_summary: str = ""
    references: list = field(default_factory=list)
    cached_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CacheService:
    """
    In-memory TTL cache for search results.

    - Query cache: keyed by normalized query hash, TTL configurable (default 30 min)
    - Session cache: keyed by session_id, stores recent search context for follow-ups
    """

    def __init__(self):
        ttl_seconds = settings.SEARCH_CACHE_TTL_MINUTES * 60
        # Query-level cache: up to 500 entries
        self._query_cache: TTLCache = TTLCache(maxsize=500, ttl=ttl_seconds)
        # Session-level cache: up to 200 sessions, same TTL
        self._session_cache: TTLCache = TTLCache(maxsize=200, ttl=ttl_seconds)
        logger.info(f"Cache service initialized (TTL={settings.SEARCH_CACHE_TTL_MINUTES}min)")

    def get(self, query: str) -> Optional[CachedSearchResult]:
        """Retrieve cached search results for a query."""
        key = self._normalize_query(query)
        result = self._query_cache.get(key)
        if result:
            logger.info(f"Cache HIT for query: {query[:60]}...")
        return result

    def set(self, query: str, result: CachedSearchResult) -> None:
        """Store search results in cache."""
        key = self._normalize_query(query)
        self._query_cache[key] = result
        logger.info(f"Cached search results for query: {query[:60]}...")

    def get_session_context(self, session_id: str) -> Optional[list]:
        """Retrieve cached web results for a conversation session (for follow-ups)."""
        return self._session_cache.get(session_id)

    def set_session_context(self, session_id: str, web_results: list) -> None:
        """Store web results for a conversation session."""
        self._session_cache[session_id] = web_results
        logger.debug(f"Cached session context for session: {session_id}")

    def _normalize_query(self, query: str) -> str:
        """
        Normalize a query into a cache key.
        Lowercases, strips punctuation, collapses whitespace, then hashes.
        This ensures similar queries hit the same cache entry.
        """
        normalized = query.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "query_cache_size": len(self._query_cache),
            "query_cache_maxsize": self._query_cache.maxsize,
            "session_cache_size": len(self._session_cache),
            "session_cache_maxsize": self._session_cache.maxsize,
            "ttl_minutes": settings.SEARCH_CACHE_TTL_MINUTES,
        }


# Singleton instance
cache_service = CacheService()
