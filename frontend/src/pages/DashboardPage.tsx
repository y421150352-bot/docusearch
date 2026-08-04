import { useEffect, useState } from "react";

import { getHealth } from "../api";
import { Card } from "../components/Card";
import type { BackendStatus, HealthResponse } from "../types";

export function DashboardPage() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [healthData, setHealthData] = useState<HealthResponse["data"] | null>(null);

  useEffect(() => {
    getHealth()
      .then((result) => {
        setHealthData(result.data);
        if (result.data.status === "ok") {
          setBackendStatus("online");
        } else if (result.data.status === "warning") {
          setBackendStatus("warning");
        } else {
          setBackendStatus("offline");
        }
      })
      .catch(() => {
        setBackendStatus("offline");
      });
  }, []);

  const statusText =
    backendStatus === "checking"
      ? "Checking..."
      : backendStatus === "online"
        ? "Backend Healthy"
        : backendStatus === "warning"
          ? "Backend Warning"
          : "Backend Degraded";

  const statusDotClass =
    backendStatus === "online"
      ? "bg-green-500"
      : backendStatus === "warning"
        ? "bg-yellow-500"
        : backendStatus === "offline"
          ? "bg-red-500"
          : "bg-slate-400";

  return (
    <section>
      <div className="mb-8">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <p className="mt-2 text-slate-600">
          Inspect API availability and the current readiness of core backend dependencies.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <Card title="Backend Status">
          <div className="flex items-center gap-3">
            <span className={`h-3 w-3 rounded-full ${statusDotClass}`} />
            <span className="text-lg font-semibold">{statusText}</span>
          </div>

          {healthData && (
            <p className="mt-3 text-sm text-slate-500">
              Service: {healthData.service} ({healthData.status})
            </p>
          )}
        </Card>

        <Card title="Project Stage">
          <p className="text-lg font-semibold">Internal Tool</p>
          <p className="mt-3 text-sm text-slate-500">
            Focused on maintainability, deployment readiness, and operational visibility.
          </p>
        </Card>

        <Card title="Current Feature">
          <p className="text-lg font-semibold">Private RAG Platform</p>
          <p className="mt-3 text-sm text-slate-500">
            Documents, retrieval, cache, tasks, history, health checks, and deployment.
          </p>
        </Card>
      </div>

      {healthData && (
        <div className="mt-6">
          <Card title="Dependency Readiness">
            <div className="space-y-3">
              {healthData.components.map((component) => (
                <div
                  key={component.name}
                  className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="font-medium capitalize">{component.name}</div>
                    <span
                      className={
                        component.ok ? "text-green-700" : "text-red-700"
                      }
                    >
                      {component.ok ? "Ready" : "Unavailable"}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{component.detail}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </section>
  );
}
