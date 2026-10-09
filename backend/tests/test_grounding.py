"""Unit tests for context compression and citation verification (no models required)."""

from app.services import grounding


def _ev(section, text, title="Punishment for murder", act="BNS", chunk=0, score=0.9):
    return {
        "id": f"BNS_2023:s{section}:c{chunk}",
        "content": text,
        "rerank_score": score,
        "metadata": {
            "act_code": act, "act_name": "Bharatiya Nyaya Sanhita, 2023", "section": section,
            "section_title": title, "parent_document_id": f"BNS_2023:s{section}", "chunk_index": chunk,
            "source": "India Code", "source_url": "https://example.gov.in/bns.pdf", "status": "in force",
        },
    }


S103 = ("(1) Whoever commits murder shall be punished with death or imprisonment for life, "
        "and shall also be liable to fine.")


def test_build_context_tags_sources_and_merges_siblings():
    evidence = [_ev("103", S103), _ev("103", "(2) When a group of five or more persons ...", chunk=1)]
    text, sources = grounding.build_context("punishment for murder", evidence)
    assert len(sources) == 1  # sibling chunks merged into one block
    assert text.startswith("[S1] Bharatiya Nyaya Sanhita, 2023 - Section 103: Punishment for murder")
    assert "five or more persons" in text


def test_compression_respects_budget_and_keeps_relevant_clause():
    filler = " ".join(f"Clause {i} concerns unrelated procedural matters." for i in range(400))
    body = "Whoever commits murder shall be punished with death. " + filler + " Murder of a child is punishable."
    out = grounding._compress(body, {"murder", "child"}, 600)
    assert len(out) <= 800
    assert out.startswith("Whoever commits murder")
    assert "child" in out


def test_verify_accepts_supported_answer():
    _, sources = grounding.build_context("murder", [_ev("103", S103)])
    ans = "Under Section 103 of the BNS, murder is punishable with death or imprisonment for life [S1]."
    v = grounding.verify_citations(ans, sources)
    assert v["grounded"] and v["cited_sources"] == ["S1"] and not v["unverified_references"]


def test_verify_flags_invented_section_case_and_source():
    _, sources = grounding.build_context("murder", [_ev("103", S103)])
    ans = ("Section 302 IPC applies, see Bachan Singh v. State of Punjab [S4], "
           "punishable with seven years [S1].")
    v = grounding.verify_citations(ans, sources)
    assert not v["grounded"]
    flagged = " ".join(v["unverified_references"])
    assert "Section 302 IPC" in flagged
    assert "Bachan Singh v. State" in flagged
    assert "seven years" in flagged
    assert "[S4]" in flagged


def test_verify_wrong_act_for_known_section_number():
    _, sources = grounding.build_context("murder", [_ev("103", S103)])
    v = grounding.verify_citations("Section 103 of the BNSS covers this [S1].", sources)
    assert "Section 103 BNSS" in v["unverified_references"]


def test_refusal_is_grounded_without_citations():
    v = grounding.verify_citations(
        "The available sources are insufficient to answer this question.", [])
    assert v["refusal"] and v["grounded"]
    assert grounding.confidence_level(v, []) == "low"


def test_prompt_is_compact_and_deterministic():
    msgs = grounding.build_messages("What is Section 103 BNS?", "[S1] ...", "en")
    assert msgs[0]["role"] == "system" and len(msgs[0]["content"]) < 800
    assert "REQUIRED OUTPUT" in msgs[1]["content"]
    assert grounding.build_messages("q", "c") == grounding.build_messages("q", "c")


def test_claim_checked_against_the_source_it_cites():
    """'ten-year' cited to s.103 must fail even though another retrieved section mentions ten years."""
    ev = [_ev("103", S103), _ev("105", "shall be punished with imprisonment for a term which may extend to ten years",
                                 title="Punishment for culpable homicide")]
    _, sources = grounding.build_context("murder", ev)
    v = grounding.verify_citations("Murder carries a ten-year maximum [S1].", sources)
    assert "ten years" in v["unverified_references"]
    v2 = grounding.verify_citations("Culpable homicide may extend to ten years [S2].", sources)
    assert v2["grounded"]


def test_loose_citation_forms_are_recognised():
    _, sources = grounding.build_context("murder", [_ev("103", S103)])
    v = grounding.verify_citations("Murder is punishable with death [Source: Section 103, S1].", sources)
    assert v["cited_sources"] == ["S1"] and v["grounded"]


def test_dedupe_sentences_removes_loops():
    looped = "Answer: X applies [S1]. " + "[S2] applies harsher terms if a life convict re-offends. " * 5
    out = grounding.dedupe_sentences(looped)
    assert out.count("harsher terms") == 1 and out.startswith("Answer: X applies")
