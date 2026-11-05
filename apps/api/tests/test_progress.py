from services.progress import advance, begin, finish, retitle, snapshot


def test_progress_counts_each_answer():
    begin("progress-test", 4)
    try:
        assert snapshot("progress-test").percent == 0
        advance("progress-test", "ChatGPT · Quel outil choisir ?")
        current = snapshot("progress-test")
        assert (current.done, current.percent, current.running) == (1, 25, True)
        assert current.label.startswith("1 sur 4 · ChatGPT")
        retitle("progress-test", "Lecture des réponses…")
        assert snapshot("progress-test").label == "Lecture des réponses…"
        assert snapshot("progress-test").percent == 25
    finally:
        finish("progress-test")
    assert snapshot("progress-test").running is False
