import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const MarkdownRenderer = ({ content, className = '' }) => {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Custom styling for tables
          table: ({ children, ...props }) => (
            <div className="table-wrapper">
              <table {...props}>{children}</table>
            </div>
          ),
          thead: ({ children, ...props }) => (
            <thead {...props}>{children}</thead>
          ),
          tbody: ({ children, ...props }) => (
            <tbody {...props}>{children}</tbody>
          ),
          tr: ({ children, ...props }) => (
            <tr {...props}>{children}</tr>
          ),
          th: ({ children, ...props }) => (
            <th {...props}>{children}</th>
          ),
          td: ({ children, ...props }) => (
            <td {...props}>{children}</td>
          ),
          // Custom styling for other elements
          p: ({ children, ...props }) => (
            <p {...props}>{children}</p>
          ),
          strong: ({ children, ...props }) => (
            <strong {...props}>{children}</strong>
          ),
          em: ({ children, ...props }) => (
            <em {...props}>{children}</em>
          ),
          code: ({ children, ...props }) => (
            <code {...props}>{children}</code>
          ),
          pre: ({ children, ...props }) => (
            <pre {...props}>{children}</pre>
          ),
          ul: ({ children, ...props }) => (
            <ul {...props}>{children}</ul>
          ),
          ol: ({ children, ...props }) => (
            <ol {...props}>{children}</ol>
          ),
          li: ({ children, ...props }) => (
            <li {...props}>{children}</li>
          ),
          blockquote: ({ children, ...props }) => (
            <blockquote {...props}>{children}</blockquote>
          ),
          h1: ({ children, ...props }) => (
            <h1 {...props}>{children}</h1>
          ),
          h2: ({ children, ...props }) => (
            <h2 {...props}>{children}</h2>
          ),
          h3: ({ children, ...props }) => (
            <h3 {...props}>{children}</h3>
          ),
          h4: ({ children, ...props }) => (
            <h4 {...props}>{children}</h4>
          ),
          h5: ({ children, ...props }) => (
            <h5 {...props}>{children}</h5>
          ),
          h6: ({ children, ...props }) => (
            <h6 {...props}>{children}</h6>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;

