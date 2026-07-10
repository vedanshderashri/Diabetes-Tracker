"""
MedAI Assistant - Reranker Service
Implements a lightweight reranker combining lexical TF-IDF matching and semantic overlap.
Verifies structural alignment and ranks chunks before context assembly.
"""
import logging
import math
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class Reranker:
    """
    Reranks document chunks based on a combined score of:
    1. Lexical matching (query term frequency overlap)
    2. Semantic distance (if vector distances are available)
    """

    def __init__(self):
        # English stop words to filter out before lexical term matching
        self.stopwords = {
            "a", "about", "an", "and", "are", "as", "at", "be", "by", "can", "do",
            "for", "from", "have", "how", "i", "if", "in", "is", "it", "of", "on",
            "or", "please", "should", "tell", "the", "this", "to", "was", "what",
            "when", "where", "who", "will", "with", "you", "your",
        }

    def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        vector_distances: Optional[List[float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Reranks a list of documents/chunks against a query.

        Args:
            query: The user query string.
            documents: List of dicts, each containing 'document' or 'content' key.
            vector_distances: Optional list of raw cosine distances matching the documents.

        Returns:
            Sorted list of documents with updated score metadata.
        """
        if not documents:
            return []

        # Tokenize query
        query_terms = self._tokenize(query)
        if not query_terms:
            return documents

        scored_docs = []
        for idx, doc in enumerate(documents):
            text = doc.get("document", doc.get("content", ""))
            
            # Calculate Lexical Score (Overlap & TF)
            lexical_score = self._calculate_lexical_score(query_terms, text)
            
            # Calculate Semantic Score
            # If distance is provided, semantic_similarity = 1 - distance (assuming cosine space 0..2)
            semantic_score = 0.5
            if vector_distances and idx < len(vector_distances):
                dist = vector_distances[idx]
                semantic_score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
            elif "distance" in doc:
                dist = doc["distance"]
                semantic_score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))

            # Combined score: 40% Lexical + 60% Semantic
            combined_score = (lexical_score * 0.4) + (semantic_score * 0.6)
            
            # Attach score metadata
            doc_copy = doc.copy()
            doc_copy["rerank_score"] = round(combined_score, 4)
            doc_copy["lexical_score"] = round(lexical_score, 4)
            doc_copy["semantic_score"] = round(semantic_score, 4)
            
            scored_docs.append(doc_copy)

        # Sort documents by combined score descending
        scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        logger.info(f"Reranked {len(documents)} docs. Top score: {scored_docs[0]['rerank_score']}")
        return scored_docs

    def _tokenize(self, text: str) -> List[str]:
        """Normalize, tokenize, and clean stopwords from text."""
        text = text.lower()
        # Keep alphanumeric words and hyphens
        words = re.findall(r"\b[a-z0-9-]+\b", text)
        return [w for w in words if w not in self.stopwords]

    def _calculate_lexical_score(self, query_terms: List[str], document_text: str) -> float:
        """Calculate word frequency overlap and Jaccard-like index for the query against a document."""
        if not document_text:
            return 0.0
            
        doc_text_lower = document_text.lower()
        doc_words = self._tokenize(doc_text_lower)
        if not doc_words:
            return 0.0
            
        doc_word_set = set(doc_words)
        
        # Jaccard overlap count
        matching_terms = [term for term in query_terms if term in doc_word_set]
        if not matching_terms:
            return 0.0
            
        overlap_ratio = len(matching_terms) / len(query_terms)
        
        # Term Frequency weight (bonus for multiple matches of same term)
        tf_bonus = 0.0
        for term in matching_terms:
            count = doc_words.count(term)
            # Logarithmic scaling for term frequencies
            tf_bonus += math.log1p(count)
            
        # Normalize TF bonus by document length
        normalized_tf = min(1.0, tf_bonus / (math.log1p(len(doc_words)) + 1e-5))
        
        # Combined lexical: 60% overlap + 40% normalized term frequency
        return (overlap_ratio * 0.6) + (normalized_tf * 0.4)


# Singleton instance
reranker = Reranker()
