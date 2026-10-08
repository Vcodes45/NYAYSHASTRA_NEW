"""
NyayaShastra - Local Embedding Service (MEMORY-OPTIMIZED)
Uses BGE-M3 for Multi-Lingual (Hindi + English), Long Context (8k tokens) embeddings
State-of-the-Art dense retrieval for semantic search
"""

import os
import logging
from typing import List, Union
import numpy as np

# CRITICAL: Force CPU-only mode to prevent OOM crashes
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

logger = logging.getLogger(__name__)

# Imports moved inside for lazy loading to save RAM on cloud
BGE_M3_AVAILABLE = True
SENTENCE_TRANSFORMERS_AVAILABLE = True
BGEM3FlagModel = None
SentenceTransformer = None


class EmbeddingService:
    """
    Local embedding service using BGE-M3 for superior semantic understanding.
    Falls back to sentence-transformers if BGE-M3 is not available.
    """
    
    def __init__(self, model_name: str = None, use_fp16: bool = False):
        """
        Initialize embedding service (MEMORY-OPTIMIZED).
        
        Args:
            model_name: Model identifier (defaults to settings.embedding_model)
            use_fp16: Use half precision - DISABLED for CPU stability
        """
        from app.config import settings
        
        if model_name:
            self.model_name = model_name
        else:
            self.model_name = settings.embedding_model
            
        self.use_fp16 = False  # Force FP32 for CPU stability
        self.model = None
        # Adjust dimension based on model name
        if "bge-m3" in self.model_name.lower():
            self.embedding_dim = 1024
        elif "all-MiniLM-L6-v2" in self.model_name.lower():
            self.embedding_dim = 384
        else:
            self.embedding_dim = 768 # Default for MiniLM-L12
            
        self._initialized = False
        self.use_api = False
        self._query_cache = {}
        
    def initialize(self):
        """Lazy initialization of the embedding model."""
        if self._initialized:
            return
            
        from app.config import settings
        
        # Gemini API embeddings only when explicitly enabled: the index must be built with the same model
        if settings.embedding_use_api and settings.gemini_api_key:
            self.use_api = True
            self.api_key = settings.gemini_api_key
            self.embedding_dim = 768  # text-embedding-004 dimension
            logger.info("✅ Using Gemini API for embeddings (Memory Optimized: 0MB RAM)")
            self._initialized = True
            return
            
        try:
            # sentence-transformers loads BGE-M3 dense head natively (FlagEmbedding is incompatible
            # with transformers>=5). No silent fallback to another model: the index dimension must match.
            import torch
            from sentence_transformers import SentenceTransformer
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            logger.info(f"Loading embedding model: {self.model_name} on {device}")
            self.model = SentenceTransformer(self.model_name, device=device)
            self.model.max_seq_length = min(self.model.max_seq_length or 1024, 1024)
            self.embedding_dim = self.model.get_embedding_dimension()
            logger.info(f"✅ Model {self.model_name} loaded (dim: {self.embedding_dim})")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            raise
    
    def embed(self, text: Union[str, List[str]], batch_size: int = 8) -> np.ndarray:
        """
        Generate embeddings for text(s) (MEMORY-OPTIMIZED).
        
        Args:
            text: Single text or list of texts
            batch_size: Batch size (REDUCED to 8 to prevent OOM)
            
        Returns:
            numpy array of embeddings (shape: [n_texts, embedding_dim])
        """
        if not self._initialized:
            self.initialize()
        
        # Convert single text to list
        is_single = isinstance(text, str)
        texts = [text] if is_single else text
        
        # Remove empty strings
        texts = [t if t else " " for t in texts]
        
        try:
            if self.use_api:
                # Use Gemini API via httpx
                import httpx
                import asyncio
                import json
                
                async def _get_api_embeddings():
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        results = []
                        for i in range(0, len(texts), batch_size):
                            batch = texts[i:i+batch_size]
                            for t in batch:
                                response = await client.post(
                                    f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}",
                                    json={"model": "models/text-embedding-004", "content": {"parts": [{"text": t}]}}
                                )
                                if response.status_code == 200:
                                    results.append(response.json()["embedding"]["values"])
                                else:
                                    # Fallback vector on error
                                    results.append([0.0] * self.embedding_dim)
                        return results
                
                try:
                    # If there's a running loop, run in current loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import nest_asyncio
                        nest_asyncio.apply()
                    embeddings_list = loop.run_until_complete(_get_api_embeddings())
                except RuntimeError:
                    embeddings_list = asyncio.run(_get_api_embeddings())
                    
                embeddings = np.array(embeddings_list)
                
            else:
                embeddings = self.model.encode(
                    texts,
                    batch_size=min(batch_size, 16),
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # cosine space in Chroma
                )
            
            # Return single embedding if input was single text
            if is_single:
                return embeddings[0]
            
            return embeddings
            
        except Exception as e:
            # Fail loudly: zero vectors would silently return arbitrary "evidence"
            logger.error(f"[EMBEDDING] generation failed: {e}")
            raise
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a search query.
        Some models have different encoding for queries vs documents.
        
        Args:
            query: Search query text
            
        Returns:
            Query embedding vector
        """
        # For BGE-M3, queries and documents use the same encoding; cache repeated queries
        key = query.strip()
        cached = self._query_cache.get(key)
        if cached is not None:
            return cached
        vec = self.embed(query)
        self._query_cache[key] = vec
        if len(self._query_cache) > 512:
            self._query_cache.pop(next(iter(self._query_cache)))
        return vec
    
    def embed_documents(self, documents: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for documents.
        
        Args:
            documents: List of document texts
            batch_size: Batch size for processing
            
        Returns:
            Document embeddings (shape: [n_docs, embedding_dim])
        """
        return self.embed(documents, batch_size=batch_size)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        if not self._initialized:
            self.initialize()
        return self.embedding_dim


# Singleton instance
_embedding_service: EmbeddingService = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the singleton embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
        _embedding_service.initialize()
    return _embedding_service


if __name__ == "__main__":
    # Test the embedding service
    service = get_embedding_service()
    
    # Test English
    en_text = "What is the punishment for murder under IPC Section 302?"
    en_emb = service.embed_query(en_text)
    print(f"English embedding shape: {en_emb.shape}")
    
    # Test Hindi
    hi_text = "आईपीसी धारा 302 के तहत हत्या की सजा क्या है?"
    hi_emb = service.embed_query(hi_text)
    print(f"Hindi embedding shape: {hi_emb.shape}")
    
    # Test similarity
    similarity = np.dot(en_emb, hi_emb) / (np.linalg.norm(en_emb) * np.linalg.norm(hi_emb))
    print(f"Cross-lingual similarity: {similarity:.4f}")
    
    # Test batch
    docs = [
        "Section 302 IPC deals with punishment for murder",
        "Section 307 IPC deals with attempt to murder",
        "Section 304 IPC deals with culpable homicide"
    ]
    doc_embs = service.embed_documents(docs)
    print(f"Batch embeddings shape: {doc_embs.shape}")
