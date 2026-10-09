"""
NyayaShastra - Grounding layer between retrieval and the legal SLM.

1. Context compression: merge sibling chunks, keep query-relevant clauses,
   enforce an explicit token budget, tag every block with a source id [S#].
2. Deterministic, compact prompt.
3. Citation verification: every [S#], section/article, case name and term of
   years in the answer must be traceable to retrieved evidence.
"""

import re
from typing import List, Dict, Any, Tuple

from app.config import settings

INSUFFICIENT_EVIDENCE_MSG = (
    "I do not have sufficient authoritative legal material in the retrieved sources "
    "to answer this reliably."
)

SYSTEM_PROMPT = """You are NyayShastra, an Indian legal information assistant.
Answer only from the supplied authoritative legal context.
Do not invent statutes, sections, cases, citations, penalties, dates, or legal rules.
When the context is insufficient, explicitly say that the available sources are insufficient.
Distinguish clearly between statutory text, judicial interpretation, and inference.
Cite the supplied source identifiers (e.g. [S1]) for every legal claim.
Explain the answer clearly and concisely. Do not provide unsupported legal conclusions."""

USER_TEMPLATE = """QUESTION:
{question}

AUTHORITATIVE CONTEXT:
{context}

REQUIRED OUTPUT:
1. Answer
2. Relevant law
3. Application/explanation
4. Sources (the [S#] identifiers used)
Quote the context's exact words for penalties, terms and conditions; cite [S#] after each claim.{language_note}"""

ACT_ALIASES = {
    "BNS": ["bns", "bharatiya nyaya sanhita", "nyaya sanhita"],
    "BNSS": ["bnss", "bharatiya nagarik suraksha sanhita", "nagarik suraksha"],
    "BSA": ["bsa", "bharatiya sakshya adhiniyam", "sakshya adhiniyam"],
    "IPC": ["ipc", "indian penal code", "penal code"],
    "CrPC": ["crpc", "cr.p.c", "code of criminal procedure"],
    "IEA": ["iea", "indian evidence act", "evidence act"],
    "COI": ["constitution"],
}

_CLAUSE_SPLIT = re.compile(r"(?<=[.;:])\s+(?=[A-Z(])|\n(?=\(\w{1,4}\)\s)")
_WORD = re.compile(r"[a-z]{3,}")
_STOP = {"the", "and", "for", "with", "shall", "any", "such", "which", "under", "what",
         "this", "that", "who", "whoever", "section", "person", "may", "not", "from", "been"}


