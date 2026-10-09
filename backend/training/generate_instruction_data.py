"""
Generate grounded instruction data from VERIFIED statute text (data/cleaned/*.sections.jsonl).

Answers are extractive/template-built from the official text: nothing is invented.
Every example carries its context, so the SLM learns to answer FROM evidence and to
refuse when the evidence does not cover the question.

Leakage control:
  - split is by parent section (document-level), hashed deterministically
  - any section used as gold in evaluation/benchmark.jsonl is forced into the test split

Output: data/curated/instructions.jsonl, data/{train,validation,test}/*.jsonl,
        and mlx-lm chat format in data/mlx/{train,valid,test}.jsonl
"""

import hashlib
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "cleaned"
BENCH = ROOT / "evaluation" / "benchmark.jsonl"
DATA = ROOT / "data"
SOURCES = {s["id"]: s for s in json.loads((ROOT / "manifests" / "sources.json").read_text())["sources"]}

import sys
sys.path.insert(0, str(ROOT))
from app.services.grounding import SYSTEM_PROMPT, USER_TEMPLATE, INSUFFICIENT_EVIDENCE_MSG  # noqa: E402

# Target task mix (fractions of total); refusal + citation grounding are kept explicitly
MIX = {"grounded_legal_qa": .30, "statute_extraction": .15, "legal_definition": .10, "penalty_extraction": .10,
       "fact_to_statute": .10, "legal_comparison": .10, "refusal": .10, "citation_grounding": .05}
PUNISH_RE = re.compile(r"(shall be punished with[^.;]*(?:[.;]|$))", re.I)
DEF_RE = re.compile(r"\((\d+)\)\s*“([^”]{2,60})”\s*(means|includes|denotes)\s*([^;]{10,400});")


def unwrap(text):
    return re.sub(r"\s*\n\s*(?!\(\w{1,4}\))", " ", text).strip()


def label(doc, sec):
    src = SOURCES[doc]
    return f"{src['act_name']} - Section {sec['section']}: {sec['title']}"


def ctx_block(i, doc, sec, max_chars=1800):
    return {"id": f"S{i}", "source": SOURCES[doc]["publisher"], "authority": "statute",
            "citation": f"{SOURCES[doc]['act_code']} s.{sec['section']}", "label": label(doc, sec),
            "text": unwrap(sec["text"])[:max_chars]}


def example(task, doc, sec, question, context, answer, citations, difficulty="medium"):
    return {"id": hashlib.sha1(f"{task}|{question}|{answer}".encode()).hexdigest()[:16], "task": task,
            "domain": SOURCES[doc]["legal_domain"], "jurisdiction": "India", "question": question,
            "context": context, "answer": answer, "citations": citations, "difficulty": difficulty,
            "parent_id": f"{doc}:s{sec['section']}"}


def gen_for_section(doc, sec, others, rng):
    act = SOURCES[doc]["act_code"]
    text = unwrap(sec["text"])
    c1 = ctx_block(1, doc, sec)
    cite = f"[S1] {act} Section {sec['section']}"
    out = []

    first = re.split(r"(?<=[.;])\s", text, 1)[0][:500]
    out.append(example("grounded_legal_qa", doc, sec, f"What does Section {sec['section']} of the {act} provide?",
                       [c1], f"Section {sec['section']} of the {SOURCES[doc]['act_name']} ({sec['title']}) provides: "
                       f"\"{first}\" [S1].\n\nSources: {cite}", [cite], "easy"))

    out.append(example("statute_extraction", doc, sec,
                       f"Which section of the supplied context deals with {sec['title'].lower()}?",
                       [ctx_block(1, doc, sec)] + [ctx_block(i + 2, d, s, 600) for i, (d, s) in enumerate(others[:2])],
                       f"{sec['title']} is dealt with in Section {sec['section']} of the {act} [S1].\n\nSources: {cite}",
                       [cite]))

    m = PUNISH_RE.search(text)
    if m:
        out.append(example("penalty_extraction", doc, sec,
                           f"What punishment is prescribed under Section {sec['section']} of the {act}?", [c1],
                           f"Under Section {sec['section']} of the {act}, the offender {m.group(1).strip()} [S1].\n\n"
                           f"Sources: {cite}", [cite]))
        out.append(example("fact_to_statute", doc, sec,
                           f"A person's conduct falls within {sec['title'].lower()}. Which provision applies and what is the punishment?",
                           [c1], f"On the supplied text, Section {sec['section']} of the {act} ({sec['title']}) applies; "
                           f"the offender {m.group(1).strip()} [S1]. Whether the conduct actually satisfies every element "
                           f"of the provision depends on the facts.\n\nSources: {cite}", [cite], "hard"))

    for dm in list(DEF_RE.finditer(text))[:3]:
        term, verb, body = dm.group(2), dm.group(3), dm.group(4).strip()
        out.append(example("legal_definition", doc, sec, f"How does the {act} define \"{term}\"?", [c1],
                           f"Under Section {sec['section']}({dm.group(1)}) of the {act}, \"{term}\" {verb} {body} [S1].\n\n"
                           f"Sources: {cite}", [cite], "easy"))

    if others:
        d2, s2 = others[0]
        c2 = ctx_block(2, d2, s2)
        cite2 = f"[S2] {SOURCES[d2]['act_code']} Section {s2['section']}"
        out.append(example("legal_comparison", doc, sec,
                           f"Compare Section {sec['section']} and Section {s2['section']} of the supplied context.",
                           [c1, c2], f"Section {sec['section']} of the {act} concerns {sec['title'].lower()} [S1], whereas "
                           f"Section {s2['section']} of the {SOURCES[d2]['act_code']} concerns {s2['title'].lower()} [S2]. "
                           f"They address different matters; the supplied text does not state a relationship between them."
                           f"\n\nSources: {cite}; {cite2}", [cite, cite2], "hard"))
        # Refusal: the question asks about this section but only an unrelated one is supplied
        out.append(example("refusal", doc, sec, f"What does Section {sec['section']} of the {act} provide?",
                           [ctx_block(1, d2, s2)], f"{INSUFFICIENT_EVIDENCE_MSG} The supplied context contains "
                           f"Section {s2['section']} of the {SOURCES[d2]['act_code']}, not Section {sec['section']} of the {act}.",
                           [], "medium"))
    out.append(example("citation_grounding", doc, sec,
                       f"Quote the opening words of the provision on {sec['title'].lower()} with its citation.", [c1],
                       f"\"{text[:220].rstrip()}...\" - {act} Section {sec['section']} [S1].\n\nSources: {cite}", [cite], "easy"))
    return out


