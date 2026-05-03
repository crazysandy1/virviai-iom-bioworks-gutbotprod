import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { v4 as uuidv4 } from "uuid";
import "./App.css";
import ChatContainer from "./components/ChatContainer";
import UploadZone from "./components/UploadZone";
import ChatInput from "./components/ChatInput";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import LoadingSpinner from "./components/LoadingSpinner";
import ErrorBoundary from "./components/ErrorBoundary";
import DocumentManager from "./components/DocumentManager";
import apiClient from "./services/apiClient";

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const uploadAbortController = useRef(null);

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  // Adjust sidebar visibility on resize
  useEffect(() => {
    const handleWindowResize = () => {
      const isMobile = window.innerWidth <= 768;
      setSidebarOpen(!isMobile);
    };

    window.addEventListener("resize", handleWindowResize);
    return () => window.removeEventListener("resize", handleWindowResize);
  }, []);

  // Load conversations from localStorage on mount
  useEffect(() => {
    const loadConversations = () => {
      try {
        const saved = localStorage.getItem("conversations");
        if (saved) {
          const parsed = JSON.parse(saved);
          setConversations(Array.isArray(parsed) ? parsed : []);
        }
      } catch (err) {
        console.error("Failed to load conversations:", err);
        setError("Failed to load conversation history");
      }
    };

    loadConversations();
  }, []);

  // Persist conversations to localStorage
  useEffect(() => {
    try {
      if (conversations.length > 0) {
        localStorage.setItem("conversations", JSON.stringify(conversations));
      }
    } catch (err) {
      console.error("Failed to save conversations:", err);
    }
  }, [conversations]);

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 0);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [conversations, scrollToBottom]);

  // Create new conversation
  const createNewConversation = useCallback(() => {
    const newConversation = {
      id: uuidv4(),
      title: "New Conversation",
      messages: [],
      files: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      metadata: {
        messageCount: 0,
        fileCount: 0,
      },
    };
    setConversations((prev) => [newConversation, ...prev]);
    setCurrentConversationId(newConversation.id);
    setError(null);
  }, []);

  // Initialize first conversation
  useEffect(() => {
    if (conversations.length === 0) {
      createNewConversation();
    } else if (!currentConversationId) {
      setCurrentConversationId(conversations[0].id);
    }
  }, [conversations, currentConversationId, createNewConversation]);

  const currentConversation = useMemo(
    () => conversations.find((c) => c.id === currentConversationId),
    [conversations, currentConversationId]
  );

  // Upload file with AbortController support
  const uploadFile = useCallback(
    async (file) => {
      if (!currentConversationId || !isOnline) {
        setError(isOnline ? "No conversation selected" : "No internet connection");
        return;
      }

      // Validate file
      if (!file.type.includes("pdf")) {
        setError("Please upload a PDF file only.");
        return;
      }

      if (file.size > 50 * 1024 * 1024) {
        setError("File size must be less than 50MB.");
        return;
      }

      setIsUploading(true);
      setUploadProgress(0);
      setError(null);

      try {
        uploadAbortController.current = new AbortController();
        const formData = new FormData();
        formData.append("file", file);
        formData.append("conversationId", currentConversationId);

        const response = await apiClient.postFormData(
          "/upload",
          formData,
          (progress) => setUploadProgress(progress),
          { retries: 1 }
        );

        const fileData = {
          id: response.docId || uuidv4(),
          backendDocId: response.docId,
          name: file.name,
          size: file.size,
          type: file.type,
          uploadedAt: new Date().toISOString(),
          status: "completed",
          chunks: response.chunks || 0,
          source: response.source || "unknown",
          selected: true,
        };

        setConversations((prev) =>
          prev.map((conv) => {
            if (conv.id === currentConversationId) {
              return {
                ...conv,
                files: [...conv.files, fileData],
                metadata: {
                  ...conv.metadata,
                  fileCount: conv.metadata.fileCount + 1,
                },
                updatedAt: new Date().toISOString(),
              };
            }
            return conv;
          })
        );

        const systemMessage = {
          id: uuidv4(),
          role: "system",
          content: `✓ Document "${file.name}" uploaded successfully (${response.chunks} chunks).`,
          timestamp: new Date().toISOString(),
          metadata: {
            fileId: fileData.id,
            type: "upload_success",
          },
        };

        setConversations((prev) =>
          prev.map((conv) => {
            if (conv.id === currentConversationId) {
              return {
                ...conv,
                messages: [...conv.messages, systemMessage],
                metadata: {
                  ...conv.metadata,
                  messageCount: conv.metadata.messageCount + 1,
                },
              };
            }
            return conv;
          })
        );

        setTimeout(() => setError(null), 3000);
      } catch (err) {
        console.error("Upload error:", err);
        const errorMessage =
          err.response?.data?.error ||
          err.message ||
          "Failed to upload file. Please try again.";
        setError(errorMessage);

        const errorChatMessage = {
          id: uuidv4(),
          role: "system",
          content: `✗ Upload failed: ${errorMessage}`,
          timestamp: new Date().toISOString(),
          metadata: { type: "upload_error" },
        };

        setConversations((prev) =>
          prev.map((conv) => {
            if (conv.id === currentConversationId) {
              return {
                ...conv,
                messages: [...conv.messages, errorChatMessage],
                metadata: {
                  ...conv.metadata,
                  messageCount: conv.metadata.messageCount + 1,
                },
              };
            }
            return conv;
          })
        );
      } finally {
        setIsUploading(false);
        setUploadProgress(0);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        uploadAbortController.current = null;
      }
    },
    [currentConversationId, isOnline]
  );

  // Send message with retry logic
  const sendMessage = useCallback(
    async (retryCount = 0) => {
      if (!message.trim() || !currentConversationId || !isOnline) {
        if (!isOnline) setError("No internet connection");
        return;
      }

      setError(null);
      const userMessage = {
        id: uuidv4(),
        role: "user",
        content: message,
        timestamp: new Date().toISOString(),
        metadata: { sources: [] },
      };

      setConversations((prev) =>
        prev.map((conv) => {
          if (conv.id === currentConversationId) {
            return {
              ...conv,
              messages: [...conv.messages, userMessage],
              title:
                conv.messages.length === 0
                  ? message.substring(0, 50)
                  : conv.title,
              metadata: {
                ...conv.metadata,
                messageCount: conv.metadata.messageCount + 1,
              },
              updatedAt: new Date().toISOString(),
            };
          }
          return conv;
        })
      );

      setMessage("");
      setIsLoading(true);

      try {
        const chatHistory = (currentConversation?.messages || [])
          .filter((m) => m.role === "user" || m.role === "assistant")
          .slice(-10)
          .map((m) => ({ role: m.role, content: m.content }));

        const response = await apiClient.post(
          "/chat",
          {
            message: message.trim(),
            conversationId: currentConversationId,
            chatHistory,
          },
          { retries: 2 }
        );

        const assistantMessage = {
          id: uuidv4(),
          role: "assistant",
          content: response.response,
          timestamp: new Date().toISOString(),
          metadata: {
            sources: response.sources || [],
            chunksUsed: response.chunks_used || 0,
            documentsUsed: response.documents_used || 0,
            model: response.model || "bedrock",
          },
        };

        setConversations((prev) =>
          prev.map((conv) => {
            if (conv.id === currentConversationId) {
              return {
                ...conv,
                messages: [...conv.messages, assistantMessage],
                metadata: {
                  ...conv.metadata,
                  messageCount: conv.metadata.messageCount + 1,
                },
              };
            }
            return conv;
          })
        );
      } catch (err) {
        console.error("Chat error:", err);
        const errorMessage = err.message || "Failed to send message. Please try again.";
        setError(errorMessage);

        // Add error message to chat
        const errorMessage_ = {
          id: uuidv4(),
          role: "system",
          content: `✗ Error: ${errorMessage}`,
          timestamp: new Date().toISOString(),
          metadata: { type: "chat_error" },
        };

        setConversations((prev) =>
          prev.map((conv) => {
            if (conv.id === currentConversationId) {
              return {
                ...conv,
                messages: [...conv.messages, errorMessage_],
              };
            }
            return conv;
          })
        );

        if (retryCount < 1) {
          setTimeout(() => {
            setMessage(userMessage.content);
          }, 500);
        }
      } finally {
        setIsLoading(false);
      }
    },
    [message, currentConversationId, isOnline, currentConversation?.files]
  );

  // Delete conversation
  const deleteConversation = useCallback((convId) => {
    setConversations((prev) => prev.filter((c) => c.id !== convId));
    if (currentConversationId === convId) {
      setCurrentConversationId(null);
    }
  }, [currentConversationId]);

  return (
    <ErrorBoundary onError={(err) => setError(err.message)}>
      <div className="app-container">
        {!isOnline && (
          <div className="offline-banner">
            <span>📡 No internet connection</span>
          </div>
        )}

        {error && (
          <div className="error-banner">
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="close-btn"
              aria-label="Close error"
            >
              ×
            </button>
          </div>
        )}

        <div className="app-content">
          <Sidebar
            conversations={conversations}
            currentConversationId={currentConversationId}
            onSelectConversation={setCurrentConversationId}
            onCreateNew={createNewConversation}
            onDeleteConversation={deleteConversation}
            isOpen={sidebarOpen}
            onToggle={() => setSidebarOpen(!sidebarOpen)}
          />

          <div className="main-content">
            {currentConversation ? (
              <>
                <Header
                  conversation={currentConversation}
                  onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
                  pendingRequests={apiClient.getPendingCount()}
                />

                {currentConversation.messages.length === 0 ? (
                  <div className="empty-state">
                    <h3>Start a new conversation</h3>
                    <p>Upload a PDF document to get started.</p>
                  </div>
                ) : (
                  <ChatContainer
                    messages={currentConversation.messages}
                    messagesEndRef={messagesEndRef}
                  />
                )}

                <div className="chat-bottom-section">
                  {currentConversation.files.length > 0 && (
                    <DocumentManager
                      conversationId={currentConversationId}
                      files={currentConversation.files}
                      onRemoveFile={(docId) => {
                        setConversations((prev) =>
                          prev.map((conv) => {
                            if (conv.id === currentConversationId) {
                              return {
                                ...conv,
                                files: conv.files.filter(
                                  (f) => f.backendDocId !== docId
                                ),
                                metadata: {
                                  ...conv.metadata,
                                  fileCount: Math.max(
                                    0,
                                    conv.metadata.fileCount - 1
                                  ),
                                },
                              };
                            }
                            return conv;
                          })
                        );
                      }}
                      onToggleSelection={(docId, selected) => {
                        setConversations((prev) =>
                          prev.map((conv) => {
                            if (conv.id === currentConversationId) {
                              return {
                                ...conv,
                                files: conv.files.map((f) =>
                                  f.backendDocId === docId
                                    ? { ...f, selected }
                                    : f
                                ),
                              };
                            }
                            return conv;
                          })
                        );
                      }}
                    />
                  )}

                  {!currentConversation.files.length ? (
                    <UploadZone
                      onFileSelect={uploadFile}
                      isUploading={isUploading}
                      uploadProgress={uploadProgress}
                      fileInputRef={fileInputRef}
                    />
                  ) : (
                    <div className="upload-zone-compact">
                      <button
                        className="add-file-btn"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                        aria-label="Add another document"
                      >
                        + Add Another Document
                      </button>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf"
                        onChange={(e) => {
                          if (e.target.files?.[0]) {
                            uploadFile(e.target.files[0]);
                          }
                        }}
                        className="file-input-hidden"
                        aria-label="Upload file"
                      />
                      {isUploading && (
                        <div className="mini-progress-bar">
                          <div
                            className="progress-fill"
                            style={{ width: `${uploadProgress}%` }}
                          ></div>
                          <span className="progress-text">{uploadProgress}%</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <ChatInput
                  message={message}
                  onMessageChange={setMessage}
                  onSendMessage={sendMessage}
                  isLoading={isLoading}
                  disabled={
                    isLoading ||
                    isUploading ||
                    !currentConversation.files.length ||
                    !isOnline
                  }
                  isOnline={isOnline}
                />
              </>
            ) : (
              <div className="no-conversation">
                <h2>No conversation selected</h2>
                <button onClick={createNewConversation} className="primary-btn">
                  Create New Conversation
                </button>
              </div>
            )}
          </div>
        </div>

        {isLoading && <LoadingSpinner />}
      </div>
    </ErrorBoundary>
  );
}

export default App;