def estimate_tokens(text: str) -> int:
    """Cheap token estimate (~4 chars/token for English legal text on Qwen tokenizer)."""
    return max(1, len(text) // 4)


def _label(meta: Dict[str, Any]) -> str:
    unit = f"Article {meta['article']}" if meta.get("article") else f"Section {meta.get('section', '?')}"
    title = f": {meta['section_title']}" if meta.get("section_title") else ""
    return f"{meta.get('act_name', meta.get('act_code', 'Source'))} - {unit}{title}"


def _compress(text: str, query_terms: set, budget_chars: int) -> str:
    """Keep the opening clause plus the clauses most relevant to the query, in original order."""
    text = re.sub(r"[ \t]*\n[ \t]*(?!\(\w{1,4}\))", " ", text).strip()  # unwrap PDF line breaks
    if len(text) <= budget_chars:
        return text
    clauses = [c.strip() for c in _CLAUSE_SPLIT.split(text) if c.strip()]
    scored = [(len(query_terms & set(_WORD.findall(c.lower()))), i) for i, c in enumerate(clauses)]
    keep, used = {0}, len(clauses[0])
    for score, i in sorted(scored, key=lambda x: (-x[0], x[1])):
        if i in keep or score == 0:
            continue
        if used + len(clauses[i]) > budget_chars:
            continue
        keep.add(i)
        used += len(clauses[i])
    out, prev = [], -1
    for i in sorted(keep):
        if prev != -1 and i != prev + 1:
            out.append("[...]")
        out.append(clauses[i])
        prev = i
    return " ".join(out)[: budget_chars + 200]


def build_context(query: str, evidence: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """Return (context_text, sources). Sibling chunks of a section are merged into one block."""
    blocks: Dict[str, Dict[str, Any]] = {}
    for ev in evidence:
        meta = ev.get("metadata", {})
        key = meta.get("parent_document_id") or ev["id"]
        if key in blocks:
            blocks[key]["texts"].append((meta.get("chunk_index", 0), ev["content"]))
        else:
            blocks[key] = {"meta": meta, "texts": [(meta.get("chunk_index", 0), ev["content"])],
                           "score": ev.get("rerank_score"), "id": ev["id"]}

    budget_chars = settings.rag_context_token_budget * 4
    per_block = max(600, budget_chars // max(1, len(blocks)))
    query_terms = set(_WORD.findall(query.lower())) - _STOP

    lines, sources = [], []
    for n, block in enumerate(blocks.values(), start=1):
        sid = f"S{n}"
        meta = block["meta"]
        text = " ".join(t for _, t in sorted(block["texts"]))
        body = _compress(text, query_terms, per_block)
        status = f" | status: {meta['status']}" if meta.get("status") and meta["status"] != "in force" else ""
        lines.append(f"[{sid}] {_label(meta)}{status}\n{body}")
        sources.append({
            "id": sid,
            "label": _label(meta),
            "act_name": meta.get("act_name"),
            "act_code": meta.get("act_code"),
            "section": meta.get("section"),
            "article": meta.get("article"),
            "section_title": meta.get("section_title"),
            "document_type": meta.get("document_type"),
            "authority_level": meta.get("authority_level"),
            "status": meta.get("status"),
            "source": meta.get("source"),
            "url": meta.get("source_url"),
            "chunk_id": block["id"],
            "relevance": block["score"],
            "text": text,
        })
    return "\n\n".join(lines), sources


def build_messages(query: str, context_text: str, language: str = "en") -> List[Dict[str, str]]:
    language_note = "\nWrite the entire answer in Hindi." if language == "hi" else ""
    user = USER_TEMPLATE.format(question=query[:1024], context=context_text, language_note=language_note)
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


# ---------------------------------------------------------------- verification
_BRACKET_RE = re.compile(r"\[([^\[\]]{1,80})\]")
_SID_IN_GROUP_RE = re.compile(r"\b(S\d+)\b")
# Sentence boundaries, but not after legal abbreviations ("v.", "s.", "Sec.", "No.", "Art.")
_SENTENCE_RE = re.compile(r"(?<!\bv\.)(?<!\bvs\.)(?<!\bs\.)(?<!\bSec\.)(?<!\bNo\.)(?<!\bArt\.)(?<=[.!?])\s+|\n+")
_SECTION_REF_RE = re.compile(
    r"\b(?:section|sec\.|s\.)\s*(\d{1,3}[A-Z]{0,2})(?:\s*\(\w+\))*"
    r"(?:\s*(?:of|,)?\s*(?:the\s+)?([A-Za-z.\s]{0,45}?(?:sanhita|adhiniyam|code|act|bns|bnss|bsa|ipc|crpc)))?\b",
    re.IGNORECASE,
)
_ARTICLE_REF_RE = re.compile(r"\barticle\s*(\d{1,3}[A-Z]{0,2})\b", re.IGNORECASE)
_CASE_RE = re.compile(r"\b([A-Z][\w.&']+(?:\s+[A-Z][\w.&']+){0,5})\s+(?:v\.|vs\.?|versus)\s+([A-Z][\w.&']+(?:\s+[A-Z][\w.&']+){0,5})")
_YEARS_RE = re.compile(r"\b(\w+)[\s-]+years?\b", re.IGNORECASE)
_NUM_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
              "eleven", "twelve", "fourteen", "twenty", "thirty"}
_REFUSAL_RE = re.compile(r"(insufficient|not sufficient|do not have sufficient|cannot verify|"
                         r"not (?:contain|mention|available) in the (?:supplied|provided|retrieved))", re.I)


def _act_code(name: str) -> str:
    low = (name or "").lower()
    for code, aliases in ACT_ALIASES.items():  # word boundaries: "bns" must not match "bnss"
        if any(re.search(rf"\b{re.escape(a)}\b", low) for a in aliases):
            return code
    return ""


def _cited_ids(text: str) -> List[str]:
    """Source ids in any bracketed form: [S1], [S1, S3], [Source: Section 103, S1]."""
    ids = []
    for group in _BRACKET_RE.findall(text):
        ids += _SID_IN_GROUP_RE.findall(group)
    return ids


def verify_citations(answer: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check legal references sentence by sentence against the sources each sentence cites.

    A sentence with citations is checked against those sources only; an uncited sentence
    is checked against all retrieved evidence.
    """
    by_id = {s["id"]: s for s in sources}
    all_text = " ".join(s["text"] for s in sources).lower()
    cited_all: List[str] = []
    verified, unverified = [], []

    for sentence in _SENTENCE_RE.split(answer):
        ids = _cited_ids(sentence)
        cited_all += ids
        scope = [by_id[i] for i in ids if i in by_id] or sources
        text = " ".join(s["text"] for s in scope).lower() if ids else all_text
        sections = {(s.get("act_code"), (s.get("section") or "").upper()) for s in scope if s.get("section")}
        articles = {(s.get("article") or "").upper() for s in scope if s.get("article")}

        for m in _SECTION_REF_RE.finditer(sentence):
            num, act = m.group(1).upper(), _act_code(m.group(2) or "")
            ref = f"Section {num}" + (f" {act}" if act else "")
            in_meta = any(sec == num and (not act or code == act) for code, sec in sections)
            in_text = f"section {num.lower()}" in text
            (verified if in_meta or (in_text and not act) else unverified).append(ref)

        for m in _ARTICLE_REF_RE.finditer(sentence):
            num = m.group(1).upper()
            ok = num in articles or f"article {num.lower()}" in text
            (verified if ok else unverified).append(f"Article {num}")

        for m in _CASE_RE.finditer(sentence):
            name = f"{m.group(1)} v. {m.group(2)}"
            ok = m.group(1).lower() in all_text and m.group(2).lower() in all_text
            (verified if ok else unverified).append(name)

        for m in _YEARS_RE.finditer(sentence):
            qty = m.group(1).lower()
            if qty.isdigit() or qty in _NUM_WORDS:
                ok = re.search(rf"\b{qty}[\s-]+years?\b", text) is not None
                (verified if ok else unverified).append(f"{qty} years")

    cited = sorted(set(cited_all), key=lambda x: int(x[1:]))
    unverified += [f"[{c}] (not a retrieved source)" for c in cited if c not in by_id]
    refusal = bool(_REFUSAL_RE.search(answer))
    grounded = not unverified and (bool(cited) or refusal)
    return {
        "grounded": grounded,
        "refusal": refusal,
        "cited_sources": [c for c in cited if c in by_id],
        "verified_references": sorted(set(verified)),
        "unverified_references": sorted(set(unverified)),
    }


def confidence_level(verification: Dict[str, Any], sources: List[Dict[str, Any]]) -> str:
    if verification["refusal"] or not sources:
        return "low"
    top = max((s.get("relevance") or 0) for s in sources)
    if verification["grounded"] and top >= 0.5:
        return "high"
    if verification["grounded"] or (not verification["unverified_references"] and top >= 0.3):
        return "medium"
    return "low"


def format_sources_footer(sources: List[Dict[str, Any]], cited: List[str]) -> str:
    """Deterministic source list built from retrieval metadata (never from model output)."""
    used = [s for s in sources if s["id"] in cited] or sources
    lines = ["\n\n**Retrieved sources**"]
    for s in used:
        status = f" ({s['status']})" if s.get("status") and s["status"] != "in force" else ""
        url = f" - {s['url']}" if s.get("url") else ""
        lines.append(f"- [{s['id']}] {s['label']}{status}{url}")
    return "\n".join(lines)


def dedupe_sentences(answer: str) -> str:
    """Drop verbatim repeated sentences (small models can loop near the token limit)."""
    seen, out = set(), []
    for line in answer.split("\n"):
        kept = []
        for sent in _SENTENCE_RE.split(line):
            key = re.sub(r"\W+", " ", sent).strip().lower()
            if key and key in seen and len(key) > 20:
                continue
            seen.add(key)
            kept.append(sent)
        out.append(" ".join(kept))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def extractive_answer(sources: List[Dict[str, Any]], max_sources: int = 2, max_chars: int = 700) -> str:
    """Verbatim statutory text of the top sources - used when a generated summary fails verification."""
    parts = ["The AI summary was withheld because it could not be fully verified against the retrieved "
             "law. The relevant statutory text is:"]
    for s in sources[:max_sources]:
        text = re.sub(r"\s+", " ", s["text"]).strip()
        parts.append(f"\n**[{s['id']}] {s['label']}**\n> {text[:max_chars]}{'...' if len(text) > max_chars else ''}")
    return "\n".join(parts)


def statutory_excerpt(source: Dict[str, Any], max_chars: int = 500) -> str:
    text = re.sub(r"\s+", " ", source["text"]).strip()
    return (f"\n\n**Statutory text [{source['id']}] {source['label']}**\n> "
            f"{text[:max_chars]}{'...' if len(text) > max_chars else ''}")
