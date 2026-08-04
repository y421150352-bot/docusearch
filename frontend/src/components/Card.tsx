import type { PropsWithChildren, ReactNode } from "react";

type CardProps = PropsWithChildren<{
  className?: string;
  title?: ReactNode;
  actions?: ReactNode;
}>;

export function Card({ className = "", title, actions, children }: CardProps) {
  return (
    <section className={`rounded-2xl bg-white p-6 shadow-sm ${className}`.trim()}>
      {(title || actions) && (
        <div className="flex items-center justify-between gap-3">
          {typeof title === "string" ? (
            <p className="text-sm text-slate-500">{title}</p>
          ) : (
            title
          )}
          {actions}
        </div>
      )}
      <div className={title || actions ? "mt-4" : ""}>{children}</div>
    </section>
  );
}
