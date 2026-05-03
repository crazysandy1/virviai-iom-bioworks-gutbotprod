/**
 * Input validation and sanitization utilities
 * Prevents XSS, injection attacks, and validates file types
 */

// XSS prevention: sanitize HTML content
export const sanitizeHtml = (text) => {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
};

// Validate PDF file
export const validatePdf = (file) => {
  if (!file) return { valid: false, error: "No file selected" };

  const maxSize = 50 * 1024 * 1024; // 50MB
  if (file.size > maxSize) {
    return {
      valid: false,
      error: `File size exceeds 50MB limit (${(file.size / 1024 / 1024).toFixed(1)}MB)`,
    };
  }

  if (!file.type.includes("pdf")) {
    return {
      valid: false,
      error: "Only PDF files are supported",
    };
  }

  return { valid: true };
};

// Validate text input
export const validateMessage = (text) => {
  if (!text || !text.trim()) {
    return { valid: false, error: "Message cannot be empty" };
  }

  if (text.trim().length > 5000) {
    return {
      valid: false,
      error: "Message exceeds 5000 character limit",
    };
  }

  return { valid: true, message: text.trim() };
};

// Sanitize user input to prevent injection
export const sanitizeInput = (input) => {
  if (!input) return "";
  return String(input)
    .trim()
    .replace(/[<>]/g, "") // Remove potential HTML tags
    .substring(0, 5000); // Limit length
};

// Validate conversation ID (UUID format)
export const validateConversationId = (id) => {
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(id);
};

// Validate document ID (UUID format)
export const validateDocumentId = (id) => {
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(id);
};

// Check if API response is valid
export const validateApiResponse = (response) => {
  if (!response) {
    return { valid: false, error: "Invalid response from server" };
  }

  if (response.error) {
    return { valid: false, error: response.error };
  }

  return { valid: true };
};

// Rate limiter for user actions
export class RateLimiter {
  constructor(maxCalls, windowMs) {
    this.maxCalls = maxCalls;
    this.windowMs = windowMs;
    this.calls = [];
  }

  isAllowed(key = "default") {
    const now = Date.now();
    this.calls = this.calls.filter((call) => call.timestamp > now - this.windowMs);

    const callsWithKey = this.calls.filter((call) => call.key === key);
    if (callsWithKey.length >= this.maxCalls) {
      return false;
    }

    this.calls.push({ key, timestamp: now });
    return true;
  }

  reset() {
    this.calls = [];
  }
}

// Common rate limiters
export const messageLimiter = new RateLimiter(1, 500); // Max 1 message per 500ms
export const uploadLimiter = new RateLimiter(1, 1000); // Max 1 upload per 1s
export const deleteLimiter = new RateLimiter(3, 5000); // Max 3 deletes per 5s

export default {
  sanitizeHtml,
  validatePdf,
  validateMessage,
  sanitizeInput,
  validateConversationId,
  validateDocumentId,
  validateApiResponse,
  RateLimiter,
  messageLimiter,
  uploadLimiter,
  deleteLimiter,
};
