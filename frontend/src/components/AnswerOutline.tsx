import type { KeyPoint } from "../types";
import { stripInlineCitations } from "../utils/text";

export function AnswerOutline({ keyPoints }: { keyPoints: KeyPoint[] }) {
  if (keyPoints.length === 0) {
    return null;
  }

  return (
    <div className="answer-outline">
      <p className="assistant-section-title">回答结构</p>
      <div className="answer-outline-grid">
        {keyPoints.slice(0, 5).map((item, index) => (
          <div key={`${item.title}-${index}`} className="answer-outline-card">
            <p className="answer-outline-title">
              {stripInlineCitations(item.title)}
            </p>
            <p className="answer-outline-content">
              {stripInlineCitations(item.content)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
