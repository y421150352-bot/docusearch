from app.agents.agent_schema import AgentDecision


def route_agent_intent(message: str) -> AgentDecision:
    """
    Agent 意图路由器。

    第一版使用规则路由：
    - 稳定
    - 可控
    - 容易调试
    - 不会误触发重建索引这种操作

    后续可以把这里替换成 LangChain Tool Calling 或 LLM Router。
    """
    text = message.strip().lower()

    # 1. 文档列表
    if any(
        keyword in text
        for keyword in [
            "有哪些文档",
            "文档列表",
            "知识库里有什么",
            "上传了哪些",
            "有什么文件",
            "文件列表",
        ]
    ):
        return AgentDecision(
            intent="list_documents",
            tool_name="list_documents",
        )

    # 2. 重建索引
    if any(
        keyword in text
        for keyword in [
            "重建索引",
            "重新索引",
            "更新索引",
            "更新知识库",
            "重新构建索引",
        ]
    ):
        return AgentDecision(
            intent="rebuild_index",
            tool_name="rebuild_index",
        )

    # 3. 查看历史
    if any(
        keyword in text
        for keyword in [
            "历史记录",
            "问答历史",
            "最近问过",
            "history",
        ]
    ):
        return AgentDecision(
            intent="chat_history",
            tool_name="chat_history",
            arguments={"limit": 10},
        )

    # 4. 查询任务状态
    if any(
        keyword in text
        for keyword in [
            "任务状态",
            "任务完成",
            "完成了吗",
            "task",
            "task_id",
        ]
    ):
        return AgentDecision(
            intent="task_status",
            tool_name="task_status",
        )

    # 5. 默认走 RAG 问答
    return AgentDecision(
        intent="rag_qa",
        tool_name="rag_qa",
        arguments={"question": message},
    )