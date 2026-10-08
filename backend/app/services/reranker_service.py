"""
NyayaShastra - Re-Ranking Service
Uses BGE-Reranker-v2-m3 for cross-encoder re-ranking
Acts as a "strict judge" to eliminate hallucination sources before they reach the LLM
"""

import logging
from typing import List, Dict, Any, Tuple
import numpy as np

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import CrossEncoder  # FlagEmbedding is incompatible with transformers>=5
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    logger.warning("Reranker not available. Install with: pip install sentence-transformers")


class RerankerService:
    """
    Cross-encoder re-ranking service using BGE-Reranker-v2-m3.
    Re-scores retrieved documents based on query-document relevance.
    """
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", use_fp16: bool = True):
        """
        Initialize reranker service.
        
        Args:
            model_name: Reranker model identifier
            use_fp16: Use half precision for faster inference
        """
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self.model = None
        self._initialized = False
        
    def initialize(self):
        """Lazy initialization of the reranker model."""
        if self._initialized:
            return
        
        if not RERANKER_AVAILABLE:
            logger.warning(
                "Reranker not available. Results will not be re-ranked. "
                "Install with: pip install FlagEmbedding"
            )
            self._initialized = True
            return
        
        try:
            logger.info(f"Loading BGE-Reranker model: {self.model_name}")
            import torch
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            self.model = CrossEncoder(self.model_name, device=device, max_length=384)
            logger.info("✅ BGE-Reranker model loaded successfully")
            logger.info(f"   - Model: Cross-Encoder (judges query-document pairs)")
            logger.info(f"   - Purpose: Eliminate hallucination sources")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize reranker: {e}")
            logger.warning("Continuing without reranking...")
            self._initialized = True
    
    def _score(self, pairs: List[List[str]]) -> List[float]:
        """Sigmoid-normalised relevance in [0, 1] (same scale as FlagReranker normalize=True)."""
        import torch
        scores = self.model.predict(pairs, batch_size=16, activation_fn=torch.nn.Sigmoid(),
                                    show_progress_bar=False)
        return [float(x) for x in scores]
    
    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Re-rank documents based on query relevance.
        
        Args:
            query: User query
            documents: List of document dicts (must have 'content' or 'text' field)
            top_k: Return top K documents after re-ranking
            score_threshold: Minimum relevance score (filter out low-quality matches)
            
        Returns:
            Re-ranked list of documents with 'rerank_score' field added
        """
        if not self._initialized:
            self.initialize()
        
        if not documents:
            return []
        
        # If reranker not available, return original documents
        if self.model is None:
            logger.debug("Reranker not available, returning original order")
            return documents[:top_k]
        
        try:
            # Extract text from documents
            doc_texts = []
            for doc in documents:
                # Try different field names for document content
                text = doc.get('content') or doc.get('text') or doc.get('page_content') or str(doc)
                doc_texts.append(text)
            
            # Create query-document pairs for the reranker
            pairs = [[query, doc_text] for doc_text in doc_texts]
            
            # Get relevance scores from the reranker
            scores = self._score(pairs)
            
            # Handle single score (if only one document)
            if isinstance(scores, float):
                scores = [scores]
            
            # Add scores to documents
            for doc, score in zip(documents, scores):
                doc['rerank_score'] = float(score)
            
            # Filter by threshold
            filtered_docs = [doc for doc in documents if doc['rerank_score'] >= score_threshold]
            
            # Sort by rerank score (descending)
            filtered_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            # Return top K
            top_docs = filtered_docs[:top_k]
            
            logger.info(f"Reranked {len(documents)} docs → Top {len(top_docs)} (threshold: {score_threshold})")
            if top_docs:
                logger.debug(f"Top score: {top_docs[0]['rerank_score']:.4f}, Bottom score: {top_docs[-1]['rerank_score']:.4f}")
            
            return top_docs
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            logger.warning("Falling back to original order")
            return documents[:top_k]
    
    def rerank_with_scores(
        self,
        query: str,
        documents: List[str]
    ) -> List[Tuple[int, float]]:
        """
        Re-rank documents and return indices with scores.
        
        Args:
            query: User query
            documents: List of document texts
            
        Returns:
            List of (index, score) tuples sorted by score (descending)
        """
        if not self._initialized:
            self.initialize()
        
        if not documents:
            return []
        
        if self.model is None:
            # Return original order with dummy scores
            return [(i, 1.0) for i in range(len(documents))]
        
        try:
            pairs = [[query, doc] for doc in documents]
            scores = self._score(pairs)
            
            if isinstance(scores, float):
                scores = [scores]
            
            # Create (index, score) pairs and sort by score
            indexed_scores = [(i, float(score)) for i, score in enumerate(scores)]
            indexed_scores.sort(key=lambda x: x[1], reverse=True)
            
            return indexed_scores
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return [(i, 1.0) for i in range(len(documents))]


# Singleton instance
_reranker_service: RerankerService = None


def get_reranker_service() -> RerankerService:
    """Get or create the singleton reranker service."""
    global _reranker_service
    if _reranker_service is None:
        from app.config import settings
        _reranker_service = RerankerService(model_name=settings.reranker_model)
        _reranker_service.initialize()
    return _reranker_service


if __name__ == "__main__":
    # Test the reranker service
    service = get_reranker_service()
    
    query = "What is the punishment for murder?"
    
    documents = [
        {"content": "Section 302 IPC: Punishment for murder - death penalty or life imprisonment", "id": "1"},
        {"content": "Section 304: Punishment for culpable homicide not amounting to murder", "id": "2"},
        {"content": "Section 307: Attempt to murder", "id": "3"},
        {"content": "Traffic rules and regulations for motor vehicles", "id": "4"},  # Irrelevant
        {"content": "The penalty for murder under IPC 302 is severe", "id": "5"}
    ]
    
    reranked = service.rerank(query, documents, top_k=3, score_threshold=0.3)
    
    print(f"\nQuery: {query}\n")
    print("Re-ranked results:")
    for i, doc in enumerate(reranked, 1):
        print(f"{i}. Score: {doc['rerank_score']:.4f} - {doc['content'][:80]}...")
