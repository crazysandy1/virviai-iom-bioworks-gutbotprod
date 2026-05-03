/**
 * Storage utilities for localStorage management
 */

export const StorageService = {
  /**
   * Set item in localStorage
   */
  setItem: (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      console.error("Storage error:", error);
      return false;
    }
  },

  /**
   * Get item from localStorage
   */
  getItem: (key, defaultValue = null) => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.error("Storage error:", error);
      return defaultValue;
    }
  },

  /**
   * Remove item from localStorage
   */
  removeItem: (key) => {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      console.error("Storage error:", error);
      return false;
    }
  },

  /**
   * Clear all localStorage
   */
  clear: () => {
    try {
      localStorage.clear();
      return true;
    } catch (error) {
      console.error("Storage error:", error);
      return false;
    }
  },

  /**
   * Check if item exists
   */
  hasItem: (key) => {
    return localStorage.getItem(key) !== null;
  },
};

/**
 * File utilities
 */
export const FileService = {
  /**
   * Format file size
   */
  formatFileSize: (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  },

  /**
   * Validate file
   */
  validateFile: (file, maxSize = 50 * 1024 * 1024) => {
    const errors = [];

    if (!file) {
      errors.push("No file selected");
      return { valid: false, errors };
    }

    if (!file.type.includes("pdf")) {
      errors.push("Only PDF files are allowed");
    }

    if (file.size > maxSize) {
      errors.push(`File size exceeds maximum limit (${FileService.formatFileSize(maxSize)})`);
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  },

  /**
   * Download file
   */
  downloadFile: (content, filename, type = "text/plain") => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },
};

/**
 * Date utilities
 */
export const DateService = {
  /**
   * Format date
   */
  formatDate: (date, format = "short") => {
    const d = new Date(date);
    if (format === "short") {
      return d.toLocaleDateString();
    }
    return d.toLocaleString();
  },

  /**
   * Get time ago
   */
  getTimeAgo: (date) => {
    const now = new Date();
    const then = new Date(date);
    const seconds = Math.floor((now - then) / 1000);

    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " years ago";

    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " months ago";

    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days ago";

    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours ago";

    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " minutes ago";

    return "just now";
  },
};

/**
 * String utilities
 */
export const StringService = {
  /**
   * Truncate string
   */
  truncate: (str, length = 100) => {
    return str.length > length ? str.substring(0, length) + "..." : str;
  },

  /**
   * Capitalize string
   */
  capitalize: (str) => {
    return str.charAt(0).toUpperCase() + str.slice(1);
  },

  /**
   * Generate slug
   */
  generateSlug: (str) => {
    return str
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, "")
      .replace(/[\s_-]+/g, "-")
      .replace(/^-+|-+$/g, "");
  },
};

/**
 * Validation utilities
 */
export const ValidationService = {
  /**
   * Check if email is valid
   */
  isValidEmail: (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  },

  /**
   * Check if URL is valid
   */
  isValidUrl: (url) => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  },

  /**
   * Check if string is empty
   */
  isEmpty: (str) => {
    return !str || str.trim().length === 0;
  },
};

/**
 * API Error handler
 */
export const handleApiError = (error) => {
  if (error.response) {
    // Server responded with error status
    return {
      message: error.response.data?.error || "Server error occurred",
      status: error.response.status,
      data: error.response.data,
    };
  } else if (error.request) {
    // Request made but no response
    return {
      message: "No response from server. Check your connection.",
      status: 0,
      data: null,
    };
  } else {
    // Error in request setup
    return {
      message: error.message || "An error occurred",
      status: 0,
      data: null,
    };
  }
};

/**
 * Deep merge objects
 */
export const deepMerge = (target, source) => {
  const output = Object.assign({}, target);
  if (isObject(target) && isObject(source)) {
    Object.keys(source).forEach((key) => {
      if (isObject(source[key])) {
        if (!(key in target)) {
          Object.assign(output, { [key]: source[key] });
        } else {
          output[key] = deepMerge(target[key], source[key]);
        }
      } else {
        Object.assign(output, { [key]: source[key] });
      }
    });
  }
  return output;
};

const isObject = (item) => {
  return item && typeof item === "object" && !Array.isArray(item);
};

export default {
  StorageService,
  FileService,
  DateService,
  StringService,
  ValidationService,
  handleApiError,
  deepMerge,
};
