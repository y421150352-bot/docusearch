export type BackendStatus = "checking" | "online" | "warning" | "offline";

export type PageName =
  | "dashboard"
  | "chat"
  | "documents"
  | "all-documents"
  | "tasks"
  | "rag-evaluation"
  | "history";

export type MenuItem = {
  key: PageName;
  label: string;
};

export type ApiResponse<T> = {
  code: number;
  message: string;
  data: T;
};

export type AuthUser = {
  id: number;
  username: string;
  role: "admin" | "user" | string;
};

export type LoginResponseData = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
};

export type HealthResponse = ApiResponse<{
  status: "ok" | "warning" | "degraded";
  service: string;
  components: {
    name: string;
    ok: boolean;
    detail: string;
    critical: boolean;
  }[];
}>;

export type KeyPoint = {
  title: string;
  content: string;
};

export type SourceItem = {
  document_name: string;
  page_number: number;
  quote: string;
  score?: number | null;
  rerank_score?: number | null;
  retrieval_type?: string | null;
};

export type AskResponse = {
  question: string;
  summary: string;
  key_points: KeyPoint[];
  sources: SourceItem[];
};

export type AskStreamDone = AskResponse;

export type AskStreamHandlers = {
  onStatus: (message: string) => void;
  onToken: (content: string) => void;
  onDone: (payload: AskStreamDone) => void;
  onError: (message: string) => void;
};

export type AgentChatData = {
  final_answer: string;
  used_tools: string[];
  tool_result: Record<string, unknown>;
};

export type AgentChatResponse = ApiResponse<AgentChatData>;

export type DocumentIndexStatus =
  | "processing"
  | "ready"
  | "failed"
  | "indexed"
  | "outdated";

export type DocumentItem = {
  id: number;
  document_name: string;
  file_type: string;
  size_bytes: number;
  storage_path: string;
  index_status: DocumentIndexStatus;
  index_version: number;
  last_indexed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminDocumentItem = DocumentItem & {
  owner_id: number | null;
  owner_username: string;
};

export type FeedbackItem = {
  id: number;
  question: string;
  answer: string;
  document_name: string | null;
  feedback_type: string;
  feedback_reason: string | null;
  feedback_comment: string | null;
  created_at: string;
};

export type RetrievalPreviewChunk = {
  chunk_id: string;
  document_name: string;
  page_number: number;
  content: string;
  score: number;
  retrieval_type: string;
  owner_id: number | null;
};

export type RetrievalPreviewData = {
  question: string;
  strategy: string;
  chunks: RetrievalPreviewChunk[];
};

export type RebuildIndexData = {
  task_id: string;
  status: string;
};

export type UploadDocumentData = {
  document: DocumentItem;
  task_id: string;
  status: "processing";
};

export type TaskStatusData = {
  task_id: string;
  task_type?: string;
  status: string;
  message: string;
};

export type ChatHistoryItem = {
  id: number;
  question: string;
  document_name: string | null;
  summary: string;
  key_points: KeyPoint[];
  sources: SourceItem[];
  from_cache: boolean;
  latency_ms: number;
  created_at: string;
};

export type FeedbackPayload = {
  question: string;
  answer: string;
  document_name?: string | null;
  sources?: SourceItem[] | Record<string, unknown>[];
  used_tools?: string[];
  feedback_type: string;
  feedback_reason?: string | null;
  feedback_comment?: string | null;
};
