from tmki_demo.chat_session import (
    ChatSession,
    ChatSessionStore,
    ChatTurn,
    augment_query_with_session,
    is_follow_up_query,
)


def test_is_follow_up():
    assert is_follow_up_query("а что там по пункту 2")
    assert is_follow_up_query("подробнее")
    assert not is_follow_up_query("кран ростехнадзор требования промбезопасности на опасном производственном объекте")


def test_session_history_and_memory(tmp_path):
    store = ChatSessionStore(persist_dir=tmp_path)
    session = store.create(corpus_id="skru-2")
    store.append_turn(session, ChatTurn(role="user", content="опиши письмо 452"))
    store.append_turn(
        session,
        ChatTurn(
            role="assistant",
            content="Суть: правки КМД",
            citations=[{"doc_id": "doc_x", "relative_path": "452 правки письма.pdf", "snippet": "текст"}],
        ),
    )
    assert session.active_paths == ["452 правки письма.pdf"]
    hist = store.history_for_llm(session)
    assert len(hist) == 2
    expanded = augment_query_with_session("подробнее про ограждение", session)
    assert "Контекст диалога" in expanded


def test_session_persist_roundtrip(tmp_path):
    store = ChatSessionStore(persist_dir=tmp_path)
    s = store.create(corpus_id="arm-ks")
    store.append_turn(s, ChatTurn(role="user", content="тест"))
    reloaded = ChatSessionStore(persist_dir=tmp_path)
    got = reloaded.get(s.session_id)
    assert got is not None
    assert got.turns[0].content == "тест"
