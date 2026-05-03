import { useEffect } from "react";
import ReactMarkdown from "react-markdown";
import "./ChatContainer.css";

export default function ChatContainer({ messages, messagesEndRef }) {
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, messagesEndRef]);

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="chat-container">
      {messages.map((msg, index) => (
        <div
          key={msg.id || index}
          className={`message message-${msg.role}`}
          data-type={msg.metadata?.type || ""}
        >
          <div className="message-avatar">
            {msg.role === "user" ? "👤" : msg.role === "assistant" ? "🤖" : "ℹ️"}
          </div>

          <div className="message-content-wrapper">
            <div className="message-header">
              <span className="message-role">
                {msg.role === "user"
                  ? "You"
                  : msg.role === "assistant"
                    ? "GutBot"
                    : "System"}
              </span>
              <span className="message-time">{formatTime(msg.timestamp)}</span>
            </div>

            <div className="message-body">
              {msg.role === "assistant" ? (
                <ReactMarkdown className="markdown-content">
                  {msg.content}
                </ReactMarkdown>
              ) : (
                <p className="message-text">{msg.content}</p>
              )}
            </div>

            {msg.metadata?.sources && msg.metadata.sources.length > 0 && (
              <div className="message-sources">
                <details>
                  <summary>
                    📚 Sources ({msg.metadata.sources.length})
                  </summary>
                  <ul>
                    {msg.metadata.sources.map((source, i) => (
                      <li key={i}>
                        <strong>
                          {typeof source === "string" ? source : source.file || "Document"}
                        </strong>
                        {source.page && <span> - Page {source.page}</span>}
                        {source.confidence && (
                          <span className="confidence">
                            ({Math.round(source.confidence * 100)}%)
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </details>
              </div>
            )}

            {msg.metadata?.model && (
              <div className="message-metadata">
                <span className="meta-item">🔬 {msg.metadata.model}</span>
                {msg.metadata.chunksUsed && (
                  <span className="meta-item">📖 {msg.metadata.chunksUsed} chunks used</span>
                )}
                {msg.metadata.tokens && (
                  <span className="meta-item">⚡ {msg.metadata.tokens} tokens</span>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}
