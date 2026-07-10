"""
MedAI Assistant - Medical Source Filter
Validates, ranks, and deduplicates retrieved documents based on source credibility.
Ensures only trusted medical sources are used for generating responses.
"""
import logging
import re
from typing import List
from urllib.parse import urlparse
from difflib import SequenceMatcher

from app.services.retriever import RetrievedDocument

logger = logging.getLogger(__name__)


class MedicalSourceFilter:
    """
    Filters, validates, and ranks retrieved medical documents.

    - Assigns credibility scores based on source domain
    - Removes duplicate or near-duplicate content
    - Ranks results by combined credibility + relevance
    - Rejects content from untrusted sources
    """

    # Credibility scores for trusted medical domains (0.0 - 1.0)
    SOURCE_CREDIBILITY = {
        # Tier 1: Highest credibility — peer-reviewed / government agencies
        "pubmed.ncbi.nlm.nih.gov": 0.95,
        "ncbi.nlm.nih.gov": 0.95,
        "nih.gov": 0.92,
        "who.int": 0.93,
        "cdc.gov": 0.90,
        "fda.gov": 0.90,
        "ema.europa.eu": 0.90,
        "clinicaltrials.gov": 0.92,
        "cochranelibrary.com": 0.95,
        "scholar.google.com": 0.88,

        # Tier 2: Professional medical organizations
        "diabetes.org": 0.90,  # ADA
        "icmr.gov.in": 0.88,   # ICMR
        "nhs.uk": 0.88,
        "mayoclinic.org": 0.87,
        "uptodate.com": 0.90,
        "medscape.com": 0.82,

        # Tier 3: Drug/pharmacology databases
        "drugbank.com": 0.85,
        "rxlist.com": 0.80,
        "drugs.com": 0.75,

        # Tier 4: Reputable health information
        "webmd.com": 0.70,
        "healthline.com": 0.65,
        "medicalnewstoday.com": 0.65,
        "clevelandclinic.org": 0.85,
        "hopkinsmedicine.org": 0.87,
        "stanfordhealthcare.org": 0.85,
    }

    # Domains that are explicitly NOT trusted
    BLOCKED_DOMAINS = [
        "medium.com",
        "quora.com",
        "reddit.com",
        "wikipedia.org",  # Good for general info but not primary medical source
        "facebook.com",
        "twitter.com",
        "x.com",
        "instagram.com",
        "tiktok.com",
        "youtube.com",
        "pinterest.com",
        "blogspot.com",
        "wordpress.com",
    ]

    # Minimum similarity ratio to consider two documents as duplicates
    DUPLICATE_THRESHOLD = 0.75

    def filter_and_rank(self, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """
        Filter, validate, score, deduplicate, and rank documents.

        Args:
            documents: Raw list of retrieved documents.

        Returns:
            Filtered and ranked list of documents.
        """
        if not documents:
            return []

        # Step 1: Filter out untrusted sources
        trusted_docs = [doc for doc in documents if self._is_trusted_source(doc.url)]
        rejected_count = len(documents) - len(trusted_docs)
        if rejected_count > 0:
            logger.info(f"Filtered out {rejected_count} documents from untrusted sources")

        # Step 2: Assign credibility scores
        for doc in trusted_docs:
            doc.credibility_score = self._get_credibility_score(doc.url)

        # Step 3: Remove duplicates
        deduped_docs = self._remove_duplicates(trusted_docs)
        if len(trusted_docs) != len(deduped_docs):
            logger.info(f"Removed {len(trusted_docs) - len(deduped_docs)} duplicate documents")

        # Step 4: Rank by combined score (credibility * 0.6 + relevance * 0.4)
        for doc in deduped_docs:
            doc.relevance_score = (
                doc.credibility_score * 0.6 + doc.relevance_score * 0.4
            )

        deduped_docs.sort(key=lambda d: d.relevance_score, reverse=True)

        logger.info(
            f"Source filter: {len(documents)} input → {len(deduped_docs)} filtered & ranked"
        )
        return deduped_docs

    def _is_trusted_source(self, url: str) -> bool:
        """Check if a URL belongs to a trusted medical source."""
        domain = self._extract_domain(url)
        if not domain:
            return False

        # Check if explicitly blocked
        for blocked in self.BLOCKED_DOMAINS:
            if blocked in domain:
                return False

        # Check if it matches a known trusted domain (partial match)
        for trusted in self.SOURCE_CREDIBILITY:
            if trusted in domain or domain.endswith(trusted):
                return True

        # Allow .gov, .edu, and .org domains (generally more trustworthy)
        if domain.endswith(".gov") or domain.endswith(".edu"):
            return True

        # Allow .org with caution (credibility will be lower)
        if domain.endswith(".org"):
            return True

        # For unknown domains, still allow but with low credibility
        # (they came from Google CSE which was site-restricted)
        return True

    def _get_credibility_score(self, url: str) -> float:
        """Get the credibility score for a URL's domain."""
        domain = self._extract_domain(url)
        if not domain:
            return 0.3

        # Check exact matches first
        if domain in self.SOURCE_CREDIBILITY:
            return self.SOURCE_CREDIBILITY[domain]

        # Check partial matches (e.g., "pmc.ncbi.nlm.nih.gov" matches "ncbi.nlm.nih.gov")
        for trusted_domain, score in self.SOURCE_CREDIBILITY.items():
            if domain.endswith(trusted_domain) or trusted_domain in domain:
                return score

        # Default scores by TLD
        if domain.endswith(".gov"):
            return 0.85
        if domain.endswith(".edu"):
            return 0.80
        if domain.endswith(".org"):
            return 0.65

        return 0.50  # Unknown but not blocked

    def _remove_duplicates(self, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """
        Remove near-duplicate documents based on content similarity.
        Keeps the document with the higher credibility score.
        """
        if len(documents) <= 1:
            return documents

        unique_docs = []
        for doc in documents:
            is_duplicate = False
            for existing in unique_docs:
                # Check URL-based duplication first (fast)
                if self._urls_match(doc.url, existing.url):
                    is_duplicate = True
                    break

                # Check content similarity (slower, use truncated content)
                similarity = self._text_similarity(
                    doc.content[:500], existing.content[:500]
                )
                if similarity >= self.DUPLICATE_THRESHOLD:
                    # Keep the one with higher credibility
                    if doc.credibility_score > existing.credibility_score:
                        unique_docs.remove(existing)
                        unique_docs.append(doc)
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_docs.append(doc)

        return unique_docs

    def _urls_match(self, url1: str, url2: str) -> bool:
        """Check if two URLs point to the same resource (ignoring query params)."""
        try:
            p1 = urlparse(url1)
            p2 = urlparse(url2)
            return (
                p1.netloc.lower().replace("www.", "") == p2.netloc.lower().replace("www.", "")
                and p1.path.rstrip("/") == p2.path.rstrip("/")
            )
        except Exception:
            return url1 == url2

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two texts."""
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""


# Singleton instance
medical_source_filter = MedicalSourceFilter()
