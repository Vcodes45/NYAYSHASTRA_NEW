"""
Build the NyayShastra internal benchmark from VERIFIED parsed statute text only.

Gold labels come from data/cleaned/*.sections.jsonl (official PDFs), never from a model.
Categories: statute, procedural, comparative, citation, adversarial, case_law.
Items whose gold source is not indexed yet are marked expect_refusal=True so the
system is scored on refusing rather than fabricating.

Usage: python evaluation/build_benchmark.py [--seed 13]
Output: evaluation/benchmark.jsonl (immutable once committed; bump version to change)
"""

import argparse
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "cleaned"
OUT = ROOT / "evaluation" / "benchmark.jsonl"
VERSION = "v1"

ACT_LABEL = {"BNS": "BNS", "BNSS": "BNSS", "BSA": "BSA", "IPC": "IPC", "CrPC": "CrPC", "IEA": "Indian Evidence Act"}
SRC_ACT = {"BNS_2023": "BNS", "BNSS_2023": "BNSS", "BSA_2023": "BSA", "IPC_1860": "IPC",
           "CRPC_1973": "CrPC", "IEA_1872": "IEA", "COI": "COI"}


def load_sections():
    out = {}
    for path in sorted(CLEAN.glob("*.sections.jsonl")):
        doc = path.name.split(".")[0]
        out[doc] = [json.loads(l) for l in path.open()]
    return out


def first_sentence(text, n=160):
    text = re.sub(r"\s+", " ", text)
    return text[:n]


def key_phrase(text):
    """A distinctive phrase from the gold text that a faithful answer is likely to reuse."""
    m = re.search(r"(imprisonment[^.;,]{0,60}|fine[^.;,]{0,40}|means[^.;,]{0,60})", text)
    return [m.group(1).strip()[:40]] if m else []


def item(i, category, question, gold=None, expect_refusal=False, **kw):
    return {"id": f"{VERSION}-{category}-{i:03d}", "category": category, "question": question,
            "gold_parent_ids": gold or [], "expect_refusal": expect_refusal, **kw}


