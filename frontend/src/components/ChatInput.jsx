import { useEffect, useRef } from "react";
import "./ChatInput.css";

export default function ChatInput({
  message,
  onMessageChange,
  onSendMessage,
  isLoading,
  disabled,
}) {
  const inputRef = useRef(null);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && !disabled && message.trim()) {
        onSendMessage();
      }
    }
  };

  const handleInputChange = (e) => {
    onMessageChange(e.target.value);
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + "px";
  };

  return (
    <div className="chat-input-container">
      <div className="input-wrapper">
        <textarea
          ref={inputRef}
          value={message}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          placeholder="Ask about your document... (Shift+Enter for new line)"
          disabled={disabled || isLoading}
          className="message-input"
          rows={1}
        />

        <button
          onClick={onSendMessage}
          disabled={disabled || isLoading || !message.trim()}
          className="send-btn"
          title="Send message (Enter)"
        >
          {isLoading ? (
            <>
              <span className="loading-spinner"></span>
              Sending...
            </>
          ) : (
            <>
              <span>Send</span>
              <span className="send-icon">✈️</span>
            </>
          )}
        </button>
      </div>

      {disabled && (
        <div className="input-hint">
          Please upload a document to start asking questions.
        </div>
      )}

      <div className="input-tips">
        <p>💡 Tip: You can ask questions about your uploaded document</p>
      </div>
    </div>
  );
}
