# Agent Tools And Scenarios

DocuSearch Agent 使用 MySQL 保存业务数据、Qdrant 保存语义向量、Redis 保存缓存与任务状态，并使用 BM25 关键词召回。

## 新增 Agent Tools

- `rag_qa_tool(question, document_name=None)`: 文档问答与知识库总结
- `list_documents_tool()`: 查看知识库中的文档列表
- `chat_history_tool(limit=10)`: 查看最近问答历史
- `task_status_tool(task_id)`: 查询后台任务状态
- `document_detail_tool(document_name)`: 查询文档详情与索引状态
- `index_health_tool()`: 检查当前知识库索引健康状态
- `search_sources_tool(query, document_name=None, top_k=5)`: 只检索相关原文片段，不生成总结
- `summarize_document_tool(document_name)`: 总结指定文档
- `compare_documents_tool(document_a, document_b, question=None)`: 比较两篇文档

## 真实用户需求场景

用户现在可以直接问：

1. `知识库里有哪些文档`
2. `当前知识库状态正常吗`
3. `哪些文档需要重建索引`
4. `demo.pdf 有没有被索引`
5. `只帮我找认知负荷相关原文片段`
6. `总结 demo.pdf`
7. `比较 A.pdf 和 B.pdf 的研究方法`
8. `查看最近问答历史`
9. `帮我重建索引`
10. `清理缓存`

## 确认机制

- 用户说 `帮我重建索引` 时，系统不会直接执行，而是提示输入 `确认重建索引`
- 用户说 `清理缓存` 时，系统不会直接执行，而是提示输入 `确认清理缓存`
- 缓存清理只删除 Redis 中 `qa_cache:` 前缀的问答缓存，不会 `flushdb`，不会删除任务状态

## 并发与安全

- `compare_documents_tool` 会并发生成两篇文档的局部摘要
- 并发执行仅用于只读任务或 LLM 生成任务，不用于写 MySQL、写 Qdrant、删除文档或重建索引
- 重建索引前会获取 Redis 锁 `rebuild_index_lock`，避免多个任务同时更新 MySQL 文档片段和 Qdrant 集合
- 解析正文写入 MySQL `document_chunk`；Qdrant upsert 使用等待确认，并以 Dense + Sparse + RRF 完成混合召回