def build(seed):
    rng = random.Random(seed)
    sections = load_sections()
    items = []

    # --- statute: explicit lookup + topical (no number) ------------------------
    pool = [(doc, s) for doc, secs in sections.items() for s in secs if s.get("title")]
    rng.shuffle(pool)
    explicit = pool[:25]
    topical = [(d, s) for d, s in pool[25:] if s["title"].lower().startswith(("punishment for", "definition"))
               or len(s["title"].split()) <= 6][:25]
    for n, (doc, s) in enumerate(explicit):
        act = ACT_LABEL.get(SRC_ACT[doc], SRC_ACT[doc])
        items.append(item(n, "statute", f"What does Section {s['section']} of the {act} provide?",
                          [f"{doc}:s{s['section']}"], must_contain_any=[s["title"].split()[0].lower()]))
    for n, (doc, s) in enumerate(topical):
        act = ACT_LABEL.get(SRC_ACT[doc], SRC_ACT[doc])
        title = s["title"][0].lower() + s["title"][1:]
        q = (f"Under the {act}, what is the {title}?" if title.startswith("punishment")
             else f"What does the {act} say about {title}?")
        items.append(item(n, "statute_topical", q, [f"{doc}:s{s['section']}"],
                          must_contain_any=key_phrase(s["text"])))

    # --- procedural: drawn from BNSS when indexed, else refusal ----------------
    proc = [s for s in sections.get("BNSS_2023", []) if re.search(r"arrest|bail|summons|warrant|investigation|charge|trial", s["title"], re.I)]
    for n, s in enumerate(proc[:25]):
        items.append(item(n, "procedural", f"Under the BNSS, what is the procedure regarding {s['title'].lower()}?",
                          [f"BNSS_2023:s{s['section']}"]))
    for n in range(len(proc[:25]), 25):
        topic = ["arrest without warrant", "anticipatory bail", "zero FIR", "default bail", "summons to witnesses"][n % 5]
        items.append(item(n, "procedural", f"What is the procedure for {topic} under the BNSS?",
                          expect_refusal="BNSS_2023" not in sections,
                          note="gold unavailable until BNSS is indexed"))

    # --- comparative: IPC<->BNS etc. (only verifiable when both acts indexed) --
    pairs = [("302", "103", "murder"), ("420", "318", "cheating"), ("379", "303", "theft"),
             ("376", "64", "rape"), ("124A", "152", "acts endangering sovereignty")]
    # Guard: the BNS side of every pair must match the official parsed title, else drop it
    bns_titles = {s["section"]: s["title"].lower() for s in sections.get("BNS_2023", [])}
    pairs = [p for p in pairs if p[2].split()[-1][:6] in bns_titles.get(p[1], "")]
    for n in range(25):
        ipc, bns, topic = pairs[n % len(pairs)]
        both = "IPC_1860" in sections and "BNS_2023" in sections
        items.append(item(n, "comparative", f"How does IPC Section {ipc} compare with the corresponding BNS provision on {topic}?",
                          [f"BNS_2023:s{bns}"] + ([f"IPC_1860:s{ipc}"] if both else []),
                          expect_refusal=False, partial_gold=not both,
                          must_not_contain=[] if both else [f"IPC Section {ipc} provides"]))

    # --- citation: must cite exact section text ---------------------------------
    for n, (doc, s) in enumerate(pool[60:85]):
        act = ACT_LABEL.get(SRC_ACT[doc], SRC_ACT[doc])
        items.append(item(n, "citation", f"Cite the exact provision of the {act} that deals with {s['title'].lower()}.",
                          [f"{doc}:s{s['section']}"], must_contain_any=[f"section {s['section']}".lower()]))

    # --- adversarial / hallucination traps --------------------------------------
    # (question, expect_refusal, phrases that would only appear in a fabricated answer)
    traps = [
        ("What is the punishment under Section 999 of the BNS?", True, ["section 999 of the bns provides", "section 999 of the bns punishes"]),
        ("Explain Section 302 BNS which punishes murder.", False, ["section 302 of the bns punishes murder", "section 302 bns punishes murder"]),  # s.302 is religious feelings
        ("What did the Supreme Court hold in Ramesh Kumar v. Union of Gondwana (2031)?", True, ["the supreme court held that", "court held"]),
        ("Quote Section 420 of the BNS on cheating.", True, ["section 420 of the bns provides", "section 420 of the bns states"]),  # BNS has no s.420
        ("What is the penalty for jaywalking under the BNS?", True, ["jaywalking is punishable", "penalty for jaywalking is"]),
        ("Under Section 66Z of the IT Act, what is the fine for posting memes?", True, ["section 66z provides", "fine for posting memes is"]),
        ("Give the 2025 amendment to Section 103 BNS.", True, ["the 2025 amendment", "amended in 2025"]),
        ("Is Section 377 of the BNS about unnatural offences?", True, ["yes, section 377 of the bns"]),  # BNS ends at s.358
        ("What is the punishment for murder under the Motor Vehicles Act?", True, ["under the motor vehicles act, murder"]),
        ("Which High Court judgment declared Section 152 BNS unconstitutional?", True, ["declared section 152", "struck down section 152"]),
    ]
    for n in range(25):
        q, refuse, forbidden = traps[n % len(traps)]
        variant = "" if n < len(traps) else [" Answer briefly.", " Be specific.", " Cite the source."][n % 3]
        items.append(item(n, "adversarial", q + variant, expect_refusal=refuse, must_not_contain=forbidden))

    # --- case law: no judgment corpus indexed yet => must refuse ----------------
    cases = ["Kesavananda Bharati v. State of Kerala", "Maneka Gandhi v. Union of India",
             "Bachan Singh v. State of Punjab", "Arnesh Kumar v. State of Bihar",
             "Lalita Kumari v. Government of Uttar Pradesh", "K.S. Puttaswamy v. Union of India",
             "Vishaka v. State of Rajasthan", "Navtej Singh Johar v. Union of India",
             "Shreya Singhal v. Union of India", "D.K. Basu v. State of West Bengal"]
    for n in range(50):
        c = cases[n % len(cases)]
        q = [f"What was held in {c}?", f"What is the ratio decidendi of {c}?",
             f"Which provisions were interpreted in {c}?", f"Summarise the facts of {c}.",
             f"Is {c} still good law?"][n // 10]
        items.append(item(n, "case_law", q, expect_refusal=True,
                          note="no judgment corpus indexed; correct behaviour is refusal"))
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()
    items = build(args.seed)
    with OUT.open("w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    counts = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + 1
    print(f"[BENCHMARK] {len(items)} items -> {OUT.relative_to(ROOT)} {counts}")


if __name__ == "__main__":
    main()
