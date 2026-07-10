"""
MedAI Assistant - Retriever
Fetches and extracts clean text content from web search result URLs.
Uses httpx for async HTTP and BeautifulSoup for HTML parsing.
"""
import logging
import re
from typing import List, Optional
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Maximum characters to extract per page
MAX_CONTENT_LENGTH = 3000
# Maximum pages to fetch concurrently
MAX_CONCURRENT_FETCHES = 5


@dataclass
class RetrievedDocument:
    """A document retrieved and extracted from a web source."""
    title: str
    url: str
    content: str  # Cleaned extracted text
    source: str  # "google_cse" | "pubmed"
    domain: str
    snippet: str = ""  # Original search snippet
    credibility_score: float = 0.0
    relevance_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "source": self.source,
            "domain": self.domain,
            "snippet": self.snippet,
            "credibility_score": self.credibility_score,
            "relevance_score": self.relevance_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RetrievedDocument":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Retriever:
    """
    Fetches full-text content from search result URLs and extracts
    relevant medical text using BeautifulSoup.
    """

    # Tags that typically contain main content
    CONTENT_TAGS = ["article", "main", "section", ".content", "#content"]

    # Tags/classes to strip (navigation, ads, footers, etc.)
    STRIP_SELECTORS = [
        "nav", "header", "footer", "aside", "script", "style", "noscript",
        "iframe", ".sidebar", ".advertisement", ".ad", ".nav", ".menu",
        ".footer", ".header", ".cookie", ".popup", ".modal", ".social",
        "#sidebar", "#nav", "#menu", "#footer", "#header", "#cookie-banner",
        "[role='navigation']", "[role='banner']", "[role='contentinfo']",
    ]

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(12.0, connect=5.0),
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
            )
        return self._http_client

    async def retrieve(
        self, search_results: list, max_fetch: int = MAX_CONCURRENT_FETCHES
    ) -> List[RetrievedDocument]:
        """
        Retrieve and extract content from search result URLs.

        Args:
            search_results: List of SearchResult objects from search_service.
            max_fetch: Maximum number of URLs to fetch.

        Returns:
            List of RetrievedDocument objects with extracted content.
        """
        documents = []
        results_to_fetch = search_results[:max_fetch]

        for result in results_to_fetch:
            try:
                content = await self._fetch_and_extract(result.url)
                if content and len(content.strip()) > 50:
                    documents.append(RetrievedDocument(
                        title=result.title,
                        url=result.url,
                        content=content,
                        source=result.source,
                        domain=result.domain,
                        snippet=result.snippet,
                        relevance_score=result.relevance_score,
                    ))
                    logger.debug(f"Extracted {len(content)} chars from {result.url}")
                else:
                    # Fall back to snippet if full content extraction fails
                    if result.snippet:
                        documents.append(RetrievedDocument(
                            title=result.title,
                            url=result.url,
                            content=result.snippet,
                            source=result.source,
                            domain=result.domain,
                            snippet=result.snippet,
                            relevance_score=result.relevance_score,
                        ))
            except Exception as e:
                logger.warning(f"Failed to retrieve {result.url}: {e}")
                # Use snippet as fallback
                if result.snippet:
                    documents.append(RetrievedDocument(
                        title=result.title,
                        url=result.url,
                        content=result.snippet,
                        source=result.source,
                        domain=result.domain,
                        snippet=result.snippet,
                        relevance_score=result.relevance_score,
                    ))

        logger.info(f"Retrieved {len(documents)} documents from {len(results_to_fetch)} URLs")
        return documents

    async def _fetch_and_extract(self, url: str) -> Optional[str]:
        """
        Fetch a URL and extract clean text content.

        Returns:
            Cleaned text content or None if extraction fails.
        """
        client = await self._get_client()

        try:
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                logger.debug(f"Skipping non-HTML content: {content_type} at {url}")
                return None

            html = response.text
            return self._clean_html(html)

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP {e.response.status_code} for {url}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
            return None

    def _clean_html(self, html: str) -> str:
        """
        Parse HTML and extract clean, readable text content.
        Strips navigation, ads, scripts, and formatting.
        """
        soup = BeautifulSoup(html, "lxml")

        # Remove unwanted elements
        for selector in self.STRIP_SELECTORS:
            try:
                for element in soup.select(selector):
                    element.decompose()
            except Exception:
                continue

        # Try to find the main content area
        content_element = None
        for tag in ["article", "main", "[role='main']"]:
            try:
                content_element = soup.select_one(tag)
                if content_element:
                    break
            except Exception:
                continue

        # Fall back to body
        if not content_element:
            content_element = soup.find("body")

        if not content_element:
            return ""

        # Extract text
        text = content_element.get_text(separator="\n", strip=True)

        # Clean up the text
        text = self._normalize_text(text)

        # Truncate to maximum length
        if len(text) > MAX_CONTENT_LENGTH:
            # Try to cut at a sentence boundary
            truncated = text[:MAX_CONTENT_LENGTH]
            last_period = truncated.rfind(".")
            if last_period > MAX_CONTENT_LENGTH * 0.7:
                text = truncated[:last_period + 1]
            else:
                text = truncated + "..."

        return text

    def _normalize_text(self, text: str) -> str:
        """Normalize extracted text: remove excess whitespace, empty lines, etc."""
        # Collapse multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Collapse multiple spaces
        text = re.sub(r'[ \t]+', ' ', text)
        # Remove lines that are just whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        # Remove very short lines that are likely artifacts (< 10 chars)
        lines = [line for line in lines if len(line) >= 10 or line.endswith('.')]
        return '\n'.join(lines)

    async def close(self):
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()


# Singleton instance
retriever = Retriever()
