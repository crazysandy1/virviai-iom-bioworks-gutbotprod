import { useRef, useState, useCallback } from "react";
import "./UploadZone.css";

export default function UploadZone({
  onFileSelect,
  isUploading,
  uploadProgress,
  fileInputRef,
}) {
  const dragRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragCounter = useRef(0);

  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      dragCounter.current = 0;

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        onFileSelect(files[0]);
      }
    },
    [onFileSelect]
  );

  const handleFileInput = useCallback(
    (e) => {
      if (e.target.files && e.target.files.length > 0) {
        onFileSelect(e.target.files[0]);
      }
    },
    [onFileSelect]
  );

  return (
    <div className="upload-zone-container">
      {isUploading ? (
        <div className="upload-progress-compact">
          <div className="progress-icon">📤</div>
          <div className="progress-info">
            <span className="progress-label">Uploading...</span>
            <div className="progress-bar-compact">
              <div
                className="progress-fill-compact"
                style={{ width: `${uploadProgress}%` }}
                role="progressbar"
                aria-valuenow={uploadProgress}
                aria-valuemin="0"
                aria-valuemax="100"
              ></div>
            </div>
            <span className="progress-percent">{uploadProgress}%</span>
          </div>
        </div>
      ) : (
        <div
          ref={dragRef}
          className={`upload-btn-minimal ${isDragging ? "dragging" : ""}`}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          role="button"
          tabIndex={0}
          onClick={() => fileInputRef.current?.click()}
          aria-label="Upload PDF file (click or drag and drop)"
          title="Click to upload or drag and drop a PDF file"
        >
          <span className="upload-icon-mini">📎</span>
          <span className="upload-label-mini">Attach File</span>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileInput}
            className="file-input-hidden"
            aria-label="File input"
          />
        </div>
      )}
    </div>
  );
}
