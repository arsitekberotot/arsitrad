from pipeline.conversation_memory import contextualize_question, needs_contextualization


def test_contextualize_question_rewrites_followup():
    history = [{"role": "user", "content": "Berapa KDB maksimal untuk area komersial?"}]
    rewritten = contextualize_question("Bagaimana kalau dekat sungai?", history)

    assert "KDB maksimal" in rewritten
    assert "dekat sungai" in rewritten


def test_needs_contextualization_detects_short_followup():
    assert needs_contextualization("Kalau di Semarang?") is True
    assert needs_contextualization("Apa itu PBG?") is False


def test_contextualize_question_leaves_standalone_query_untouched():
    history = [{"role": "user", "content": "Berapa KDB maksimal untuk area komersial?"}]
    query = "Apa syarat PBG rumah tinggal 2 lantai di Semarang?"

    assert contextualize_question(query, history) == query
