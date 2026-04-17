from pipeline.inference import (
    build_no_answer_response,
    build_prompt,
    ensure_structured_sections,
)
from pipeline.retriever import CandidateChunk, RetrievalResult


def make_result(should_answer=True):
    candidate = CandidateChunk(
        chunk_key="pp16-1",
        content="Pasal 1 Bangunan Gedung wajib memenuhi persyaratan administratif.",
        metadata={"source_name": "PP 16/2021", "start_page": 1, "end_page": 1},
        score=0.92,
        source="reranked",
    )
    return RetrievalResult(
        question="Apa syarat PBG?",
        standalone_query="Apa syarat PBG?",
        expanded_queries=["Apa syarat PBG?"],
        filters={"region": "Semarang"},
        candidates=[candidate],
        should_answer=should_answer,
        confidence=0.92 if should_answer else 0.2,
        message="Arsitrad tidak dapat menemukan regulasi yang cukup spesifik.",
    )


def test_build_prompt_includes_question_and_citations():
    prompt = build_prompt("Apa syarat PBG?", make_result())

    assert "KONTEKS REGULASI" in prompt
    assert "PERTANYAAN: Apa syarat PBG?" in prompt
    assert "[1]" in prompt


def test_no_answer_response_is_structured():
    response = build_no_answer_response(make_result(should_answer=False))

    assert "RINGKASAN" in response
    assert "DETAIL REGULASI" in response
    assert "SUMBER" in response


def test_ensure_structured_sections_wraps_plain_text():
    response = ensure_structured_sections("Jawaban singkat saja.", make_result().candidates)

    assert "RINGKASAN" in response
    assert "SUMBER" in response
