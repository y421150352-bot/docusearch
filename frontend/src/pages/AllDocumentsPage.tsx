import { useEffect, useState } from "react";

import { deleteAnyDocument, getAllDocuments } from "../api";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import type { AdminDocumentItem } from "../types";

export function AllDocumentsPage() {
  const [documents, setDocuments] = useState<AdminDocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh() {
    try {
      setLoading(true);
      setError("");
      setDocuments((await getAllDocuments()).data);
    } catch {
      setError("获取全部文献失败，请确认管理员登录状态。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, []);

  async function remove(document: AdminDocumentItem) {
    if (!window.confirm(`确定删除「${document.document_name}」吗？该操作会删除用户的文件和向量数据。`)) return;
    try {
      await deleteAnyDocument(document.id);
      await refresh();
    } catch {
      setError("删除失败，请稍后重试。");
    }
  }

  return (
    <section>
      <div className="mb-8">
        <h2 className="text-2xl font-bold">全部文献管理</h2>
        <p className="mt-2 text-slate-600">查看各用户上传的文献及处理状态；删除操作会同步移除 MySQL、Qdrant 和原始文件。</p>
      </div>
      <Card title="全部文献" actions={<button onClick={() => void refresh()} className="rounded-xl border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100">刷新</button>}>
        {error && <p className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-600">{error}</p>}
        {loading ? <p className="text-sm text-slate-500">正在加载…</p> : documents.length === 0 ? <EmptyState message="目前没有用户文献。" /> : (
          <div className="space-y-3">
            {documents.map((document) => (
              <div key={document.id} className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-3"><p className="font-semibold">{document.document_name}</p><StatusBadge status={document.index_status} /></div>
                  <p className="mt-1 text-sm text-slate-500">所属用户：{document.owner_username} · {document.file_type.toUpperCase()} · {(document.size_bytes / 1024).toFixed(1)} KB</p>
                </div>
                <button onClick={() => void remove(document)} className="rounded-xl border border-red-300 px-4 py-2 text-sm text-red-600 hover:bg-red-50">删除</button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </section>
  );
}