def split_of(parent_id, test_ids):
    if parent_id in test_ids:
        return "test"
    h = int(hashlib.md5(parent_id.encode()).hexdigest(), 16) % 100
    return "train" if h < 85 else "validation" if h < 93 else "test"


def to_chat(ex):
    context = "\n\n".join(f"[{c['id']}] {c['label']}\n{c['text']}" for c in ex["context"])
    user = USER_TEMPLATE.format(question=ex["question"], context=context, language_note="")
    return {"messages": [{"role": "system", "content": SYSTEM_PROMPT},
                         {"role": "user", "content": user},
                         {"role": "assistant", "content": ex["answer"]}]}


def rebalance(examples, rng):
    """Downsample over-represented tasks toward MIX (never upsample by duplication)."""
    by_task = {}
    for e in examples:
        by_task.setdefault(e["task"], []).append(e)
    # Cap over-represented tasks at their target share; scarce tasks keep everything they have
    total = sum(len(v) for v in by_task.values())
    out = []
    for t, v in by_task.items():
        rng.shuffle(v)
        out += v[: max(1, int(total * MIX.get(t, 0.05)))]
    return out


def main():
    rng = random.Random(13)
    sections = [(p.name.split(".")[0], json.loads(l)) for p in sorted(CLEAN.glob("*.sections.jsonl")) for l in p.open()]
    test_ids = {g for l in BENCH.open() for g in json.loads(l)["gold_parent_ids"]} if BENCH.exists() else set()

    examples = []
    for doc, sec in sections:
        others = rng.sample([x for x in sections if x[1]["section"] != sec["section"] or x[0] != doc], 2)
        examples += gen_for_section(doc, sec, others, rng)
    examples = rebalance(list({e["id"]: e for e in examples}.values()), rng)

    (DATA / "curated").mkdir(parents=True, exist_ok=True)
    (DATA / "mlx").mkdir(parents=True, exist_ok=True)
    with (DATA / "curated" / "instructions.jsonl").open("w") as f:
        for e in examples:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    splits = {"train": [], "validation": [], "test": []}
    for e in examples:
        splits[split_of(e["parent_id"], test_ids)].append(e)
    for name, rows in splits.items():
        (DATA / name).mkdir(exist_ok=True)
        with (DATA / name / "instructions.jsonl").open("w") as f:
            for e in rows:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        mlx_name = {"validation": "valid"}.get(name, name)
        with (DATA / "mlx" / f"{mlx_name}.jsonl").open("w") as f:
            for e in rows:
                f.write(json.dumps(to_chat(e), ensure_ascii=False) + "\n")

    # Leakage check: no parent section appears in more than one split
    parents = {n: {e["parent_id"] for e in r} for n, r in splits.items()}
    assert not (parents["train"] & parents["test"]) and not (parents["train"] & parents["validation"]), "split leakage"
    mix = {}
    for e in examples:
        mix[e["task"]] = mix.get(e["task"], 0) + 1
    print(f"[DATA] {len(examples)} examples; splits={ {k: len(v) for k, v in splits.items()} }; mix={mix}")


if __name__ == "__main__":
    main()
