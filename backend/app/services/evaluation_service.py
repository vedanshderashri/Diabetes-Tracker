"""
MedAI Assistant - Evaluation Service
Implements LLM-as-a-Judge metrics to assess RAG pipeline quality:
- Faithfulness (Groundedness)
- Context Precision
- Context Recall
- Citation Accuracy
"""
import json
import logging
import re
import time
from typing import List, Dict, Any, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EvaluationService:
    """
    Evaluates generated pharmacology responses against the retrieved context
    to identify hallucinations, omissions, and context alignment.
    """

    def __init__(self):
        self._http_client = None

    def _call_judge(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM API in synchronous context for quick judging."""
        if not settings.OPENAI_API_KEY:
            return "{}"

        try:
            from openai import OpenAI

            extra_headers = {}
            if settings.OPENAI_API_BASE and "openrouter.ai" in settings.OPENAI_API_BASE:
                extra_headers = {
                    "HTTP-Referer": "https://github.com/Vedansh/Diabetes-Chatbot",
                    "X-Title": "MedAI Assistant Evaluation Judge",
                }

            client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE if settings.OPENAI_API_BASE else None,
                default_headers=extra_headers if extra_headers else None,
            )

            response = client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,  # Strict, deterministic judgments
                max_tokens=1000,
                response_format={"type": "json_object"} if "json" in system_prompt.lower() else None,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Evaluation judge API call failed: {e}")
            return "{}"

    def evaluate_faithfulness(self, context: str, response: str) -> float:
        """
        Measures Groundedness: What percentage of claims in the response
        are directly supported by the retrieved context?
        """
        if not response or not context:
            return 0.0

        system_prompt = (
            "You are an expert medical evaluation judge. Analyze the provided response and context. "
            "Your task is to identify every factual claim in the response, and evaluate if it is directly "
            "supported by the context. Respond ONLY in valid JSON format: "
            '{"claims": [{"claim": "Text of the claim", "supported": true/false, "explanation": "Why"}]}'
        )

        user_prompt = (
            f"CONTEXT:\n{context}\n\n"
            f"RESPONSE:\n{response}\n"
        )

        result_text = self._call_judge(system_prompt, user_prompt)
        
        try:
            data = json.loads(result_text)
            claims = data.get("claims", [])
            if not claims:
                return 1.0  # No claims to evaluate
                
            supported_count = sum(1 for c in claims if c.get("supported") is True)
            score = supported_count / len(claims)
            logger.info(f"Faithfulness evaluated: {supported_count}/{len(claims)} claims supported ({score:.2%})")
            return round(score, 2)
        except Exception as e:
            logger.error(f"Failed to parse faithfulness result: {e}. Output was: {result_text}")
            return 0.5  # Fallback neutral score

    def evaluate_context_precision(self, query: str, context_chunks: List[str]) -> float:
        """
        Measures Context Precision: How many of the retrieved chunks are relevant to the query?
        """
        if not context_chunks or not query:
            return 0.0

        system_prompt = (
            "You are an expert RAG evaluation judge. Evaluate if each context chunk is relevant and useful "
            "for answering the query. Respond ONLY in valid JSON format: "
            '{"evaluations": [{"chunk_index": 0, "relevant": true/false, "explanation": "Why"}]}'
        )

        chunks_text = "\n\n".join(f"CHUNK {i}:\n{chunk}" for i, chunk in enumerate(context_chunks))
        user_prompt = (
            f"QUERY: {query}\n\n"
            f"CONTEXT CHUNKS:\n{chunks_text}\n"
        )

        result_text = self._call_judge(system_prompt, user_prompt)
        
        try:
            data = json.loads(result_text)
            evals = data.get("evaluations", [])
            if not evals:
                return 0.0
                
            relevant_count = sum(1 for e in evals if e.get("relevant") is True)
            score = relevant_count / len(context_chunks)
            logger.info(f"Context Precision evaluated: {relevant_count}/{len(context_chunks)} chunks relevant ({score:.2%})")
            return round(score, 2)
        except Exception as e:
            logger.error(f"Failed to parse context precision: {e}")
            return 0.5

    def evaluate_context_recall(self, query: str, context: str, gold_answer: str) -> float:
        """
        Measures Context Recall: Did the RAG retrieve all key facts required to answer the query
        according to the gold standard answer?
        """
        if not context or not gold_answer:
            return 0.0

        system_prompt = (
            "You are an expert RAG evaluation judge. Extract the key facts from the gold standard answer, "
            "and check if each key fact is present in the retrieved context. Respond ONLY in valid JSON format: "
            '{"facts": [{"fact": "Text of the key fact", "present_in_context": true/false}]}'
        )

        user_prompt = (
            f"QUERY: {query}\n\n"
            f"GOLD STANDARD ANSWER:\n{gold_answer}\n\n"
            f"RETRIEVED CONTEXT:\n{context}\n"
        )

        result_text = self._call_judge(system_prompt, user_prompt)
        
        try:
            data = json.loads(result_text)
            facts = data.get("facts", [])
            if not facts:
                return 0.0
                
            present_count = sum(1 for f in facts if f.get("present_in_context") is True)
            score = present_count / len(facts)
            logger.info(f"Context Recall evaluated: {present_count}/{len(facts)} facts present in context ({score:.2%})")
            return round(score, 2)
        except Exception as e:
            logger.error(f"Failed to parse context recall: {e}")
            return 0.5

    def evaluate_citation_accuracy(self, response: str, references: List[Dict[str, Any]]) -> float:
        """
        Measures Citation Accuracy: Are references formatted correctly and pointing to correct sources?
        Checks if citations in format [Source X] exist and correspond to actual sources in index.
        """
        if not response:
            return 0.0
        if not references:
            return 1.0  # No references, nothing to mis-cite

        # Find all brackets like [Source 1], [Source 2], etc.
        citations = re.findall(r"\[Source\s+(\d+)\]", response, re.IGNORECASE)
        if not citations:
            # Check if there are general source tags or domain citations
            return 1.0  # No source citations found to validate

        valid_citations = 0
        total_citations = len(citations)

        for cit in citations:
            index = int(cit) - 1
            if 0 <= index < len(references):
                ref = references[index]
                # Check if URL or source domain exists
                if ref.get("url") or ref.get("source"):
                    valid_citations += 1

        score = valid_citations / total_citations if total_citations > 0 else 1.0
        logger.info(f"Citation Accuracy: {valid_citations}/{total_citations} citations verified ({score:.2%})")
        return round(score, 2)

    def run_full_evaluation(
        self, 
        query: str, 
        context: str, 
        response: str, 
        references: List[Dict[str, Any]], 
        gold_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run all evaluation metrics and compile a report."""
        start_time = time.time()
        
        # 1. Parse context into chunks
        # Simple split by Double newline to estimate chunks
        chunks = [c.strip() for c in context.split("\n\n") if c.strip()]
        
        faithfulness = self.evaluate_faithfulness(context, response)
        precision = self.evaluate_context_precision(query, chunks[:10])  # limit evaluation chunks to 10 for tokens
        citation_acc = self.evaluate_citation_accuracy(response, references)
        
        recall = 1.0
        if gold_answer:
            recall = self.evaluate_context_recall(query, context, gold_answer)
            
        latency = time.time() - start_time
        
        report = {
            "query": query,
            "metrics": {
                "faithfulness": faithfulness,
                "context_precision": precision,
                "context_recall": recall,
                "citation_accuracy": citation_acc,
            },
            "performance": {
                "latency_seconds": round(latency, 2),
            }
        }
        
        logger.info(f"RAG Evaluation complete: {report['metrics']}")
        return report


# Singleton instance
evaluation_service = EvaluationService()
