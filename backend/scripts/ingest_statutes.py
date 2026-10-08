"""
Structure-aware ingestion of official statute PDFs into ChromaDB.

- Parses Gazette / India Code layouts into one record per section (or article),
  keeping marginal-note titles, chapter info and provenance metadata.
- Long sections are split on sub-section boundaries; every chunk keeps the
  parent section metadata so retrieval can filter by act + section.
- Writes cleaned section JSONL to data/cleaned/ and updates manifests/dataset_manifest.json.

Legal text is never rewritten: cleaning only removes page chrome (headers,
rules, margin notes) and normalises whitespace.

Usage: python scripts/ingest_statutes.py [--only BNS_2023] [--reset] [--dry-run]
"""

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RAW_DIR = ROOT / "data" / "raw" / "statutes"
CLEAN_DIR = ROOT / "data" / "cleaned"
SOURCES = ROOT / "manifests" / "sources.json"
FETCH_LOG = ROOT / "manifests" / "fetch_log.json"
DATASET_MANIFEST = ROOT / "manifests" / "dataset_manifest.json"

BODY_X0, BODY_X1 = 112, 480  # Gazette body column; margin notes sit outside it
HEADER_BOTTOM = 78           # running header + rule line
MAX_CHUNK_CHARS = 1800       # ~450 tokens per evidence block

SECTION_RE = re.compile(r"^(\d{1,3}[A-Z]{0,3})\.\s*(.*)$")
INLINE_TITLE_RE = re.compile(r"^([A-Z][^\n]{2,200}?)\.\s*[—–-]{1,2}\s*(.*)$", re.S)
CHAPTER_RE = re.compile(r"^(CHAPTER|PART)\s*([IVXLC]+[A-Z]?)\b\s*(.*)$")
SUBSECTION_SPLIT_RE = re.compile(r"(?=\n\(\d+[A-Z]?\)\s)")
END_RE = re.compile(r"^(—{3,}|_{5,}|SECRETARY TO THE GOVERNMENT|THE SCHEDULE|THE FIRST SCHEDULE)", re.I)
NOISE_LINE_RE = re.compile(r"^(_{5,}|Sec\.\s*\d+\]|\[?Part\s*II|\d+\s+THE GAZETTE OF INDIA)", re.I)


