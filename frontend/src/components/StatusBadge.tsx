import type { DocumentIndexStatus } from "../types";

type StatusBadgeProps = {
  status: DocumentIndexStatus | "pending" | "running" | "completed";
  label?: string;
};

const badgeClassMap: Record<StatusBadgeProps["status"], string> = {
  processing: "bg-slate-200 text-slate-600",
  ready: "bg-slate-900 text-white",
  indexed: "bg-slate-900 text-white",
  outdated: "bg-slate-200 text-slate-600",
  failed: "bg-red-100 text-red-700",
  pending: "bg-yellow-100 text-yellow-700",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
};

const defaultLabelMap: Record<StatusBadgeProps["status"], string> = {
  processing: "正在处理…",
  ready: "可用于问答",
  indexed: "可用于问答",
  outdated: "正在处理…",
  failed: "处理失败",
  pending: "pending",
  running: "running",
  completed: "completed",
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-medium ${badgeClassMap[status]}`}
    >
      {label ?? defaultLabelMap[status]}
    </span>
  );
}
