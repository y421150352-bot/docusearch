import type {
  ApiResponse,
  AgentChatResponse,
  AuthUser,
  AskResponse,
  AskStreamDone,
  AskStreamHandlers,
  ChatHistoryItem,
  DocumentItem,
  AdminDocumentItem,
  FeedbackItem,
  RetrievalPreviewData,
  FeedbackPayload,
  HealthResponse,
  RebuildIndexData,
  TaskStatusData,
  UploadDocumentData,
  LoginResponseData,
} from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

const TOKEN_KEY = "docusearch_access_token";

export function getAccessToken(): string | null {
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  window.sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  window.sessionStorage.removeItem(TOKEN_KEY);
}

async function authFetch(
  input: RequestInfo | URL,
  init: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(input, { ...init, headers });
  if (response.status === 401) {
    clearAccessToken();
    window.dispatchEvent(new Event("docusearch:auth-expired"));
  }
  return response;
}

export async function login(
  username: string,
  password: string
): Promise<ApiResponse<LoginResponseData>> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Login failed: ${response.status}`);
  }
  const result = (await response.json()) as ApiResponse<LoginResponseData>;
  setAccessToken(result.data.access_token);
  return result;
}

export async function getCurrentUser(): Promise<ApiResponse<AuthUser>> {
  const response = await authFetch(`${API_BASE_URL}/auth/me`);
  if (!response.ok) {
    throw new Error(`Get current user failed: ${response.status}`);
  }
  return response.json();
}

export async function logout(): Promise<void> {
  const response = await authFetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
  });
  clearAccessToken();
  if (!response.ok && response.status !== 401) {
    throw new Error(`Logout failed: ${response.status}`);
  }
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}

export async function agentChat(
  message: string,
  documentName?: string,
  signal?: AbortSignal
): Promise<AgentChatResponse> {
  const response = await authFetch(`${API_BASE_URL}/agent-chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      document_name: documentName ?? null,
    }),
    signal,
  });
  if (!response.ok) {
    throw new Error(`Agent request failed: ${response.status}`);
  }
  return response.json();
}

export async function askQuestion(
  question: string,
  documentName?: string
): Promise<AskResponse> {
  const params = new URLSearchParams({ question });
  if (documentName) {
    params.set("document_name", documentName);
  }

  const response = await authFetch(`${API_BASE_URL}/ask?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Ask request failed: ${response.status}`);
  }
  return response.json();
}

function processSseEvent(
  eventBlock: string,
  handlers: AskStreamHandlers
): void {
  const lines = eventBlock.split(/\r?\n/);
  let eventName = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (dataLines.length === 0) {
    return;
  }

  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(dataLines.join("\n")) as Record<string, unknown>;
  } catch {
    handlers.onError("Invalid streaming payload.");
    return;
  }
  if (eventName === "status") {
    handlers.onStatus(String(payload.message ?? ""));
    return;
  }
  if (eventName === "token") {
    handlers.onToken(String(payload.content ?? ""));
    return;
  }
  if (eventName === "done") {
    handlers.onDone(payload as AskStreamDone);
    return;
  }
  if (eventName === "error") {
    handlers.onError(String(payload.message ?? "Streaming request failed."));
  }
}

export async function askQuestionStream(
  question: string,
  documentName: string | undefined,
  handlers: AskStreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  const response = await authFetch(`${API_BASE_URL}/ask-stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      question,
      document_name: documentName ?? null,
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Ask stream request failed: ${response.status}`);
  }
  if (!response.body) {
    throw new Error("Streaming response body is empty.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    const events = buffer.split(/\r?\n\r?\n/);
    buffer = events.pop() ?? "";

    for (const eventBlock of events) {
      if (eventBlock.trim()) {
        processSseEvent(eventBlock, handlers);
      }
    }

    if (done) {
      if (buffer.trim()) {
        processSseEvent(buffer, handlers);
      }
      break;
    }
  }
}

