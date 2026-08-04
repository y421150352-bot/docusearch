from fastapi import BackgroundTasks

from app.agents import agent_service
from app.agents.agent_schema import AgentChatRequest, AgentChatResult


def test_agent_chat_is_saved_once(monkeypatch):
    saved: list[dict] = []
    monkeypatch.setattr(
        agent_service,
        "_run_agent_chat_impl",
        lambda request, background_tasks, owner_id: AgentChatResult(
            final_answer="测试回答",
            used_tools=["test_tool"],
        ),
    )
    monkeypatch.setattr(
        agent_service,
        "save_agent_chat_history",
        lambda **kwargs: saved.append(kwargs),
    )

    result = agent_service.run_agent_chat(
        AgentChatRequest(message=" 测试问题 ", document_name="demo.pdf"),
        BackgroundTasks(),
        owner_id=1,
    )

    assert result.final_answer == "测试回答"
    assert len(saved) == 1
    assert saved[0]["question"] == "测试问题"
    assert saved[0]["final_answer"] == "测试回答"
    assert saved[0]["document_name"] == "demo.pdf"
    assert saved[0]["owner_id"] == 1
    assert saved[0]["latency_ms"] >= 0
