import { useState } from "react";

import type { SourceItem } from "../types";

type SourceListProps = {
  sources: SourceItem[];
};

function SourceQuote({ quote }: { quote: string }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div>
      <p className={expanded ? "source-quote" : "source-quote is-collapsed"}>
        {quote}
      </p>
      {quote.length > 140 && (
        <button
          type="button"
          className="source-inline-button"
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "收起" : "展开"}
        </button>
      )}
    </div>
  );
}

export function SourceList({ sources }: SourceListProps) {
  const [expanded, setExpanded] = useState(false);

  if (sources.length === 0) {
    return null;
  }

  return (
    <div className="assistant-section">
      <button
        type="button"
        className="source-toggle"
        onClick={() => setExpanded((current) => !current)}
      >
        {expanded
          ? `收起引用来源 ${sources.length} 条`
          : `查看引用来源 ${sources.length} 条`}
      </button>

      {expanded && (
        <div className="source-list">
          {sources.map((source, index) => (
            <div
              key={`${source.document_name}-${source.page_number}-${index}`}
              className="source-card"
            >
              <div className="source-card-header">
                <div>
                  <p className="source-doc-name">{source.document_name}</p>
                  <p className="source-meta">
                    第 {source.page_number} 页
                    {source.retrieval_type ? ` · ${source.retrieval_type}` : ""}
                  </p>
                </div>
                <div className="source-score-group">
                  {typeof source.score === "number" && (
                    <span className="source-score-tag">
                      score {source.score.toFixed(3)}
                    </span>
                  )}
                  {typeof source.rerank_score === "number" && (
                    <span className="source-score-tag">
                      rerank {source.rerank_score.toFixed(3)}
                    </span>
                  )}
                </div>
              </div>
              <SourceQuote quote={source.quote} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
