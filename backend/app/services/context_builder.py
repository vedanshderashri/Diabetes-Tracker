"""
MedAI Assistant - Context Builder
Merges RAG context and web search results into a unified context for the LLM.
Determines when web search is needed and formats source citations.
"""
import logging
from typing import List, Optional
from dataclasses import dataclass, field

from app.services.retriever import RetrievedDocument

logger = logging.getLogger(__name__)

# RAG distance threshold — above this, results are considered low quality
RAG_QUALITY_THRESHOLD = 0.6

# Maximum total context length (characters) to avoid token overflow
MAX_CONTEXT_LENGTH = 8000


@dataclass
class ContextResult:
    """Combined context from RAG and web search."""
    rag_context: str = ""
    web_context: str = ""
    combined_context: str = ""
    evidence_summary: str = ""
    references: list = field(default_factory=list)  # list of dicts with title, url, source, credibility_score
    source_type: str = "rag_only"  # "rag_only" | "web_only" | "rag_and_web"
    rag_sources_count: int = 0
    web_sources_count: int = 0


class ContextBuilder:
    """
    Assembles unified context from RAG results and web search results
    for the LLM to generate evidence-based responses.
    """

    # Keywords indicating the query needs real-time / recent information
    RECENCY_KEYWORDS = [
        "latest", "newest", "recent", "new", "updated", "current",
        "2024", "2025", "2026", "approved", "guidelines", "recommendation",
        "clinical trial", "phase 3", "phase iii", "fda approved",
        "ema approved", "breakthrough", "novel", "emerging",
    ]

    # Keywords indicating the query is about specific drugs or treatments
    DRUG_KEYWORDS = [
        "drug", "medicine", "medication", "treatment", "therapy",
        "dosage", "dose", "side effect", "adverse", "contraindication",
        "interaction", "prescribed", "prescription", "generic",
        "tirzepatide", "semaglutide", "ozempic", "mounjaro",
        "trulicity", "jardiance", "farxiga", "invokana",
    ]

    def build_context(
        self,
        rag_results: List[dict],
        web_results: List[RetrievedDocument],
        user_query: str,
    ) -> ContextResult:
        """
        Build a unified context from RAG and web search results.

        Args:
            rag_results: Results from ChromaDB RAG engine.
            web_results: Filtered and ranked web search results.
            user_query: The original user question.

        Returns:
            ContextResult with combined context, evidence summary, and references.
        """
        context = ContextResult()

        # Build RAG context
        if rag_results:
            context.rag_context = self._format_rag_context(rag_results)
            context.rag_sources_count = len(rag_results)

        # Build web context
        if web_results:
            context.web_context = self._format_web_context(web_results)
            context.web_sources_count = len(web_results)
            context.references = self._format_references(web_results)
            context.evidence_summary = self._build_evidence_summary(web_results)

        # Determine source type
        if rag_results and web_results:
            context.source_type = "rag_and_web"
        elif web_results:
            context.source_type = "web_only"
        else:
            context.source_type = "rag_only"

        # Combine contexts
        context.combined_context = self._combine_contexts(
            context.rag_context, context.web_context, context.source_type
        )

        return context

    def needs_web_search(self, query: str, rag_results: List[dict]) -> bool:
        """
        Determine if web search is needed based on query analysis and RAG quality.

        Returns True if:
        - RAG results are empty
        - RAG results have high distance scores (low relevance)
        - Query contains recency/currency keywords
        - Query mentions specific drugs or clinical trials
        """
        query_lower = query.lower()

        # Always search if RAG returns nothing
        if not rag_results:
            logger.info("Web search needed: No RAG results")
            return True

        # Check RAG quality via distance scores
        distances = [r.get("distance", 1.0) for r in rag_results]
        avg_distance = sum(distances) / len(distances)
        best_distance = min(distances)

        if best_distance > RAG_QUALITY_THRESHOLD:
            logger.info(
                f"Web search needed: Best RAG distance {best_distance:.3f} "
                f"> threshold {RAG_QUALITY_THRESHOLD}"
            )
            return True

        # Check for recency keywords
        if any(kw in query_lower for kw in self.RECENCY_KEYWORDS):
            logger.info("Web search needed: Recency keywords detected")
            return True

        # Check for drug/treatment keywords (often need up-to-date info)
        if any(kw in query_lower for kw in self.DRUG_KEYWORDS):
            logger.info("Web search needed: Drug/treatment query detected")
            return True

        # Check if user is asking about guidelines or protocols
        guideline_keywords = [
            "guideline", "protocol", "standard of care", "first line",
            "second line", "algorithm", "consensus", "position statement",
        ]
        if any(kw in query_lower for kw in guideline_keywords):
            logger.info("Web search needed: Guidelines query detected")
            return True

        logger.info(
            f"Web search NOT needed: RAG quality sufficient "
            f"(best_distance={best_distance:.3f})"
        )
        return False

    def _format_rag_context(self, rag_results: List[dict]) -> str:
        """Format RAG results into a context string."""
        parts = []
        for i, result in enumerate(rag_results, 1):
            doc = result["document"]
            source = result.get("metadata", {}).get("source", "medical_knowledge")
            distance = result.get("distance", 0)
            parts.append(
                f"[Local Knowledge Source {i} ({source}, relevance: {1 - distance:.0%})]: {doc}"
            )
        return "\n\n".join(parts)

    def _format_web_context(self, web_results: List[RetrievedDocument]) -> str:
        """Format web search results into a context string."""
        parts = []
        for i, doc in enumerate(web_results, 1):
            credibility = f"{doc.credibility_score:.0%}" if doc.credibility_score else "N/A"
            parts.append(
                f"[Web Source {i} ({doc.domain}, credibility: {credibility})]:\n"
                f"Title: {doc.title}\n"
                f"Content: {doc.content[:1500]}\n"
                f"URL: {doc.url}"
            )
        context = "\n\n".join(parts)

        # Enforce max length
        if len(context) > MAX_CONTEXT_LENGTH:
            context = context[:MAX_CONTEXT_LENGTH] + "\n\n[Context truncated for length...]"

        return context

    def _combine_contexts(
        self, rag_context: str, web_context: str, source_type: str
    ) -> str:
        """Combine RAG and web contexts into a single string."""
        parts = []

        if rag_context:
            parts.append(
                "═══ LOCAL MEDICAL KNOWLEDGE BASE ═══\n"
                f"{rag_context}"
            )

        if web_context:
            parts.append(
                "═══ REAL-TIME WEB SEARCH RESULTS (from trusted medical sources) ═══\n"
                f"{web_context}"
            )

        if not parts:
            return "No specific medical context retrieved for this query."

        return "\n\n".join(parts)

    def _format_references(self, web_results: List[RetrievedDocument]) -> list:
        """Format web results into a list of reference dicts."""
        references = []
        for doc in web_results:
            references.append({
                "title": doc.title,
                "url": doc.url,
                "source": doc.domain,
                "credibility_score": round(doc.credibility_score, 2),
            })
        return references

    def _build_evidence_summary(self, web_results: List[RetrievedDocument]) -> str:
        """Build a brief evidence summary from web results."""
        if not web_results:
            return ""

        sources = set(doc.domain for doc in web_results)
        top_source = web_results[0].domain if web_results else "unknown"

        summary = (
            f"Evidence retrieved from {len(web_results)} trusted medical source(s) "
            f"including {', '.join(list(sources)[:3])}. "
            f"Highest credibility source: {top_source} "
            f"(credibility: {web_results[0].credibility_score:.0%})."
        )
        return summary


# Singleton instance
context_builder = ContextBuilder()
