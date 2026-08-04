import { useEffect, useState } from "react";

import "./App.css";
import { getCurrentUser, getHealth, getAccessToken, logout } from "./api";
import { Sidebar } from "./components/Sidebar";
import { ChatPage } from "./pages/ChatPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { AllDocumentsPage } from "./pages/AllDocumentsPage";
import { HistoryPage } from "./pages/HistoryPage";
import { RagEvaluationPage } from "./pages/RagEvaluationPage";
import { TasksPage } from "./pages/TasksPage";
import { LoginPage } from "./pages/LoginPage";
import type { AuthUser, BackendStatus, MenuItem, PageName } from "./types";

const userMenus: MenuItem[] = [
  { key: "chat", label: "新对话" },
  { key: "documents", label: "我的文献库" },
  { key: "history", label: "历史记录" },
];

const adminMenus: MenuItem[] = [
  { key: "chat", label: "新对话" },
  { key: "documents", label: "我的文献库" },
  { key: "all-documents", label: "全部文献管理" },
  { key: "tasks", label: "任务" },
  { key: "rag-evaluation", label: "RAG 评测" },
  { key: "history", label: "历史记录" },
];

function renderPage(activePage: PageName) {
  switch (activePage) {
    case "documents":
      return <DocumentsPage />;
    case "all-documents":
      return <AllDocumentsPage />;
    case "chat":
      return <ChatPage />;
    case "tasks":
      return <TasksPage />;
    case "rag-evaluation":
      return <RagEvaluationPage />;
    case "history":
      return <HistoryPage />;
    case "dashboard":
    default:
      return <DashboardPage />;
  }
}

function App() {
  const [activePage, setActivePage] = useState<PageName>("chat");
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const menus = currentUser?.role === "admin" ? adminMenus : userMenus;

  useEffect(() => {
    let disposed = false;
    async function restoreSession() {
      if (!getAccessToken()) {
        if (!disposed) setAuthLoading(false);
        return;
      }
      try {
        const result = await getCurrentUser();
        if (!disposed) setCurrentUser(result.data);
      } catch {
        if (!disposed) setCurrentUser(null);
      } finally {
        if (!disposed) setAuthLoading(false);
      }
    }
    void restoreSession();
    return () => {
      disposed = true;
    };
  }, []);

  useEffect(() => {
    const handleExpired = () => setCurrentUser(null);
    window.addEventListener("docusearch:auth-expired", handleExpired);
    return () => window.removeEventListener("docusearch:auth-expired", handleExpired);
  }, []);

  useEffect(() => {
    let disposed = false;

    async function checkBackend() {
      try {
        const result = await getHealth();
        if (!disposed) {
          setBackendStatus(
            result.data.status === "ok"
              ? "online"
              : result.data.status === "warning"
                ? "warning"
                : "offline"
          );
        }
      } catch {
        if (!disposed) {
          setBackendStatus("offline");
        }
      }
    }

    checkBackend();
    const timer = window.setInterval(checkBackend, 15000);

    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, []);

  if (authLoading) {
    return <main className="auth-page"><p>正在检查登录状态…</p></main>;
  }

  if (!currentUser) {
    return <LoginPage onLogin={setCurrentUser} />;
  }

  async function handleLogout() {
    try {
      await logout();
    } finally {
      setCurrentUser(null);
      setActivePage("chat");
    }
  }

  return (
    <div className="app-shell">
      <Sidebar
        activePage={activePage}
        menus={menus}
        backendStatus={backendStatus}
        onSelect={setActivePage}
        currentUser={currentUser}
        onLogout={handleLogout}
      />
      <main className="app-main">{renderPage(activePage)}</main>
    </div>
  );
}

export default App;
