"""
NyayShastra evaluation harness.

Retrieval : Recall@k, Precision@k, MRR, nDCG@k on items with gold parent ids.
Grounding : grounded rate, unsupported-reference rate, citation presence.
Generation: refusal correctness, must_contain / must_not_contain checks.
Cost      : retrieval / rerank / SLM / total latency, prompt + completion tokens, peak RSS.

Usage:
  python evaluation/evaluate.py --mode retrieval            # fast, no SLM
  python evaluation/evaluate.py --mode e2e --limit 20       # full pipeline through the orchestrator
"""

import argparse
import asyncio
import json
import math
import resource
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
BENCH = ROOT / "evaluation" / "benchmark.jsonl"
RESULTS = ROOT / "evaluation" / "results"


def parent_of(evidence_item):
    return evidence_item["metadata"].get("parent_document_id") or evidence_item["id"].rsplit(":c", 1)[0]


def retrieval_metrics(ranked_parents, gold, k):
    top = ranked_parents[:k]
    hits = [1 if p in gold else 0 for p in top]
    recall = len(set(top) & set(gold)) / len(gold)
    precision = sum(hits) / max(1, len(top))
    rr = next((1 / (i + 1) for i, h in enumerate(hits) if h), 0.0)
    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits))
    idcg = sum(1 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return recall, precision, rr, (dcg / idcg if idcg else 0.0)


def summarize(values):
    return round(statistics.mean(values), 4) if values else None


def pct(values, q):
    if not values:
        return None
    values = sorted(values)
    return round(values[min(len(values) - 1, int(q * len(values)))], 1)


def run_retrieval(items, k):
    from app.agents.query_agent import QueryUnderstandingAgent
    from app.agents.base import AgentContext
    from app.services.hybrid_search_service import get_hybrid_search_service

    search = get_hybrid_search_service()
    qa = QueryUnderstandingAgent()
    rows = []
    for it in items:
        if not it["gold_parent_ids"]:
            continue
        ctx = asyncio.run(qa.process(AgentContext(it["question"])))
        ents = {t: [e["value"] for e in ctx.entities if e["type"] == t] for t in ("article", "act")}
        ents["section"] = [(e.get("act"), e["value"]) for e in ctx.entities if e["type"] == "section"]
        t0 = time.perf_counter()
        ev, diag = search.search(it["question"], act_codes=ents["act"] or None,
                                 sections=ents["section"] or None, articles=ents["article"] or None, top_k=k)
        ms = (time.perf_counter() - t0) * 1000
        parents = list(dict.fromkeys(parent_of(e) for e in ev))
        r, p, rr, ndcg = retrieval_metrics(parents, it["gold_parent_ids"], k)
        rows.append({"id": it["id"], "category": it["category"], "recall": r, "precision": p, "mrr": rr,
                     "ndcg": ndcg, "latency_ms": ms, "retrieved": parents, "gold": it["gold_parent_ids"],
                     "top_scores": diag.get("top_scores")})
    by_cat = {}
    for row in rows:
        by_cat.setdefault(row["category"], []).append(row)
    report = {
        f"recall@{k}": summarize([r["recall"] for r in rows]),
        f"precision@{k}": summarize([r["precision"] for r in rows]),
        "mrr": summarize([r["mrr"] for r in rows]),
        f"ndcg@{k}": summarize([r["ndcg"] for r in rows]),
        "latency_ms_p50": pct([r["latency_ms"] for r in rows], 0.5),
        "latency_ms_p95": pct([r["latency_ms"] for r in rows], 0.95),
        "n": len(rows),
        "by_category": {c: {"recall": summarize([r["recall"] for r in rs]), "mrr": summarize([r["mrr"] for r in rs]),
                            "n": len(rs)} for c, rs in by_cat.items()},
    }
    return report, rows


async def run_e2e(items):
    from app.agents.orchestrator import get_orchestrator

    orch = get_orchestrator()
    await orch._ensure_services()
    rows = []
    for it in items:
        t0 = time.perf_counter()
        res = await orch.process_query(it["question"])
        total_ms = (time.perf_counter() - t0) * 1000
        answer = (res.get("answer") or "").lower()
        g = res.get("grounding", {})
        refused = bool(g.get("refusal")) or g.get("reason") in ("no_relevant_evidence", "empty_knowledge_base", "section_not_found")
        parents = [s.get("chunk_id", "").rsplit(":c", 1)[0] for s in res.get("sources", [])]
        gold_hit = bool(set(parents) & set(it["gold_parent_ids"])) if it["gold_parent_ids"] else None
        rows.append({
            "id": it["id"], "category": it["category"], "question": it["question"],
            "expect_refusal": it["expect_refusal"], "refused": refused,
            "refusal_correct": refused == it["expect_refusal"],
            "grounded": res.get("grounded"), "confidence": res.get("confidence"),
            "unverified": g.get("unverified_references", []),
            "suppressed": bool(g.get("suppressed_answer")),
            "cited": g.get("cited_sources", []),
            "gold_in_context": gold_hit,
            "contains_ok": (not it.get("must_contain_any")) or any(m.lower() in answer for m in it["must_contain_any"]),
            "forbidden_hit": any(m.lower() in answer for m in it.get("must_not_contain", [])),
            "retrieval_ms": (res.get("retrieval") or {}).get("retrieval_ms"),
            "rerank_ms": (res.get("retrieval") or {}).get("rerank_ms"),
            "slm_ms": g.get("slm_ms"), "total_ms": total_ms,
            "prompt_tokens": (g.get("usage") or {}).get("prompt_tokens"),
            "completion_tokens": (g.get("usage") or {}).get("completion_tokens"),
            "context_tokens_est": g.get("context_tokens_est"),
            "model": res.get("model"),
            "answer": res.get("answer"),
        })
        print(f"[EVAL] {it['id']} refused={refused} expect={it['expect_refusal']} grounded={res.get('grounded')} "
              f"unverified={len(rows[-1]['unverified'])} {total_ms:.0f}ms", flush=True)

    answered = [r for r in rows if not r["refused"]]
    num = lambda key: [r[key] for r in rows if isinstance(r[key], (int, float))]
    report = {
        "n": len(rows),
        "refusal_accuracy": summarize([1.0 if r["refusal_correct"] else 0.0 for r in rows]),
        "false_refusals": sum(1 for r in rows if r["refused"] and not r["expect_refusal"]),
        "missed_refusals": sum(1 for r in rows if not r["refused"] and r["expect_refusal"]),
        "grounded_rate": summarize([1.0 if r["grounded"] else 0.0 for r in rows]),
        # raw SLM hallucination rate (before the verifier) and how often a summary had to be withheld
        "unsupported_claim_rate_raw": summarize([1.0 if r["unverified"] else 0.0 for r in answered]),
        "suppressed_summary_rate": summarize([1.0 if r["suppressed"] else 0.0 for r in answered]),
        "unsupported_claims_surfaced": sum(1 for r in answered if r["unverified"] and not r["suppressed"]),
        "citation_presence": summarize([1.0 if r["cited"] else 0.0 for r in answered]),
        "gold_in_context_rate": summarize([1.0 if r["gold_in_context"] else 0.0 for r in rows if r["gold_in_context"] is not None]),
        "must_contain_rate": summarize([1.0 if r["contains_ok"] else 0.0 for r in answered]),
        "forbidden_content_hits": sum(1 for r in rows if r["forbidden_hit"]),
        "latency_ms": {k: {"p50": pct(num(k), .5), "p95": pct(num(k), .95)}
                       for k in ("retrieval_ms", "rerank_ms", "slm_ms", "total_ms")},
        "tokens": {k: summarize(num(k)) for k in ("prompt_tokens", "completion_tokens", "context_tokens_est")},
        "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 1),  # bytes on macOS
        "model": next((r["model"] for r in rows if r["model"]), None),
    }
    return report, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["retrieval", "e2e"], default="retrieval")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--categories", default="")
    args = parser.parse_args()

    items = [json.loads(l) for l in BENCH.open()]
    if args.categories:
        cats = set(args.categories.split(","))
        items = [i for i in items if i["category"] in cats]
    if args.limit:
        # stratified: take items round-robin across categories
        by_cat = {}
        for it in items:
            by_cat.setdefault(it["category"], []).append(it)
        items, i = [], 0
        while len(items) < args.limit and any(by_cat.values()):
            for c in list(by_cat):
                if by_cat[c] and len(items) < args.limit:
                    items.append(by_cat[c].pop(0))

    if args.mode == "retrieval":
        report, rows = run_retrieval(items, args.k)
    else:
        report, rows = asyncio.run(run_e2e(items))

    RESULTS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = RESULTS / f"{args.mode}-{stamp}.json"
    out.write_text(json.dumps({"report": report, "rows": rows}, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2))
    print(f"[EVAL] details -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
