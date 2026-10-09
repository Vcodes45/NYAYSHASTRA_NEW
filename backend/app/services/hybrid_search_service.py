"""
NyayaShastra - Hybrid Legal Retrieval

query -> metadata exact-match (act/section) -> dense (BGE-M3) + lexical (BM25)
      -> Reciprocal Rank Fusion -> dedupe -> cross-encoder rerank -> top-k evidence

RAG is the source of legal facts; this module never calls the generation model.
"""

import hashlib
import logging
import re
import time
from collections import OrderedDict
from typing import List, Dict, Any, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)

RRF_K = 60
EXACT_MATCH_WEIGHT = 3.0  # exact act+section metadata hits dominate fusion
EXACT_COMPANION_MIN_SCORE = 0.8
_TOKEN_RE = re.compile(r"\w+")
DOMAIN_ALIASES = {"consitutional": "constitutional", "civil": "civil_family", "cyber": "it_cyber"}


class EmptyKnowledgeBaseError(RuntimeError):
    """Raised when the vector collection has no documents."""


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip().lower())


class HybridSearchService:
    """Hybrid dense + BM25 retrieval with RRF fusion and cross-encoder reranking."""

    def __init__(self, chroma_client, embedding_service, reranker_service=None,
                 collection_name: Optional[str] = None):
        self.chroma_client = chroma_client
        self.embedding_service = embedding_service
        self.reranker_service = reranker_service
        self.collection_name = collection_name or settings.rag_collection
        self.collection = None
        self.bm25 = None
        self.bm25_ids: List[str] = []
        self.bm25_docs: Dict[str, Dict[str, Any]] = {}
        self._bm25_count = -1
        self._cache: "OrderedDict[str, Tuple[List[Dict[str, Any]], Dict[str, Any]]]" = OrderedDict()

    # ------------------------------------------------------------------ setup
    def initialize(self):
        self.collection = self.chroma_client.get_or_create_collection(self.collection_name)
        self._refresh_bm25()

    def count(self) -> int:
        return self.collection.count() if self.collection else 0

    def _refresh_bm25(self):
        """(Re)build the in-memory BM25 index when the collection size changes."""
        n = self.count()
        if n == self._bm25_count:
            return
        self._cache.clear()
        self._bm25_count = n
        if n == 0:
            self.bm25, self.bm25_ids, self.bm25_docs = None, [], {}
            return
        from rank_bm25 import BM25Okapi
        data = self.collection.get(include=["documents", "metadatas"])
        self.bm25_ids = data["ids"]
        self.bm25_docs = {
            i: {"content": d, "metadata": m or {}}
            for i, d, m in zip(data["ids"], data["documents"], data["metadatas"])
        }
        self.bm25 = BM25Okapi([_tokenize(self._index_text(self.bm25_docs[i])) for i in self.bm25_ids])
        logger.info(f"[RETRIEVAL] BM25 index built over {n} chunks")

    @staticmethod
    def _index_text(doc: Dict[str, Any]) -> str:
        m = doc["metadata"]
        header = " ".join(str(m.get(k, "")) for k in ("act_code", "act_name", "section", "article", "section_title"))
        return f"{header} {doc['content']}"

    def diagnostics(self) -> Dict[str, Any]:
        meta = self.collection.metadata if self.collection else {}
        return {
            "collection": self.collection_name,
            "document_count": self.count(),
            "embedding_model": getattr(self.embedding_service, "model_name", None),
            "embedding_dimension": self.embedding_service.get_embedding_dimension(),
            "index_embedding_model": (meta or {}).get("embedding_model"),
            "reranker": settings.reranker_model if self.reranker_service else None,
        }

    # -------------------------------------------------------------- filtering
    @staticmethod
    def _where(domain: Optional[str], act_codes: Optional[List[str]]) -> Optional[Dict[str, Any]]:
        clauses = []
        if act_codes:
            clauses.append({"act_code": {"$in": list(act_codes)}})
        elif domain and domain.lower() not in ("all", "", "general", "other"):
            clauses.append({"domain": DOMAIN_ALIASES.get(domain.lower(), domain.lower())})
        if not clauses:
            return None
        return clauses[0] if len(clauses) == 1 else {"$and": clauses}

    @staticmethod
    def _matches(meta: Dict[str, Any], where: Optional[Dict[str, Any]]) -> bool:
        if not where:
            return True
        clauses = where.get("$and", [where])
        for clause in clauses:
            for key, cond in clause.items():
                value = meta.get(key)
                if isinstance(cond, dict) and "$in" in cond:
                    if value not in cond["$in"]:
                        return False
                elif value != cond:
                    return False
        return True

    # -------------------------------------------------------------- retrievers
    def _exact(self, act_codes: Optional[List[str]], sections: Optional[List[Any]],
               articles: Optional[List[str]]) -> List[str]:
        """Exact metadata lookup. A section may be a plain number or an (act_code, number) pair."""
        ids: List[str] = []
        for ref in sections or []:
            act, num = ref if isinstance(ref, (tuple, list)) else (None, ref)
            acts = [act] if act else act_codes
            where: Dict[str, Any] = {"section": str(num).upper()}
            if acts:
                where = {"$and": [where, {"act_code": {"$in": list(acts)}}]}
            ids += self.collection.get(where=where, include=[])["ids"]
        if articles:
            ids += self.collection.get(where={"article": {"$in": [a.upper() for a in articles]}}, include=[])["ids"]
        return list(dict.fromkeys(ids))

    def missing_sections(self, refs: List[Any]) -> List[Tuple[str, str]]:
        """(act, section) refs whose act is indexed but whose section does not exist in it."""
        missing = []
        for ref in refs or []:
            if not isinstance(ref, (tuple, list)) or not ref[0]:
                continue
            act, num = ref
            if not self.collection.get(where={"act_code": act}, limit=1, include=[])["ids"]:
                continue  # act not indexed: absence proves nothing
            hit = self.collection.get(where={"$and": [{"act_code": act}, {"section": str(num).upper()}]},
                                      limit=1, include=[])["ids"]
            if not hit:
                missing.append((act, str(num).upper()))
        return missing

    def _dense(self, query: str, where: Optional[Dict[str, Any]], k: int) -> List[Tuple[str, float]]:
        emb = self.embedding_service.embed_query(query)
        emb = emb.tolist() if hasattr(emb, "tolist") else emb
        res = self.collection.query(query_embeddings=[emb], n_results=k, where=where, include=["distances"])
        return list(zip(res["ids"][0], res["distances"][0])) if res["ids"] else []

    def _lexical(self, query: str, where: Optional[Dict[str, Any]], k: int) -> List[Tuple[str, float]]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        out = []
        for i in ranked:
            if scores[i] <= 0:
                break
            doc_id = self.bm25_ids[i]
            if self._matches(self.bm25_docs[doc_id]["metadata"], where):
                out.append((doc_id, float(scores[i])))
                if len(out) >= k:
                    break
        return out

    # ------------------------------------------------------------------ search
    def search(self, query: str, domain: Optional[str] = None, act_codes: Optional[List[str]] = None,
               sections: Optional[List[str]] = None, articles: Optional[List[str]] = None,
               top_k: Optional[int] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Return (evidence, diagnostics). Evidence is reranked and capped at top_k."""
        t0 = time.perf_counter()
        top_k = top_k or settings.rag_top_k
        self._refresh_bm25()
        if self.count() == 0:
            raise EmptyKnowledgeBaseError(
                f"Vector collection '{self.collection_name}' is empty. Run scripts/ingest_statutes.py first."
            )

        key = hashlib.sha256(
            f"{_normalize_query(query)}|{domain}|{sorted(act_codes or [])}|{sorted(map(str, sections or []))}|"
            f"{sorted(articles or [])}|{top_k}".encode()
        ).hexdigest()
        if key in self._cache:
            self._cache.move_to_end(key)
            evidence, diag = self._cache[key]
            return evidence, {**diag, "cache_hit": True}

        where = self._where(domain, act_codes)
        exact_ids = self._exact(act_codes, sections, articles)
        dense = self._dense(query, where, settings.rag_dense_k)
        if not dense and where:  # metadata filter too narrow: fall back to the whole corpus
            where = None
            dense = self._dense(query, None, settings.rag_dense_k)
        lexical = self._lexical(query, where, settings.rag_lexical_k)
        t_retrieve = time.perf_counter()

        # Reciprocal Rank Fusion
        fused: Dict[str, float] = {}
        for rank, doc_id in enumerate(exact_ids):
            fused[doc_id] = fused.get(doc_id, 0) + EXACT_MATCH_WEIGHT / (RRF_K + rank + 1)
        for ranked in (dense, lexical):
            for rank, (doc_id, _) in enumerate(ranked):
                fused[doc_id] = fused.get(doc_id, 0) + 1.0 / (RRF_K + rank + 1)
        dense_dist = dict(dense)

        candidates, seen_text = [], set()
        for doc_id in sorted(fused, key=fused.get, reverse=True):
            doc = self.bm25_docs.get(doc_id)
            if not doc:
                continue
            fingerprint = hashlib.md5(_normalize_query(doc["content"])[:500].encode()).hexdigest()
            if fingerprint in seen_text:  # near-verbatim duplicate chunk
                continue
            seen_text.add(fingerprint)
            candidates.append({
                "id": doc_id,
                "content": doc["content"],
                "metadata": doc["metadata"],
                "rrf_score": round(fused[doc_id], 5),
                "dense_similarity": round(1 - dense_dist[doc_id], 4) if doc_id in dense_dist else None,
                "exact_match": doc_id in exact_ids,
            })
        candidates = candidates[: settings.rag_rerank_candidates]

        evidence = self._rerank(query, candidates, top_k)
        t_end = time.perf_counter()

        diag = {
            "query_hash": key[:12],
            "where": where,
            "exact_matches": len(exact_ids),
            "dense_candidates": len(dense),
            "lexical_candidates": len(lexical),
            "fused_candidates": len(candidates),
            "selected": len(evidence),
            "top_scores": [e.get("rerank_score", e["rrf_score"]) for e in evidence],
            "retrieval_ms": round((t_retrieve - t0) * 1000, 1),
            "rerank_ms": round((t_end - t_retrieve) * 1000, 1),
            "cache_hit": False,
        }
        logger.info(f"[RETRIEVAL] {diag}")
        self._cache[key] = (evidence, diag)
        if len(self._cache) > settings.rag_cache_size:
            self._cache.popitem(last=False)
        return evidence, diag

    def _rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """Cross-encoder rerank; exact metadata matches are always retained first."""
        if not candidates:
            return []
        if self.reranker_service is None:
            return candidates[:top_k]
        try:
            scored = self.reranker_service.rerank_with_scores(
                query, [self._index_text(c) for c in candidates]
            )
            if scored and all(s == 1.0 for _, s in scored):  # reranker model unavailable
                return candidates[:top_k]
            for idx, score in scored:
                candidates[idx]["rerank_score"] = round(score, 4)
        except Exception as e:
            logger.error(f"[RERANK] failed, using fusion order: {e}")
            return candidates[:top_k]

        exact = [c for c in candidates if c["exact_match"]]
        rest = sorted((c for c in candidates if not c["exact_match"]),
                      key=lambda c: c["rerank_score"], reverse=True)
        # With an exact act/section hit the query often has no topical words for the reranker to use,
        # so only very strong non-exact matches may accompany it
        floor = EXACT_COMPANION_MIN_SCORE if exact else settings.rag_min_rerank_score
        rest = [c for c in rest if c["rerank_score"] >= floor]
        exact.sort(key=lambda c: c["rerank_score"], reverse=True)
        selected = (exact + rest)[:top_k]
        logger.info(f"[RERANK] {len(candidates)} -> {len(selected)} "
                    f"scores={[c['rerank_score'] for c in selected]}")
        return selected


_hybrid_search_service: Optional[HybridSearchService] = None


def get_hybrid_search_service() -> HybridSearchService:
    """Singleton built on the shared vector-store client and embedding model."""
    global _hybrid_search_service
    if _hybrid_search_service is None:
        import chromadb
        from app.services.embedding_service import get_embedding_service

        reranker = None
        if settings.use_reranker:
            from app.services.reranker_service import get_reranker_service
            reranker = get_reranker_service()
        service = HybridSearchService(
            chroma_client=chromadb.PersistentClient(path=settings.chroma_persist_dir),
            embedding_service=get_embedding_service(),
            reranker_service=reranker,
        )
        service.initialize()
        _hybrid_search_service = service
    return _hybrid_search_service
