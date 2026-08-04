import { useState } from "react";

import { getTaskStatus, rebuildIndex } from "../api";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import type { TaskStatusData } from "../types";

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function TasksPage() {
  const [currentTask, setCurrentTask] = useState<TaskStatusData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function pollTaskStatus(taskId: string) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await sleep(1000);
      const result = await getTaskStatus(taskId);
      setCurrentTask(result.data);
      if (result.data.status === "completed" || result.data.status === "failed") {
        return;
      }
    }

    setError("任务状态查询超时，请稍后手动刷新。");
  }

  async function handleRebuildIndex() {
    try {
      setLoading(true);
      setError("");
      setMessage("");
      setCurrentTask(null);

      const result = await rebuildIndex();
      const taskId = result.data.task_id;

      setMessage(result.message);
      setCurrentTask({
        task_id: taskId,
        task_type: "rebuild_index",
        status: result.data.status,
        message: result.message,
      });

      await pollTaskStatus(taskId);
    } catch {
      setError("索引重建任务提交或查询失败，请检查后端服务。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Tasks</h2>
        <p className="mt-2 text-slate-600">
          在这里提交索引重建任务，并实时查看后台任务状态。
        </p>
      </div>

      <Card title="Index Management">
        <h3 className="text-lg font-semibold text-slate-900">
          Rebuild Knowledge Base Index
        </h3>
        <p className="mt-3 leading-7 text-slate-600">
          上传或删除文档后，需要重新构建索引，Chat 页面才能基于最新知识库内容回答。
        </p>

        <button
          onClick={handleRebuildIndex}
          disabled={loading}
          className={
            loading
              ? "mt-5 rounded-xl bg-slate-400 px-5 py-2 text-sm font-medium text-white"
              : "mt-5 rounded-xl bg-slate-950 px-5 py-2 text-sm font-medium text-white hover:bg-slate-800"
          }
        >
          {loading ? "Rebuilding..." : "Rebuild Index"}
        </button>

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

      <Card className="mt-6" title="Current Task">
        {!currentTask ? (
          <EmptyState message="当前没有正在展示的任务。点击 Rebuild Index 后会显示任务状态。" />
        ) : (
          <div className="rounded-xl border border-slate-200 p-5">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm text-slate-500">Task ID</p>
                <p className="mt-1 break-all font-mono text-sm text-slate-800">
                  {currentTask.task_id}
                </p>
              </div>

              <StatusBadge
                status={
                  currentTask.status === "completed" ||
                  currentTask.status === "failed" ||
                  currentTask.status === "running"
                    ? currentTask.status
                    : "pending"
                }
                label={currentTask.status}
              />
            </div>

            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <p className="text-sm text-slate-500">Task Type</p>
                <p className="mt-1 text-slate-800">
                  {currentTask.task_type || "unknown"}
                </p>
              </div>

              <div>
                <p className="text-sm text-slate-500">Message</p>
                <p className="mt-1 text-slate-800">{currentTask.message}</p>
              </div>
            </div>
          </div>
        )}
      </Card>
    </section>
  );
}