def clean_text(text: str) -> str:
    """Encoding/whitespace normalisation only - legal wording is not altered."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("­", "")  # soft hyphens
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _margin_blocks(words: List[dict]) -> List[Tuple[float, str]]:
    """Group margin-note words into (top, text) blocks."""
    lines: Dict[int, List[dict]] = {}
    for w in words:
        lines.setdefault(round(w["top"]), []).append(w)
    blocks: List[Tuple[float, List[str]]] = []
    last_top = None
    for top in sorted(lines):
        text = " ".join(w["text"] for w in sorted(lines[top], key=lambda w: w["x0"]))
        # Marginal notes end with a period; a new note starts after one
        if last_top is not None and top - last_top <= 14 and not blocks[-1][1][-1].endswith("."):
            blocks[-1][1].append(text)
        else:
            blocks.append((top, [text]))
        last_top = top
    return [(top, " ".join(parts)) for top, parts in blocks]


def extract_lines(pdf_path: Path) -> Tuple[List[dict], List[Tuple[int, float, str]]]:
    """Return body lines [{text, page, top}] and margin notes [(page, top, text)]."""
    import pdfplumber

    body, margins = [], []
    with pdfplumber.open(pdf_path) as pdf:
        for pno, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(x_tolerance=1.2)
            margin_words = [w for w in words if w["top"] > HEADER_BOTTOM
                            and (w["x1"] <= BODY_X0 or w["x0"] >= BODY_X1)]
            margins += [(pno, top, txt) for top, txt in _margin_blocks(margin_words)]
            crop = page.within_bbox((BODY_X0, HEADER_BOTTOM, min(BODY_X1, page.width), page.height))
            for line in crop.extract_text_lines(x_tolerance=1.2):
                text = line["text"].strip()
                if text and not NOISE_LINE_RE.match(text) and re.search(r"\w", text):
                    body.append({"text": text, "page": pno, "top": line["top"]})
    return body, margins


def parse_sections(body: List[dict], margins: List[Tuple[int, float, str]]) -> List[dict]:
    """Split body lines into sections using sequential numbering and attach titles."""
    sections: List[dict] = []
    chapter = chapter_title = ""
    pending_chapter_title = False
    expected = 1

    for line in body:
        text = line["text"]
        if sections and END_RE.match(text):
            break
        m_ch = CHAPTER_RE.match(text)
        if m_ch:
            chapter, chapter_title = m_ch.group(2), m_ch.group(3).strip()
            pending_chapter_title = not chapter_title
            continue
        if pending_chapter_title and text.isupper():
            chapter_title = text.title()
            pending_chapter_title = False
            continue
        pending_chapter_title = False

        m = SECTION_RE.match(text)
        if m:
            num = m.group(1)
            base = int(re.match(r"\d+", num).group())
            # Accept the next section number (tolerating one missed heading) or lettered insertions (111A)
            if expected <= base <= expected + 1 or (base == expected - 1 and num[-1].isalpha()):
                sections.append({
                    "section": num, "chapter": chapter, "chapter_title": chapter_title,
                    "page": line["page"], "top": line["top"], "lines": [m.group(2)],
                })
                expected = base + 1
                continue
        if sections:
            sections[-1]["lines"].append(text)

    for sec in sections:
        text = clean_text("\n".join(sec.pop("lines")))
        title = ""
        page_notes = [(abs(top - sec["top"]), note) for p, top, note in margins
                      if p == sec["page"] and abs(top - sec["top"]) <= 12]
        if page_notes:
            title = min(page_notes)[1]
        else:
            m_inline = INLINE_TITLE_RE.match(text)
            if m_inline and len(m_inline.group(1)) < 160:
                title, text = m_inline.group(1), m_inline.group(2)
        sec["title"] = clean_text(title).rstrip(".")
        sec["text"] = text
        del sec["top"]
    return [s for s in sections if len(s["text"]) > 20]


def split_section(text: str) -> List[str]:
    """Split long sections at sub-section markers, packing up to MAX_CHUNK_CHARS."""
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]
    parts = [p.strip() for p in SUBSECTION_SPLIT_RE.split("\n" + text) if p.strip()]
    chunks, current = [], ""
    for part in parts:
        while len(part) > MAX_CHUNK_CHARS:  # very long clause: split on sentence boundary
            cut = part.rfind(". ", 0, MAX_CHUNK_CHARS)
            cut = cut + 1 if cut > 200 else MAX_CHUNK_CHARS
            if current:
                chunks.append(current)
                current = ""
            chunks.append(part[:cut].strip())
            part = part[cut:].strip()
        if current and len(current) + len(part) + 1 > MAX_CHUNK_CHARS:
            chunks.append(current)
            current = part
        else:
            current = f"{current}\n{part}".strip()
    if current:
        chunks.append(current)
    return chunks


def build_records(source: dict, sections: List[dict], resolved_url: str) -> List[dict]:
    unit = "article" if source.get("document_type") == "constitution" else "section"
    records = []
    for sec in sections:
        parent = f"{source['id']}:{unit[0]}{sec['section']}"
        chunks = split_section(sec["text"])
        for i, chunk in enumerate(chunks):
            records.append({
                "id": f"{parent}:c{i}",
                "text": chunk,
                "metadata": {
                    "document_id": source["id"],
                    "parent_document_id": parent,
                    "chunk_id": f"{parent}:c{i}",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "source": source["publisher"],
                    "source_url": resolved_url or source["url"],
                    "authority_level": source["authority_level"],
                    "document_type": source["document_type"],
                    "act_name": source["act_name"],
                    "act_code": source["act_code"],
                    unit: sec["section"],
                    "section_title": sec["title"],
                    "chapter": sec["chapter"],
                    "chapter_title": sec["chapter_title"],
                    "legal_domain": source["legal_domain"],
                    "domain": source["legal_domain"],
                    "jurisdiction": "India",
                    "language": "en",
                    "effective_date": source.get("effective_date", ""),
                    "status": source.get("status", "in force"),
                    "page": sec["page"],
                },
            })
    return records


def embed_text(rec: dict) -> str:
    m = rec["metadata"]
    unit = f"Article {m['article']}" if "article" in m else f"Section {m['section']}"
    return f"{m['act_name']} ({m['act_code']}) {unit}: {m['section_title']}\n{rec['text']}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="")
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild the collection")
    parser.add_argument("--dry-run", action="store_true", help="Parse only; no embedding/indexing")
    args = parser.parse_args()
    only = {s for s in args.only.split(",") if s}

    sources = json.loads(SOURCES.read_text())["sources"]
    fetch_log = json.loads(FETCH_LOG.read_text()) if FETCH_LOG.exists() else {}
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    collection = embedder = None
    if not args.dry_run:
        import chromadb
        from app.config import settings
        from app.services.embedding_service import get_embedding_service

        embedder = get_embedding_service()
        client = chromadb.PersistentClient(path=str(ROOT / settings.chroma_persist_dir.lstrip("./")))
        if args.reset:
            try:
                client.delete_collection(settings.rag_collection)
            except Exception:
                pass
        collection = client.get_or_create_collection(
            settings.rag_collection,
            metadata={"hnsw:space": "cosine", "embedding_model": embedder.model_name,
                      "embedding_dimension": str(embedder.get_embedding_dimension())},
        )
        index_model = (collection.metadata or {}).get("embedding_model")
        if index_model and index_model != embedder.model_name:
            sys.exit(f"Index built with {index_model}, current embedder is {embedder.model_name}. Use --reset.")

    manifest = json.loads(DATASET_MANIFEST.read_text()) if DATASET_MANIFEST.exists() else {"datasets": {}}
    for source in sources:
        if only and source["id"] not in only:
            continue
        pdf_path = RAW_DIR / f"{source['id']}.pdf"
        if not pdf_path.exists():
            print(f"[INGEST] {source['id']}: missing {pdf_path.name}, skipped")
            continue

        body, margins = extract_lines(pdf_path)
        sections = parse_sections(body, margins)
        resolved_url = fetch_log.get(source["id"], {}).get("resolved_url", "")
        records = build_records(source, sections, resolved_url)
        nums = [s["section"] for s in sections]
        untitled = sum(1 for s in sections if not s["title"])
        print(f"[INGEST] {source['id']}: {len(sections)} sections ({nums[:1]}..{nums[-1:]}), "
              f"{len(records)} chunks, {untitled} without title")

        with open(CLEAN_DIR / f"{source['id']}.sections.jsonl", "w") as f:
            for s in sections:
                f.write(json.dumps({"document_id": source["id"], **s}, ensure_ascii=False) + "\n")

        if collection is not None:
            for i in range(0, len(records), 32):
                batch = records[i:i + 32]
                vectors = embedder.embed_documents([embed_text(r) for r in batch])
                collection.upsert(
                    ids=[r["id"] for r in batch],
                    documents=[r["text"] for r in batch],
                    metadatas=[r["metadata"] for r in batch],
                    embeddings=[v.tolist() for v in vectors],
                )
            print(f"[INGEST] {source['id']}: indexed; collection size {collection.count()}")

        manifest["datasets"][source["id"]] = {
            "dataset_name": source["act_name"],
            "source": source["publisher"],
            "url": resolved_url or source["url"],
            "sha256": fetch_log.get(source["id"], {}).get("sha256"),
            "license": "Government of India legislative text (public document; reuse per Government Open Data / India Code terms)",
            "jurisdiction": "India",
            "document_type": source["document_type"],
            "authority_level": source["authority_level"],
            "date_range": source.get("effective_date", ""),
            "number_of_records": {"sections": len(sections), "chunks": len(records)},
            "preprocessing_method": "pdfplumber layout extraction; page chrome + margin notes separated; "
                                    "NFKC/whitespace normalisation only; split per section, sub-section packing <=1800 chars",
            "intended_use": "RAG retrieval (source of truth); grounded instruction-data generation",
            "train_eval_role": "retrieval corpus (not raw training text)",
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
    DATASET_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
