import { useEffect, useState } from "react";

import {
  clearChatHistory,
  deleteChatHistory,
  getChatHistory,
} from "../api";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import type { ChatHistoryItem } from "../types";

export function HistoryPage() {
  const [chatHistory, setChatHistory] = useState<ChatHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function refreshChatHistory() {
    try {
      setLoading(true);
      setError("");
      const result = await getChatHistory(50);
      setChatHistory(result.data);
    } catch {
      setError("获取问答历史失败，请检查后端 /chat-history 接口。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshChatHistory();
  }, []);

  async function handleDeleteChatHistory(historyId: number) {
    if (!window.confirm("确定要删除这条问答历史吗？")) {
      return;
    }

    try {
      setLoading(true);
      setError("");
      setMessage("");
      const result = await deleteChatHistory(historyId);
      setMessage(result.message);
      await refreshChatHistory();
    } catch {
      setError("删除问答历史失败，请检查后端接口。");
    } finally {
      setLoading(false);
    }
  }

  async function handleClearChatHistory() {
    if (!window.confirm("确定要清空全部问答历史吗？")) {
      return;
    }

    try {
      setLoading(true);
      setError("");
      setMessage("");
      const result = await clearChatHistory();
      setMessage(result.message);
      await refreshChatHistory();
    } catch {
      setError("清空问答历史失败，请检查后端接口。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <div className="mb-8">
        <h2 className="text-2xl font-bold">History</h2>
        <p className="mt-2 text-slate-600">
          在这里查看系统保存的历史问答记录，包括所属文档、来源数量、缓存命中和响应耗时。
        </p>
      </div>

      <Card
        title="Chat History"
        actions={
          <div className="flex gap-3">
            <button
              onClick={refreshChatHistory}
              disabled={loading}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
            >
              Refresh
            </button>
            <button
              onClick={handleClearChatHistory}
              disabled={loading || chatHistory.length === 0}
              className={
                loading || chatHistory.length === 0
                  ? "rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-400"
                  : "rounded-xl border border-red-300 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
              }
            >
              Clear All
            </button>
          </div>
        }
      >
        <p className="text-sm text-slate-600">默认展示最近 50 条问答记录。</p>

        {message && (
          <p className="mt-4 rounded-xl bg-green-50 p-3 text-sm text-green-700">
            {message}
          </p>
        )}
        {error && (
          <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-600">
            {error}
          </p>
        )}

        {loading ? (
          <div className="mt-6 text-sm text-slate-500">Loading chat history...</div>
        ) : chatHistory.length === 0 ? (
          <EmptyState
            className="mt-6"
            message="当前还没有问答历史。你可以先到 Chat 页面提问。"
          />
        ) : (
          <div className="mt-6 space-y-4">
            {chatHistory.map((item) => (
              <div key={item.id} className="rounded-xl border border-slate-200 p-5">
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                        {item.created_at}
                      </span>
                      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                        {item.document_name ?? "全部文档"}
                      </span>
                      <span
                        className={
                          item.from_cache
                            ? "rounded-full bg-blue-100 px-3 py-1 text-xs text-blue-700"
                            : "rounded-full bg-green-100 px-3 py-1 text-xs text-green-700"
                        }
                      >
                        {item.from_cache ? "Cache Hit" : "Generated"}
                      </span>
                      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                        {item.latency_ms} ms
                      </span>
                      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                        Sources: {item.sources.length}
                      </span>
                    </div>

                    <p className="mt-4 text-sm font-semibold text-slate-900">
                      Q: {item.question}
                    </p>
                    <p className="mt-3 leading-7 text-slate-700">{item.summary}</p>

                    {item.key_points.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {item.key_points.slice(0, 3).map((point, index) => (
                          <div
                            key={`${item.id}-${point.title}-${index}`}
                            className="rounded-lg bg-slate-50 p-3"
                          >
                            <p className="text-sm font-medium text-slate-800">
                              {index + 1}. {point.title}
                            </p>
                            <p className="mt-1 text-sm leading-6 text-slate-600">
                              {point.content}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => handleDeleteChatHistory(item.id)}
                    className="rounded-xl border border-red-300 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </section>
  );
}
