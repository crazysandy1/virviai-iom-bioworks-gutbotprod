import React, { useState, useEffect, useCallback, useRef } from "react";
import apiClient from "../services/apiClient";
import "./DocumentManager.css";

const DocumentManager = ({ conversationId, files, onRemoveFile, onToggleSelection }) => {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [retryingDocId, setRetryingDocId] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const retryTimerRef = useRef(null);
  const fetchDocumentsRef = useRef(null);

  // Fetch document list from backend with retry capability
  const fetchDocuments = useCallback(async (retryCount = 0) => {
    if (!conversationId) return;
    try {
      setIsLoading(true);
      const response = await apiClient.post(
        "/documents",
        { conversationId },
        { retries: 2 }
      );
      setDocuments(response.documents || []);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch documents:", err);
      if (retryCount < 1) {
        retryTimerRef.current = setTimeout(() => fetchDocuments(retryCount + 1), 2000);
      } else {
        setError("Failed to load documents. Try again.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [conversationId]);

  // Store ref so handleRetryFetch can call it without stale closure
  fetchDocumentsRef.current = fetchDocuments;

  useEffect(() => {
    fetchDocuments();
    return () => { if (retryTimerRef.current) clearTimeout(retryTimerRef.current); };
  }, [conversationId, files, fetchDocuments]);

  const handleToggleSelection = useCallback(
    async (docId, currentSelection) => {
      const previousDocuments = documents;

      try {
        // Optimistic update
        setDocuments((prev) =>
          prev.map((doc) =>
            doc.id === docId
              ? { ...doc, selected: !currentSelection }
              : doc
          )
        );

        const response = await apiClient.post(
          "/manage-documents",
          {
            conversationId,
            docId,
            selected: !currentSelection,
          },
          { retries: 1 }
        );

        // Confirm with server response
        setDocuments((prev) =>
          prev.map((doc) =>
            doc.id === docId
              ? { ...doc, selected: response.selected }
              : doc
          )
        );

        // Notify parent component
        if (onToggleSelection) {
          onToggleSelection(docId, response.selected);
        }

        setError(null);
      } catch (err) {
        console.error("Failed to toggle document selection:", err);
        // Revert optimistic update
        setDocuments(previousDocuments);
        setError("Failed to update document selection. Please try again.");

        // Auto-clear error after 4 seconds
        setTimeout(() => setError(null), 4000);
      }
    },
    [documents, conversationId, onToggleSelection]
  );

  const handleRemoveDocument = useCallback(
    async (docId) => {
      if (!window.confirm("Are you sure you want to remove this document?")) {
        return;
      }

      const previousDocuments = documents;

      try {
        // Optimistic update
        setDocuments((prev) => prev.filter((doc) => doc.id !== docId));

        await apiClient.post(
          "/remove-document",
          {
            conversationId,
            docId,
          },
          { retries: 1 }
        );

        // Notify parent component
        if (onRemoveFile) {
          onRemoveFile(docId);
        }

        setError(null);
      } catch (err) {
        console.error("Failed to remove document:", err);
        // Revert optimistic update
        setDocuments(previousDocuments);
        setError("Failed to remove document. Please try again.");

        // Auto-clear error after 4 seconds
        setTimeout(() => setError(null), 4000);
      }
    },
    [documents, conversationId, onRemoveFile]
  );

  const handleRetryFetch = useCallback(() => {
    setError(null);
    fetchDocumentsRef.current?.();
  }, []);

  if (documents.length === 0 && !isLoading) {
    return null;
  }

  const selectedCount = documents.filter((d) => d.selected).length;
  const totalSize = documents.reduce((sum, d) => sum + (d.size || 0), 0);

  return (
    <div className="document-manager-compact">
      {/* Compact Header Bar - Similar to Claude/ChatGPT */}
      <div className="docs-compact-bar">
        <button
          className="docs-toggle-btn"
          onClick={() => setIsExpanded(!isExpanded)}
          aria-expanded={isExpanded}
          title={`${documents.length} document${documents.length !== 1 ? 's' : ''} loaded`}
        >
          <span className="docs-icon">📄</span>
          <span className="docs-label">{documents.length}</span>
          <span className={`docs-chevron ${isExpanded ? 'open' : ''}`}>›</span>
        </button>
        
        {selectedCount > 0 && (
          <span className="docs-status">
            {selectedCount} using
          </span>
        )}
      </div>

      {/* Expanded List - Hidden by Default */}
      {isExpanded && (
        <div className="docs-expanded-list">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className={`doc-compact-item ${doc.selected ? "selected" : "deselected"}`}
            >
              <input
                type="checkbox"
                checked={doc.selected}
                onChange={() => handleToggleSelection(doc.id, doc.selected)}
                className="doc-compact-checkbox"
                id={`doc-${doc.id}`}
                disabled={retryingDocId === doc.id}
              />
              <label htmlFor={`doc-${doc.id}`} className="doc-compact-label">
                <span className="doc-compact-name">{doc.filename}</span>
                <span className="doc-compact-info">
                  {doc.chunks} chunks • {(doc.size / 1024).toFixed(1)} KB
                </span>
              </label>
              <button
                onClick={() => handleRemoveDocument(doc.id)}
                className="doc-compact-remove"
                title="Remove"
                aria-label={`Remove ${doc.filename}`}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="doc-compact-error">
          {error}
        </div>
      )}
    </div>
  );
};

export default DocumentManager;
