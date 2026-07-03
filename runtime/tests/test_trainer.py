from tmki_trainer.engine import evaluate_attempt, load_curriculum


def test_curriculum_loads():
    c = load_curriculum()
    assert len(c.tracks) == 4
    ids = {t.id for t in c.tracks}
    assert ids == {"search", "read", "understand", "dialogue"}
    total = sum(len(t.lessons) for t in c.tracks)
    assert total >= 10


def test_evaluate_passes_good_answer():
    c = load_curriculum()
    lesson = c.lesson_by_id("read-01")
    assert lesson is not None
    result = evaluate_attempt(
        lesson,
        "Ingest поддерживает PDF, DOCX и OCR для изображений, а для сложной вёрстки есть Docling.",
    )
    assert result.score >= 0.5
    assert "pdf" in [h.lower() for h in result.keyword_hits] or result.passed


def test_evaluate_partial():
    c = load_curriculum()
    lesson = c.lesson_by_id("search-01")
    assert lesson is not None
    result = evaluate_attempt(lesson, "кран")
    assert result.score < 1.0 or result.keyword_misses
