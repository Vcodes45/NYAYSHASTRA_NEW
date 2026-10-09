"""Hybrid retrieval tests on an in-memory Chroma collection with a deterministic fake embedder."""

import hashlib

import numpy as np
import pytest

from app.services.hybrid_search_service import HybridSearchService, EmptyKnowledgeBaseError

DIM = 64


class FakeEmbedder:
    model_name = "fake"

    def get_embedding_dimension(self):
        return DIM

    def _vec(self, text):
        v = np.zeros(DIM)
        for tok in text.lower().split():
            v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1
        n = np.linalg.norm(v)
        return v / n if n else v

    def embed_query(self, text):
        return self._vec(text)

    def embed_documents(self, texts):
        return np.array([self._vec(t) for t in texts])


class FakeReranker:
    """Scores by query-token overlap; returns (index, score) like RerankerService.rerank_with_scores."""

    def rerank_with_scores(self, query, docs):
        q = set(query.lower().split())
        scores = [len(q & set(d.lower().split())) / max(1, len(q)) for d in docs]
        return sorted(enumerate(scores), key=lambda x: x[1], reverse=True)


DOCS = [
    ("BNS:s103:c0", "Whoever commits murder shall be punished with death or imprisonment for life",
     {"act_code": "BNS", "section": "103", "section_title": "Punishment for murder", "domain": "criminal"}),
    ("BNS:s303:c0", "Whoever intending to take dishonestly any movable property commits theft",
     {"act_code": "BNS", "section": "303", "section_title": "Theft", "domain": "criminal"}),
    ("BNS:s318:c0", "Whoever by deceiving any person fraudulently induces delivery of property cheats",
     {"act_code": "BNS", "section": "318", "section_title": "Cheating", "domain": "criminal"}),
    ("COI:a21:c0", "No person shall be deprived of his life or personal liberty except according to procedure",
     {"act_code": "COI", "article": "21", "section_title": "Protection of life", "domain": "constitutional"}),
    ("COI:a21:dup", "No person shall be deprived of his life or personal liberty except according to procedure",
     {"act_code": "COI", "article": "21", "section_title": "Protection of life", "domain": "constitutional"}),
]


@pytest.fixture
def service():
    import chromadb
    client = chromadb.EphemeralClient()
    name = f"test_{np.random.randint(1e9)}"
    emb = FakeEmbedder()
    col = client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
    col.add(ids=[d[0] for d in DOCS], documents=[d[1] for d in DOCS], metadatas=[d[2] for d in DOCS],
            embeddings=emb.embed_documents([d[1] for d in DOCS]).tolist())
    svc = HybridSearchService(client, emb, FakeReranker(), collection_name=name)
    svc.initialize()
    return svc


def test_exact_section_lookup_is_pinned_first(service):
    ev, diag = service.search("what does it say", act_codes=["BNS"], sections=["303"], top_k=3)
    assert ev[0]["id"] == "BNS:s303:c0" and ev[0]["exact_match"]
    assert diag["exact_matches"] == 1


def test_semantic_and_lexical_fusion_finds_relevant_section(service):
    ev, diag = service.search("punishment for murder death", top_k=2)
    assert ev[0]["id"] == "BNS:s103:c0"
    assert diag["dense_candidates"] > 0 and diag["lexical_candidates"] > 0


def test_duplicates_removed_and_cache_hit(service):
    ev, _ = service.search("personal liberty life deprived", top_k=5)
    ids = [e["id"] for e in ev]
    assert not ({"COI:a21:c0", "COI:a21:dup"} <= set(ids))
    _, diag = service.search("personal liberty life deprived", top_k=5)
    assert diag["cache_hit"]


def test_irrelevant_query_returns_no_evidence(service):
    ev, _ = service.search("zzz qqq xyz", top_k=5)
    assert ev == []


def test_domain_filter(service):
    ev, diag = service.search("person life", domain="Consitutional", top_k=5)
    assert ev and all(e["metadata"]["domain"] == "constitutional" for e in ev)


def test_empty_collection_fails_fast():
    import chromadb
    client = chromadb.EphemeralClient()
    svc = HybridSearchService(client, FakeEmbedder(), None, collection_name=f"empty_{np.random.randint(1e9)}")
    svc.initialize()
    with pytest.raises(EmptyKnowledgeBaseError):
        svc.search("anything")


def test_section_bound_to_act_avoids_cross_act_confusion(service):
    """'IPC Section 303' must not pin BNS s.303 as an exact match (IPC/BNS confusion)."""
    ev, diag = service.search("IPC section 303 theft", act_codes=["IPC", "BNS"], sections=[("IPC", "303")], top_k=3)
    assert diag["exact_matches"] == 0
    assert not any(e["exact_match"] for e in ev)


def test_query_agent_binds_sections_to_adjacent_acts():
    from app.agents.query_agent import QueryUnderstandingAgent
    from app.services.grounding import ACT_ALIASES
    bind = QueryUnderstandingAgent._bind_sections_to_acts
    assert bind("How does IPC Section 302 compare with BNS?", ACT_ALIASES) == {"302": "IPC"}
    assert bind("s. 35 BNSS and section 63 of the Bharatiya Sakshya Adhiniyam", ACT_ALIASES) == {"35": "BNSS", "63": "BSA"}


def test_missing_section_in_indexed_act_is_detected(service):
    assert service.missing_sections([("BNS", "999"), ("BNS", "303"), ("IPC", "302"), (None, "5")]) == [("BNS", "999")]
