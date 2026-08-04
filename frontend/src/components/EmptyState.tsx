type EmptyStateProps = {
  message: string;
  className?: string;
};

export function EmptyState({ message, className = "" }: EmptyStateProps) {
  return (
    <div
      className={`rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-slate-500 ${className}`.trim()}
    >
      {message}
    </div>
  );
}
