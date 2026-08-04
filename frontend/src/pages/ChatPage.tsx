import { useEffect, useRef, useState } from "react";

import { agentChat, getDocuments } from "../api";
import { FeedbackButtons } from "../components/FeedbackButtons";
import { MessageMarkdown } from "../components/MessageMarkdown";
import type { DocumentItem } from "../types";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  question?: string;
  documentName?: string | null;
  usedTools?: string[];
  toolResult?: Record<string, unknown>;
  loading?: boolean;
  error?: string;
  copied?: boolean;
};

const QUICK_PROMPTS = [
  "知识库里有哪些文献？",
  "检索认知负荷相关原文",
  "总结当前选择的文献",
  "比较两篇文献的研究方法",
];

function createMessageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function createInitialMessages(): ChatMessage[] {
  return [];
}

function formatToolResult(result?: Record<string, unknown>) {
  if (!result || Object.keys(result).length === 0) {
    return "";
  }
  return JSON.stringify(result, null, 2);
}

export function ChatPage() {
  const [input, setInput] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocument, setSelectedDocument] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>(createInitialMessages);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    getDocuments()
      .then((result) => setDocuments(result.data))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [input]);

  function updateMessage(
    messageId: string,
    updater: (message: ChatMessage) => ChatMessage
  ) {
    setMessages((current) =>
      current.map((message) =>
        message.id === messageId ? updater(message) : message
      )
    );
  }

  async function sendAgentMessage(
    text: string,
    options?: {
      includeUserMessage?: boolean;
      documentName?: string;
    }
  ) {
    const message = text.trim();
    if (!message || loading) return;

    const documentName =
      options?.documentName ?? (selectedDocument || undefined);
    const assistantId = createMessageId();
    const nextMessages: ChatMessage[] = [];

    if (options?.includeUserMessage !== false) {
      nextMessages.push({
        id: createMessageId(),
        role: "user",
        content: message,
        question: message,
        documentName: documentName ?? null,
      });
    }
    nextMessages.push({
      id: assistantId,
      role: "assistant",
      content: "",
      question: message,
      documentName: documentName ?? null,
      loading: true,
      usedTools: ["Agent Router"],
    });
    setMessages((current) => [...current, ...nextMessages]);
    setInput("");
    setError("");
    setLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;
    try {
      const response = await agentChat(
        message,
        documentName,
        controller.signal
      );
      updateMessage(assistantId, (current) => ({
        ...current,
        content: response.data.final_answer,
        usedTools:
          response.data.used_tools.length > 0
            ? response.data.used_tools
            : ["Agent"],
        toolResult: response.data.tool_result,
        loading: false,
      }));
    } catch (exception) {
      if (exception instanceof DOMException && exception.name === "AbortError") {
        updateMessage(assistantId, (current) => ({
          ...current,
          content: current.content || "Agent 请求已停止。",
          loading: false,
        }));
      } else {
        const requestError =
          "Agent 请求失败，请检查后端服务、LLM 配置或 /agent-chat 接口。";
        updateMessage(assistantId, (current) => ({
          ...current,
          loading: false,
          error: requestError,
        }));
        setError(requestError);
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  }

  async function handleCopy(message: ChatMessage) {
    if (!message.content) return;
    await navigator.clipboard.writeText(message.content);
    updateMessage(message.id, (current) => ({ ...current, copied: true }));
    window.setTimeout(() => {
      updateMessage(message.id, (current) => ({ ...current, copied: false }));
    }, 1600);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendAgentMessage(input);
    }
  }

  return (
    <section className={messages.length === 0 ? "chat-page is-empty" : "chat-page"}>
      <header className="chat-header">
        <h2>{messages.length === 0 ? "新对话" : "文献问答"}</h2>
        <p className="chat-subtitle">基于私有文献库的智能研究助手</p>
      </header>

      {messages.length === 0 && (
        <div className="chat-empty-state">
          <img
            className="chat-empty-logo"
            src="/sheep-docusearch.png"
            alt="DocuSearch 小羊图标"
          />
          <h1>今天想研究什么？</h1>
          <p>检索文献、总结内容，或比较不同研究中的方法与结论。</p>
          <div className="quick-prompt-row">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="quick-prompt-chip"
                onClick={() => {
                  setInput(prompt);
                  textareaRef.current?.focus();
                }}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="chat-thread">
        {messages.map((message) => (
          <div
            key={message.id}
            className={
              message.role === "user"
                ? "chat-row is-user"
                : "chat-row is-assistant"
            }
          >
            <div
              className={
                message.role === "user"
                  ? "chat-bubble is-user"
                  : "chat-bubble is-assistant"
              }
            >
              <div className="chat-bubble-meta">
                <span>{message.role === "user" ? "你" : "DocuSearch"}</span>
                {message.documentName && (
                  <span className="chat-inline-tag">{message.documentName}</span>
                )}
              </div>

              {message.loading && (
                <p className="chat-status-message">
                  正在检索并分析文献...
                </p>
              )}
              {message.content &&
                (message.role === "assistant" ? (
                  <MessageMarkdown content={message.content} />
                ) : (
                  <p className="chat-message-content">{message.content}</p>
                ))}
              {message.error && (
                <p className="chat-message-error">{message.error}</p>
              )}

              {message.role === "assistant" &&
                !message.loading &&
                !message.error && (
                  <>
                    <div className="message-action-row">
                      <button
                        type="button"
                        className="message-action-button"
                        onClick={() => void handleCopy(message)}
                      >
                        {message.copied ? "已复制" : "复制"}
                      </button>
                      {message.question && (
                        <button
                          type="button"
                          className="message-action-button"
                          disabled={loading}
                          onClick={() =>
                            void sendAgentMessage(message.question ?? "", {
                              includeUserMessage: false,
                              documentName: message.documentName ?? undefined,
                            })
                          }
                        >
                          重新执行
                        </button>
                      )}
                    </div>

                    {message.usedTools && message.usedTools.length > 0 && (
                      <div className="assistant-section">
                        <p className="assistant-section-title">调用工具</p>
                        <div className="tool-chip-row">
                          {message.usedTools.map((tool) => (
                            <span key={tool} className="tool-chip">
                              {tool}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {formatToolResult(message.toolResult) && (
                      <details className="agent-tool-result">
                        <summary>查看工具执行结果</summary>
                        <pre>{formatToolResult(message.toolResult)}</pre>
                      </details>
                    )}

                    {message.question && (
                      <FeedbackButtons
                        question={message.question}
                        answer={message.content}
                        documentName={message.documentName}
                        sources={[]}
                        usedTools={message.usedTools ?? []}
                      />
                    )}
                  </>
                )}
            </div>
          </div>
        ))}
        {error && <p className="chat-global-error">{error}</p>}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-composer-shell">
        <div className="chat-composer">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="向文献库提问..."
            className="chat-composer-input"
            rows={1}
          />
          <div className="chat-composer-footer">
            <select
              value={selectedDocument}
              onChange={(event) => setSelectedDocument(event.target.value)}
              className="chat-document-select"
            >
              <option value="">全部文档</option>
              {documents.map((document) => (
                <option
                  key={document.document_name}
                  value={document.document_name}
                >
                  {document.document_name}
                </option>
              ))}
            </select>
            <div className="chat-action-row">
              {loading ? (
                <button
                  type="button"
                  className="chat-action-button is-stop"
                  onClick={() => abortControllerRef.current?.abort()}
                >
                  停止
                </button>
              ) : (
                <button
                  type="button"
                  className="chat-action-button is-dark"
                  disabled={!input.trim()}
                  onClick={() => void sendAgentMessage(input)}
                >
                  <span className="send-button-label">发送</span>
                  <span className="send-button-arrow">↑</span>
                </button>
              )}
              <button
                type="button"
                className="chat-action-button is-light"
                onClick={() => {
                  abortControllerRef.current?.abort();
                  setMessages(createInitialMessages());
                  setInput("");
                  setError("");
                }}
              >
                清空
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