export async function getDocuments(): Promise<ApiResponse<DocumentItem[]>> {
  const response = await authFetch(`${API_BASE_URL}/documents`);
  if (!response.ok) {
    throw new Error(`Get documents failed: ${response.status}`);
  }
  return response.json();
}

export async function getAllDocuments(): Promise<ApiResponse<AdminDocumentItem[]>> {
  const response = await authFetch(`${API_BASE_URL}/admin/all-documents`);
  if (!response.ok) {
    throw new Error(`Get all documents failed: ${response.status}`);
  }
  return response.json();
}

export async function deleteAnyDocument(
  documentId: number
): Promise<ApiResponse<{ id: number; document_name: string }>> {
  const response = await authFetch(`${API_BASE_URL}/admin/all-documents/${documentId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Delete document failed: ${response.status}`);
  }
  return response.json();
}

export async function uploadDocument(
  file: File
): Promise<ApiResponse<UploadDocumentData>> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await authFetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`Upload document failed: ${response.status}`);
  }
  return response.json();
}

export async function deleteDocumentByName(
  documentName: string
): Promise<ApiResponse<{ document_name: string }>> {
  const response = await authFetch(
    `${API_BASE_URL}/documents/${encodeURIComponent(documentName)}`,
    {
      method: "DELETE",
    }
  );
  if (!response.ok) {
    throw new Error(`Delete document failed: ${response.status}`);
  }
  return response.json();
}

export async function rebuildIndex(): Promise<ApiResponse<RebuildIndexData>> {
  const response = await authFetch(`${API_BASE_URL}/admin/rebuild-index`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Rebuild index failed: ${response.status}`);
  }
  return response.json();
}

export async function getTaskStatus(
  taskId: string
): Promise<ApiResponse<TaskStatusData>> {
  const response = await authFetch(
    `${API_BASE_URL}/admin/task-status/${encodeURIComponent(taskId)}`
  );
  if (!response.ok) {
    throw new Error(`Get task status failed: ${response.status}`);
  }
  return response.json();
}

export async function getChatHistory(
  limit = 50
): Promise<ApiResponse<ChatHistoryItem[]>> {
  const response = await authFetch(`${API_BASE_URL}/chat-history?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Get chat history failed: ${response.status}`);
  }
  return response.json();
}

export async function deleteChatHistory(
  historyId: number
): Promise<ApiResponse<{ id: number }>> {
  const response = await authFetch(`${API_BASE_URL}/chat-history/${historyId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Delete chat history failed: ${response.status}`);
  }
  return response.json();
}

export async function clearChatHistory(): Promise<
  ApiResponse<{ deleted_count: number }>
> {
  const response = await authFetch(`${API_BASE_URL}/chat-history`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Clear chat history failed: ${response.status}`);
  }
  return response.json();
}

export async function submitFeedback(
  payload: FeedbackPayload
): Promise<ApiResponse<{ id: number }>> {
  const response = await authFetch(`${API_BASE_URL}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question: payload.question,
      answer: payload.answer,
      document_name: payload.document_name ?? null,
      sources: payload.sources ?? [],
      used_tools: payload.used_tools ?? [],
      feedback_type: payload.feedback_type,
      feedback_reason: payload.feedback_reason ?? null,
      feedback_comment: payload.feedback_comment ?? null,
    }),
  });

  if (!response.ok) {
    throw new Error(`Submit feedback failed: ${response.status}`);
  }
  return response.json();
}

export async function getFeedback(
  limit = 100
): Promise<ApiResponse<FeedbackItem[]>> {
  const response = await authFetch(`${API_BASE_URL}/admin/feedback?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Get feedback failed: ${response.status}`);
  }
  return response.json();
}

export async function getRetrievalPreview(
  question: string,
  topK = 8
): Promise<ApiResponse<RetrievalPreviewData>> {
  const params = new URLSearchParams({ question, top_k: String(topK) });
  const response = await authFetch(`${API_BASE_URL}/admin/retrieval-preview?${params}`);
  if (!response.ok) {
    throw new Error(`Retrieval preview failed: ${response.status}`);
  }
  return response.json();
}
