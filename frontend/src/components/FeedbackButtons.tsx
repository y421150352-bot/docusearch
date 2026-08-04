import { useState } from "react";

import { submitFeedback } from "../api";
import type { SourceItem } from "../types";

type FeedbackButtonsProps = {
  question: string;
  answer: string;
  documentName?: string | null;
  sources?: SourceItem[];
  usedTools?: string[];
};

const DISLIKE_REASONS = [
  "回答太简单",
  "引用不准确",
  "没有回答问题",
  "检索来源不相关",
  "内容可能有幻觉",
  "其他",
];

export function FeedbackButtons({
  question,
  answer,
  documentName,
  sources = [],
  usedTools = [],
}: FeedbackButtonsProps) {
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [showDislikeForm, setShowDislikeForm] = useState(false);
  const [selectedReason, setSelectedReason] = useState(DISLIKE_REASONS[0]);
  const [comment, setComment] = useState("");
  const [message, setMessage] = useState("");
  const disabled = submitted || submitting || !answer.trim();

  async function handleLike() {
    try {
      setSubmitting(true);
      setMessage("");
      await submitFeedback({
        question,
        answer,
        document_name: documentName ?? null,
        sources,
        used_tools: usedTools,
        feedback_type: "like",
        feedback_reason: "helpful",
        feedback_comment: "",
      });
      setSubmitted(true);
      setShowDislikeForm(false);
      setMessage("已反馈");
    } catch {
      setMessage("反馈提交失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDislikeSubmit() {
    try {
      setSubmitting(true);
      setMessage("");
      await submitFeedback({
        question,
        answer,
        document_name: documentName ?? null,
        sources,
        used_tools: usedTools,
        feedback_type: "dislike",
        feedback_reason: selectedReason,
        feedback_comment: comment.trim(),
      });
      setSubmitted(true);
      setShowDislikeForm(false);
      setMessage("已反馈，感谢你的反馈");
    } catch {
      setMessage("反馈提交失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="feedback-block">
      <div className="feedback-actions">
        <button
          type="button"
          onClick={handleLike}
          disabled={disabled}
          className="feedback-button"
        >
          有帮助
        </button>
        <button
          type="button"
          onClick={() => setShowDislikeForm((current) => !current)}
          disabled={disabled}
          className="feedback-button"
        >
          需改进
        </button>
        {message && <span className="feedback-message">{message}</span>}
      </div>

      {showDislikeForm && !submitted && (
        <div className="feedback-form">
          <label className="feedback-label" htmlFor={`feedback-reason-${question}`}>
            反馈原因
          </label>
          <select
            id={`feedback-reason-${question}`}
            value={selectedReason}
            onChange={(event) => setSelectedReason(event.target.value)}
            className="feedback-select"
          >
            {DISLIKE_REASONS.map((reason) => (
              <option key={reason} value={reason}>
                {reason}
              </option>
            ))}
          </select>

          <textarea
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder="可以补充哪里不准确，或者你希望系统怎样回答。"
            className="feedback-textarea"
            rows={3}
          />

          <div className="feedback-form-actions">
            <button
              type="button"
              onClick={handleDislikeSubmit}
              disabled={submitting}
              className="chat-action-button is-primary"
            >
              提交反馈
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
