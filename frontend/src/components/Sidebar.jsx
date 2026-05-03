import { useState, useRef, useEffect, useCallback } from "react";
import { formatDistanceToNow } from "date-fns";
import "./Sidebar.css";

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onCreateNew,
  onDeleteConversation,
  isOpen,
  onToggle,
}) {
  const [hoveredId, setHoveredId] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sidebarWidth, setSidebarWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const sidebarRef = useRef(null);
  const resizeHandleRef = useRef(null);

  // Track mobile state
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Drag resize handler
  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;

      const newWidth = Math.max(220, Math.min(500, e.clientX));
      setSidebarWidth(newWidth);
      
      if (sidebarRef.current) {
        sidebarRef.current.style.width = `${newWidth}px`;
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleConversationSelect = useCallback(
    (convId) => {
      onSelectConversation(convId);
      // Close sidebar on mobile after selection
      if (isMobile && isOpen) {
        onToggle();
      }
    },
    [isMobile, isOpen, onSelectConversation, onToggle]
  );

  return (
    <>
      {/* Mobile overlay */}
      {isMobile && isOpen && (
        <div
          className="sidebar-overlay"
          onClick={onToggle}
          aria-label="Close sidebar"
        />
      )}

      {/* Sidebar toggle button */}
      <button
        className="sidebar-toggle-btn"
        onClick={onToggle}
        aria-label={isOpen ? "Close sidebar" : "Open sidebar"}
        aria-expanded={isOpen}
      >
        <span className="toggle-icon">{isOpen ? "✕" : "☰"}</span>
      </button>

      {/* Sidebar container */}
      <aside
        ref={sidebarRef}
        className={`sidebar-container ${isOpen ? "open" : "closed"}`}
        style={{ width: !isMobile ? `${sidebarWidth}px` : "100%" }}
        role="navigation"
        aria-label="Conversations sidebar"
      >
        {/* Resize handle (desktop only) */}
        {!isMobile && (
          <div
            ref={resizeHandleRef}
            className={`sidebar-resize-handle ${isResizing ? "active" : ""}`}
            onMouseDown={handleMouseDown}
            role="separator"
            aria-label="Resize sidebar"
            aria-orientation="vertical"
          />
        )}

        <div className="sidebar-content">
          {/* Header */}
          <div className="sidebar-header">
            <h2>💬 Conversations</h2>
            <button
              className="new-chat-btn"
              onClick={onCreateNew}
              title="Start new conversation"
              aria-label="Create new conversation"
            >
              ➕
            </button>
          </div>

          {/* Search */}
          <div className="sidebar-search">
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
              aria-label="Search conversations"
            />
          </div>

          {/* Conversations list */}
          <div className="conversations-list">
            {filteredConversations.length === 0 ? (
              <div className="empty-conversations">
                <p>📭 No conversations</p>
                <button
                  className="start-btn"
                  onClick={onCreateNew}
                  aria-label="Create new conversation"
                >
                  Start New
                </button>
              </div>
            ) : (
              filteredConversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`conversation-item ${
                    currentConversationId === conv.id ? "active" : ""
                  }`}
                  onMouseEnter={() => setHoveredId(conv.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  <button
                    className="conversation-button"
                    onClick={() => handleConversationSelect(conv.id)}
                    title={conv.title}
                    aria-current={
                      currentConversationId === conv.id ? "page" : undefined
                    }
                  >
                    <span className="conv-title">{conv.title}</span>
                    <span className="conv-meta">
                      {conv.metadata?.messageCount || 0} messages
                    </span>
                    <span className="conv-time">
                      {formatDistanceToNow(new Date(conv.updatedAt), {
                        addSuffix: true,
                      })}
                    </span>
                  </button>

                  {hoveredId === conv.id && (
                    <button
                      className="delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (
                          window.confirm(
                            "Delete this conversation? This cannot be undone."
                          )
                        ) {
                          onDeleteConversation(conv.id);
                        }
                      }}
                      title="Delete conversation"
                      aria-label={`Delete ${conv.title}`}
                    >
                      🗑️
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
