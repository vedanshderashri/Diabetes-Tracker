"""
MedAI Assistant - Search Service
Web search orchestrator using Google Custom Search API and PubMed E-utilities.
Generates optimized medical search queries and targets trusted medical sources.
"""
import logging
import re
from typing import List, Optional
from dataclasses import dataclass, field
from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class SearchResult:
    """A single search result from any source."""
    title: str
    url: str
    snippet: str
    source: str  # "google_cse" | "pubmed"
    domain: str = ""
    relevance_score: float = 0.0


class SearchService:
    """
    Web search orchestrator for medical queries.

    Searches Google Custom Search (restricted to trusted medical sites)
    and PubMed simultaneously, then merges results.
    """

    # Trusted medical domains for site-restricted Google searches
    TRUSTED_SITES = [
        "pubmed.ncbi.nlm.nih.gov",
        "diabetes.org",
        "who.int",
        "nih.gov",
        "cdc.gov",
        "nhs.uk",
        "drugbank.com",
        "fda.gov",
        "ema.europa.eu",
        "clinicaltrials.gov",
        "scholar.google.com",
        "icmr.gov.in",
        "ncbi.nlm.nih.gov",
        "mayoclinic.org",
        "medscape.com",
        "uptodate.com",
        "cochranelibrary.com",
        "rxlist.com",
    ]

    # Keywords that indicate the query needs real-time information
    RECENCY_KEYWORDS = [
        "latest", "newest", "recent", "new", "updated", "current",
        "2024", "2025", "2026", "approved", "guidelines", "recommendation",
        "clinical trial", "phase 3", "phase iii", "fda approved",
        "ema approved", "just released", "breakthrough", "novel",
    ]

    # Medical query expansion terms
    MEDICAL_SYNONYMS = {
        "diabetes": "diabetes mellitus",
        "type 1": "type 1 diabetes T1DM",
        "type 2": "type 2 diabetes T2DM",
        "sugar": "blood glucose glycemia",
        "bp": "blood pressure hypertension",
        "heart": "cardiovascular cardiac",
        "kidney": "renal nephropathy",
        "eye": "retinopathy ophthalmology",
        "nerve": "neuropathy neurological",
        "insulin": "insulin therapy",
        "metformin": "metformin biguanide",
    }

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(15.0, connect=5.0),
                follow_redirects=True,
                headers={"User-Agent": "MedAI-Assistant/1.0 (Medical Research Bot)"},
            )
        return self._http_client

    async def search(self, query: str, max_results: int = 0) -> List[SearchResult]:
        """
        Search multiple trusted sources for medical information.

        Args:
            query: The user's question or search query.
            max_results: Maximum results to return (0 = use setting default).

        Returns:
            Combined, deduplicated list of SearchResults.
        """
        if max_results <= 0:
            max_results = settings.SEARCH_MAX_RESULTS

        medical_query = self._generate_medical_query(query)
        logger.info(f"Searching for: {medical_query}")

        results: List[SearchResult] = []

        # Search Google CSE (if configured)
        if settings.GOOGLE_CSE_API_KEY and settings.GOOGLE_CSE_ENGINE_ID:
            try:
                google_results = await self._search_google(medical_query, max_results)
                results.extend(google_results)
                logger.info(f"Google CSE returned {len(google_results)} results")
            except Exception as e:
                logger.warning(f"Google CSE search failed: {e}")

        # Search PubMed (always available, free)
        try:
            pubmed_results = await self._search_pubmed(medical_query, min(5, max_results))
            results.extend(pubmed_results)
            logger.info(f"PubMed returned {len(pubmed_results)} results")
        except Exception as e:
            logger.warning(f"PubMed search failed: {e}")

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        return unique_results[:max_results]

    def _generate_medical_query(self, user_question: str) -> str:
        """
        Transform a natural language question into an optimized medical search query.
        Removes conversational noise, punctuation, and common stopwords,
        then appends relevant medical terms.
        """
        query = user_question.strip()

        # Remove conversational preambles
        for prefix in [
            "can you tell me about", "what is", "what are", "tell me about",
            "explain", "how does", "how do", "i want to know about",
            "please tell me", "i have a question about", "do you know if",
            "do you know about", "what do you know about",
        ]:
            if query.lower().startswith(prefix):
                query = query[len(prefix):].strip()

        # Remove punctuation
        query = re.sub(r"[^\w\s-]", "", query)

        # Tokenize and filter stopwords
        stopwords = {
            "a", "about", "an", "and", "are", "as", "at", "be", "by", "can", "do",
            "for", "from", "have", "how", "i", "if", "in", "is", "it", "of", "on",
            "or", "please", "should", "tell", "the", "this", "to", "was", "what",
            "when", "where", "who", "will", "with", "you", "your", "latest", "recent",
            "new", "newest", "recommendation", "recommendations", "clinical",
        }
        
        words = query.split()
        keywords = [w for w in words if w.lower() not in stopwords]

        # Expand known medical abbreviations/synonyms
        query_lower = " ".join(keywords).lower()
        expansions = []
        for keyword, expansion in self.MEDICAL_SYNONYMS.items():
            if keyword in query_lower:
                for term in expansion.split():
                    if term.lower() not in query_lower:
                        expansions.append(term)

        # Add "diabetes" context if not present (since this is a diabetes chatbot)
        if "diabet" not in query_lower and "insulin" not in query_lower:
            expansions.append("diabetes")

        final_keywords = keywords + expansions[:3]
        final_query = " ".join(final_keywords)
        
        return final_query if final_query else query

    def _build_site_restricted_query(self, query: str) -> str:
        """Build a Google CSE query with site restrictions."""
        # Google CSE handles site restriction via the engine config,
        # but we can also add explicit site: operators for extra precision
        return query

    async def _search_google(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search using Google Custom Search Engine API."""
        client = await self._get_client()
        results = []
        search_query = self._build_site_restricted_query(query)

        # Google CSE returns max 10 results per request
        num = min(max_results, 10)

        params = {
            "key": settings.GOOGLE_CSE_API_KEY,
            "cx": settings.GOOGLE_CSE_ENGINE_ID,
            "q": search_query,
            "num": num,
            "safe": "active",
        }

        try:
            response = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                url = item.get("link", "")
                domain = self._extract_domain(url)
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("snippet", ""),
                    source="google_cse",
                    domain=domain,
                    relevance_score=0.8,  # Base score for Google results
                ))
        except httpx.HTTPStatusError as e:
            logger.error(f"Google CSE HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            raise
        except Exception as e:
            logger.error(f"Google CSE error: {e}")
            raise

        return results

    async def _search_pubmed(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Search PubMed using E-utilities (free, no API key required for basic use).
        Uses esearch + esummary pipeline.
        """
        client = await self._get_client()
        results = []

        # Step 1: Search for article IDs
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        }
        if settings.PUBMED_API_KEY:
            search_params["api_key"] = settings.PUBMED_API_KEY

        try:
            search_response = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params=search_params,
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return results

            # Step 2: Fetch summaries for found articles
            summary_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json",
            }
            if settings.PUBMED_API_KEY:
                summary_params["api_key"] = settings.PUBMED_API_KEY

            summary_response = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params=summary_params,
            )
            summary_response.raise_for_status()
            summary_data = summary_response.json()

            articles = summary_data.get("result", {})
            for pmid in id_list:
                article = articles.get(pmid, {})
                if not article or isinstance(article, str):
                    continue

                title = article.get("title", "")
                # Build snippet from available fields
                authors = article.get("authors", [])
                author_str = ", ".join(a.get("name", "") for a in authors[:3])
                journal = article.get("fulljournalname", article.get("source", ""))
                pubdate = article.get("pubdate", "")

                snippet = f"{author_str}. {journal}. {pubdate}"

                results.append(SearchResult(
                    title=title,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    snippet=snippet,
                    source="pubmed",
                    domain="pubmed.ncbi.nlm.nih.gov",
                    relevance_score=0.90,  # PubMed is highly credible
                ))
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            raise

        return results

    def _extract_domain(self, url: str) -> str:
        """Extract domain from a URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def has_recency_keywords(self, query: str) -> bool:
        """Check if query contains keywords indicating need for recent information."""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.RECENCY_KEYWORDS)

    async def close(self):
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


# Singleton instance
search_service = SearchService()
