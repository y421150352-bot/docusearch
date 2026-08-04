import { useEffect, useState } from "react";

import { deleteDocumentByName, getDocuments, uploadDocument } from "../api";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import type { DocumentItem } from "../types";

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function refreshDocuments(showLoading = true) {
    try {
      if (showLoading) {
        setLoading(true);
      }
      setError("");
      const result = await getDocuments();
      setDocuments(result.data);
    } catch {
      setError("获取文档列表失败，请检查后端 /documents 接口。");
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void refreshDocuments();
  }, []);

  useEffect(() => {
    const hasProcessingDocument = documents.some(
      (document) =>
        document.index_status === "processing" ||
        document.index_status === "outdated"
    );
    if (!hasProcessingDocument) {
      return;
    }

    const timer = window.setInterval(() => {
      void refreshDocuments(false);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [documents]);

  async function handleUploadDocument() {
    if (!selectedFile) {
      setError("请先选择一个文件再上传。");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setMessage("");
      const result = await uploadDocument(selectedFile);
      setMessage(result.message);
      setSelectedFile(null);
      await refreshDocuments(false);
    } catch {
      setError("上传文档失败，请检查文件格式或后端接口。");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteDocument(documentName: string) {
    if (!window.confirm(`确定要删除文档 ${documentName} 吗？`)) {
      return;
    }

    try {
      setLoading(true);
      setError("");
      setMessage("");
      const result = await deleteDocumentByName(documentName);
      setMessage(result.message);
      await refreshDocuments();
    } catch {
      setError("删除文档失败，请检查后端接口。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <div className="mb-8">
        <h2 className="text-2xl font-bold">知识库文档</h2>
        <p className="mt-2 text-slate-600">
          文档上传后会自动解析并写入检索库，处理完成后即可直接用于问答。
        </p>
      </div>

      <Card title="上传文档">
        <div className="flex flex-col gap-4 md:flex-row md:items-center">
          <input
            type="file"
            accept=".pdf,.txt,.md"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            className="block w-full text-sm text-slate-700"
          />

          <button
            onClick={handleUploadDocument}
            disabled={loading}
            className={
              loading
                ? "rounded-xl bg-slate-400 px-5 py-2 text-sm font-medium text-white"
                : "rounded-xl bg-slate-950 px-5 py-2 text-sm font-medium text-white hover:bg-slate-800"
            }
          >
            上传
          </button>
        </div>

        {selectedFile && (
          <p className="mt-3 text-sm text-slate-500">
            已选择文件：{selectedFile.name}
          </p>
        )}
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
      </Card>

      <Card
        className="mt-6"
        title="文档列表"
        actions={
          <button
            onClick={() => void refreshDocuments()}
            className="rounded-xl border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            刷新
          </button>
        }
      >
        {loading ? (
          <div className="text-sm text-slate-500">正在加载文档…</div>
        ) : documents.length === 0 ? (
          <EmptyState message="当前没有可用文档。你可以先上传 PDF / TXT / MD 文件。" />
        ) : (
          <div className="space-y-4">
            {documents.map((document) => (
              <div
                key={document.document_name}
                className="rounded-xl border border-slate-200 p-4"
              >
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="font-semibold text-slate-900">
                        {document.document_name}
                      </p>
                      <StatusBadge status={document.index_status} />
                    </div>
                    <p className="mt-1 text-sm text-slate-500">
                      类型：{document.file_type.toUpperCase()} · 大小：
                      {(document.size_bytes / 1024).toFixed(2)} KB · 更新时间：
                      {document.updated_at}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      处理版本：{document.index_version} · 最近可用时间：
                      {document.last_indexed_at ?? "处理中"}
                    </p>
                  </div>

                  <button
                    onClick={() => handleDeleteDocument(document.document_name)}
                    className="rounded-xl border border-red-300 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    删除
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
