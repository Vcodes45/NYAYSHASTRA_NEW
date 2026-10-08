# NyayShastra - Grounded Legal RAG + Local SLM

RAG owns legal facts. The local SLM (`nyayshastra-legal`, Qwen2.5-3B legal, Q4_K_M via Ollama)
only explains retrieved evidence. Cloud LLMs are never used for chat unless
`ALLOW_CLOUD_FALLBACK=true` and the local SLM fails.

## Request path (`POST /api/chat/`, `/api/chat/stream`)

```
query
 -> QueryUnderstandingAgent   language; domain via BM25+embedding classifier (no LLM call);
                              explicit acts, sections bound to their act ("IPC s.302" != "BNS s.302"), articles
 -> StatuteRetrievalAgent     HybridSearchService.search():
                                exact metadata lookup (act+section / article)      pinned first
                                dense BGE-M3 top-15 (domain filter only if confident) + BM25 top-15
                                Reciprocal Rank Fusion -> dedupe -> top-12 candidates
                                cross-encoder rerank (bge-reranker-v2-m3) -> top-5, score >= 0.15
                              LRU cache on normalised query hash; fail fast if the collection is empty
 -> Case / Regulatory / Citation agents (UI metadata; never SLM evidence)
 -> ResponseSynthesisAgent    no evidence            -> controlled refusal, SLM not called
                              explicit section absent -> deterministic "does not exist" answer
                              else grounding.build_context(): merge sibling chunks, keep query-relevant
                                clauses, <= 3000-token budget, [S#] source ids
                              -> local SLM (temperature 0.1, <= 512 output tokens, repeat_penalty 1.15)
                              -> dedupe looped sentences -> verify_citations() per sentence:
                                 [S#] ids, sections (with act), articles, case names, terms of years
                                 must be supported by the source(s) that sentence cites
                              unverified anything -> summary withheld, verbatim statutory text shown
                              verified           -> answer + verbatim excerpt + deterministic source list
```

Additive API fields (existing fields unchanged): `answer, sources, domain, confidence, grounded,
model, retrieved_documents, grounding{cited_sources, verified/unverified_references, usage, slm_ms},
retrieval{retrieval_ms, rerank_ms, top_scores, cache_hit, ...}`.

Diagnostics: `GET /health/rag` (collection, count, embedding model/dimension, reranker, LLM provider/model;
HTTP 503 when the index is empty or the SLM is down). Log tags: `[RETRIEVAL] [RERANK] [CONTEXT] [OLLAMA]
[CITATION] [RESPONSE]`.

## Corpus

| Act | Source (provenance in `backend/manifests/`) | Sections | Chunks |
|---|---|---|---|
| BNS 2023 | Gazette of India (MHA-hosted copy) | 358 | 428 |
| BNSS 2023 | Gazette of India (MHA-hosted copy) | 531 | 634 |
| BSA 2023 | Gazette of India (MHA-hosted copy) | 170 | 200 |

IPC, CrPC, Indian Evidence Act and the Constitution are listed in `manifests/sources.json` but India Code
was returning 504s at ingestion time; re-run `scripts/fetch_sources.py` and `scripts/ingest_statutes.py`.
No judgment corpus is indexed: case-law questions are refused by design.

Ingestion (`scripts/ingest_statutes.py`): layout-aware PDF parsing (body column vs marginal notes),
one record per section with title, chapter, act, authority level, source URL, status and effective date;
long sections split on sub-section boundaries (<= 1800 chars); legal wording is never rewritten.

## Measured (Apple M1 Pro 16 GB, 2026-10-08)

Retrieval, 125 benchmark items with gold sections: Recall@5 0.88, MRR 0.85, nDCG@5 0.85
(statute/procedural/citation ~1.0; comparative 0.40 because IPC is not indexed).

End-to-end, 35 stratified items: unsupported claims surfaced to users 0; raw SLM unsupported-claim
rate 39% (all withheld by the verifier); refusal accuracy 0.91 (0 missed refusals; 3 false refusals,
all IPC-comparison questions); p50 total 9.2 s (retrieval 45 ms, rerank 2.5 s, SLM 4.9 s);
~990 prompt tokens and ~180 completion tokens per answer.

Reproduce: `python evaluation/evaluate.py --mode retrieval` and `--mode e2e --limit 35`.

## Setup

```bash
cd backend
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt
ollama serve &  ollama create nyayshastra-legal -f ollama/Modelfile
python scripts/fetch_sources.py && python scripts/ingest_statutes.py --reset
python -m pytest tests -q
uvicorn app.main:app --port 8000
```
