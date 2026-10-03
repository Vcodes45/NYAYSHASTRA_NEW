"""
LLM-based Query Router and Document Evaluator
Uses Ollama to intelligently route queries and evaluate document relevance
"""

import logging
from typing import Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)


class LLMRouter:
    """Uses LLM for intelligent query routing and document evaluation."""
    
    DOMAIN_MAP = {
        "criminal": "Criminal Law (IPC, CrPC, murder, theft, assault, etc.)",
        "traffic": "Traffic Law (Motor Vehicles Act, traffic violations, licensing, etc.)",
        "civil_family": "Civil & Family Law (contracts, marriage, divorce, property disputes, etc.)",
        "corporate": "Corporate Law (Companies Act, directors, shareholders, corporate governance, etc.)",
        "it_cyber": "IT & Cyber Law (cybercrime, hacking, data protection, digital signatures, etc.)",
        "property": "Property Law (real estate, land transactions, mortgages, inheritance, etc.)",
        "constitutional": "Constitutional Law (fundamental rights, writs, judicial review, amendments, etc.)",
        "environment": "Environmental Law (pollution, forest protection, wildlife, environmental clearances, etc.)"
    }
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
    
    async def detect_domain(self, query: str) -> Tuple[str, float]:
        """
        Use LLM to detect which legal domain the query belongs to.
        
        Returns:
            Tuple of (domain_name, confidence_score)
        """
        domain_list = "\n".join([f"- {k}: {v}" for k, v in self.DOMAIN_MAP.items()])
        
        prompt = f"""Analyze this legal query and determine which Indian law domain it belongs to.

Query: "{query}"

Available domains:
{domain_list}

Respond with ONLY the domain key (e.g., "criminal", "traffic", "corporate"). Choose the most relevant one."""

        try:
            response = await self.llm_service.generate(prompt, max_tokens=50)
            detected = response.strip().lower()
            
            # Extract domain key from response
            for domain_key in self.DOMAIN_MAP.keys():
                if domain_key in detected:
                    logger.info(f"[LLM_ROUTER] Detected domain: {domain_key}")
                    return domain_key, 0.9
            
            # Default to criminal if uncertain
            logger.warning(f"[LLM_ROUTER] Could not parse domain from: {response}, defaulting to criminal")
            return "criminal", 0.5
            
        except Exception as e:
            logger.error(f"[LLM_ROUTER] Domain detection failed: {e}")
            return "criminal", 0.3
    
    async def evaluate_documents(self, query: str, documents: List[Dict], domain: str, top_k: int = 3) -> List[Dict]:
        """
        Use LLM to evaluate and rank documents by relevance to the query.
        
        Args:
            query: User's legal query
            documents: List of retrieved documents
            domain: Expected legal domain
            top_k: Number of top documents to return
            
        Returns:
            List of top_k most relevant documents
        """
        if not documents:
            return []
        
        if len(documents) <= top_k:
            return documents
        
        # Create document summaries for LLM evaluation
        doc_summaries = []
        for i, doc in enumerate(documents[:10], 1):  # Evaluate max 10 docs
            content = doc.get("content", "")[:300]  # First 300 chars
            filename = doc.get("filename", f"Document {i}")
            doc_summaries.append(f"{i}. {filename}: {content}...")
        
        summaries_text = "\n\n".join(doc_summaries)
        
        prompt = f"""You are evaluating legal documents for relevance to a query in {domain} law.

Query: "{query}"

Documents:
{summaries_text}

Rank the top {top_k} most relevant documents by number (e.g., "1, 5, 3").
Respond with ONLY the numbers separated by commas."""

        try:
            response = await self.llm_service.generate(prompt, max_tokens=50)
            
            # Parse ranking
            rankings = []
            for char in response:
                if char.isdigit():
                    num = int(char)
                    if 1 <= num <= len(documents):
                        rankings.append(num - 1)  # Convert to 0-indexed
            
            if not rankings:
                logger.warning(f"[LLM_ROUTER] Could not parse rankings from: {response}")
                return documents[:top_k]
            
            # Return documents in ranked order
            ranked_docs = [documents[i] for i in rankings[:top_k] if i < len(documents)]
            logger.info(f"[LLM_ROUTER] Ranked documents: {rankings[:top_k]}")
            
            return ranked_docs if ranked_docs else documents[:top_k]
            
        except Exception as e:
            logger.error(f"[LLM_ROUTER] Document evaluation failed: {e}")
            return documents[:top_k]
    
    async def verify_domain_match(self, query: str, specified_domain: str) -> Tuple[bool, str]:
        """
        Verify if the query actually belongs to the specified domain.
        
        Returns:
            Tuple of (is_match, suggested_domain)
        """
        domain_desc = self.DOMAIN_MAP.get(specified_domain, specified_domain)
        
        prompt = f"""Does this legal query belong to {domain_desc}?

Query: "{query}"

Answer with ONLY "yes" or "no"."""

        try:
            response = await self.llm_service.generate(prompt, max_tokens=10)
            is_match = "yes" in response.lower()
            
            if not is_match:
                # Detect correct domain
                suggested_domain, _ = await self.detect_domain(query)
                if suggested_domain == specified_domain:
                    return True, specified_domain
                logger.info(f"[LLM_ROUTER] Domain mismatch - query is {suggested_domain}, not {specified_domain}")
                return False, suggested_domain
            
            return True, specified_domain
            
        except Exception as e:
            logger.error(f"[LLM_ROUTER] Domain verification failed: {e}")
            return True, specified_domain  # Assume match on error
