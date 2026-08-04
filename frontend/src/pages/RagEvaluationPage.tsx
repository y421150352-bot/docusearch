import { useEffect, useState } from "react";

import { getFeedback, getRetrievalPreview } from "../api";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import type { FeedbackItem, RetrievalPreviewData } from "../types";

export function RagEvaluationPage() {
  const [records, setRecords] = useState<FeedbackItem[]>([]);
  const [question, setQuestion] = useState("");
  const [preview, setPreview] = useState<RetrievalPreviewData | null>(null);
  const [loadingFeedback, setLoadingFeedback] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  async function refreshFeedback() {
    try {
      setLoadingFeedback(true);
      setRecords((await getFeedback()).data);
    } catch {
      setError("获取评测记录失败，请确认管理员登录状态。");
    } finally {
      setLoadingFeedback(false);
    }
  }

  useEffect(() => { void refreshFeedback(); }, []);

  async function inspectRetrieval() {
    const text = question.trim();
    if (!text) {
      setError("请输入一个用于评测的检索问题。");
      return;
    }
    try {
      setSearching(true);
      setError("");
      setPreview((await getRetrievalPreview(text)).data);
    } catch {
      setError("召回检索失败，请检查 Qdrant 与嵌入模型是否可用。");
    } finally {
      setSearching(false);
    }
  }

  const positive = records.filter((item) => item.feedback_type === "positive").length;

  return (
    <section>
      <div className="mb-8">
        <h2 className="text-2xl font-bold">RAG 评测</h2>
        <p className="mt-2 text-slate-600">先观察知识库的真实召回切片，再结合用户反馈评估 RAG 策略。</p>
      </div>

      <Card title="召回切片查看">
        <p className="text-sm leading-6 text-slate-600">仅执行 Qdrant Dense + BM25 Sparse + RRF 检索，不调用大模型生成答案。</p>
        <div className="mt-4 flex flex-col gap-3 md:flex-row">
          <input value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void inspectRetrieval(); }} placeholder="输入问题，例如：认知负荷的定义是什么？" className="h-11 flex-1 rounded-xl border border-slate-300 px-4 text-sm outline-none focus:border-slate-500" />
          <button onClick={() => void inspectRetrieval()} disabled={searching} className="rounded-xl bg-slate-950 px-5 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:bg-slate-400">{searching ? "检索中…" : "查看召回"}</button>
        </div>
        {error && <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-600">{error}</p>}
        {preview && (
          <div className="mt-6">
            <p className="mb-3 text-sm text-slate-500">策略：{preview.strategy} · 命中 {preview.chunks.length} 个切片</p>
            {preview.chunks.length === 0 ? <EmptyState message="没有召回切片。可以换一个更具体的关键词，或检查文献是否已处理完成。" /> : <div className="space-y-3">{preview.chunks.map((chunk, index) => <article key={chunk.chunk_id} className="rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-center gap-2 text-sm"><span className="font-semibold">#{index + 1}</span><span className="font-medium">{chunk.document_name}</span><span className="text-slate-500">第 {chunk.page_number} 页</span><span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">RRF {chunk.score.toFixed(4)}</span></div><p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{chunk.content}</p></article>)}</div>}
          </div>
        )}
      </Card>

      <div className="mb-6 mt-6 grid grid-cols-1 gap-4 md:grid-cols-2"><Card title="反馈总数"><p className="text-3xl font-semibold">{records.length}</p></Card><Card title="正向反馈"><p className="text-3xl font-semibold">{positive}</p></Card></div>
      <Card title="问答反馈记录" actions={<button onClick={() => void refreshFeedback()} className="rounded-xl border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100">刷新</button>}>
        {loadingFeedback ? <p className="text-sm text-slate-500">正在加载…</p> : records.length === 0 ? <EmptyState message="暂无评测记录。用户提交问答反馈后会显示在这里。" /> : <div className="space-y-4">{records.map((item) => <article key={item.id} className="rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-medium">{item.question}</p><span className="text-sm text-slate-500">{item.feedback_type === "positive" ? "正向" : "待改进"}</span></div><p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-600">{item.answer}</p>{item.feedback_comment && <p className="mt-3 text-sm text-slate-500">备注：{item.feedback_comment}</p>}</article>)}</div>}
      </Card>
    </section>
  );
}
