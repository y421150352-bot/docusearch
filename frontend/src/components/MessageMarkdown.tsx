import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import "katex/dist/katex.min.css";

import { stripInlineCitations } from "../utils/text";


function normalizeMathDelimiters(content: string) {
  return content
    .replace(/\\\[((?:.|\n)*?)\\\]/g, (_, formula: string) => `$$${formula}$$`)
    .replace(/\\\((.*?)\\\)/g, (_, formula: string) => `$${formula}$`);
}


export function MessageMarkdown({ content }: { content: string }) {
  return (
    <div className="message-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          h1: ({ children }) => <h2 className="message-h2">{children}</h2>,
          h2: ({ children }) => <h3 className="message-h3">{children}</h3>,
          h3: ({ children }) => <h4 className="message-h4">{children}</h4>,
          p: ({ children }) => <p className="message-paragraph">{children}</p>,
          ul: ({ children }) => <ul className="message-list">{children}</ul>,
          ol: ({ children }) => (
            <ol className="message-list is-ordered">{children}</ol>
          ),
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {normalizeMathDelimiters(stripInlineCitations(content))}
      </ReactMarkdown>
    </div>
  );
}
