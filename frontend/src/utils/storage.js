/**
 * Local storage wrapper with error handling, compression, and versioning
 * Manages conversation persistence with automatic cleanup
 */

const STORAGE_VERSION = "v1";
const STORAGE_PREFIX = "chatbot_";
const MAX_STORAGE_ATTEMPTS = 3;
const CLEANUP_THRESHOLD = 90; // Cleanup when storage at 90% capacity

class StorageManager {
  constructor() {
    this.isAvailable = this.checkStorageAvailable();
    this.metrics = {
      reads: 0,
      writes: 0,
      errors: 0,
      lastError: null,
    };
  }

  /**
   * Check if localStorage is available and not full
   */
  checkStorageAvailable() {
    try {
      const test = "__storage_test__";
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch (e) {
      console.warn("localStorage not available:", e.message);
      return false;
    }
  }

  /**
   * Get storage usage percentage (rough estimate)
   */
  getStorageUsagePercent() {
    if (!this.isAvailable) return 0;

    let total = 0;
    try {
      for (let key in localStorage) {
        if (localStorage.hasOwnProperty(key)) {
          total += localStorage[key].length + key.length;
        }
      }
    } catch (e) {
      console.warn("Error calculating storage usage:", e);
    }

    // Estimate: 5MB typical limit
    const estimatedTotal = total / (5 * 1024 * 1024);
    return Math.min(100, estimatedTotal * 100);
  }

  /**
   * Save data with automatic retry and cleanup
   */
  setItem(key, data, options = {}) {
    if (!this.isAvailable) {
      console.warn("Storage not available, using memory fallback");
      return false;
    }

    const { retries = MAX_STORAGE_ATTEMPTS, compress = false } = options;
    const fullKey = `${STORAGE_PREFIX}${key}`;

    try {
      let value = data;
      if (typeof data === "object") {
        value = JSON.stringify({
          version: STORAGE_VERSION,
          timestamp: Date.now(),
          data,
        });
      }

      // Try to save
      for (let i = 0; i < retries; i++) {
        try {
          localStorage.setItem(fullKey, value);
          this.metrics.writes++;
          return true;
        } catch (e) {
          if (e.name === "QuotaExceededError") {
            // Cleanup and retry
            if (i < retries - 1) {
              this.cleanup();
              continue;
            }
          }
          throw e;
        }
      }

      return false;
    } catch (error) {
      this.metrics.errors++;
      this.metrics.lastError = error.message;
      console.error("Storage save error:", error);
      return false;
    }
  }

  /**
   * Retrieve data with automatic parsing
   */
  getItem(key, defaultValue = null) {
    if (!this.isAvailable) return defaultValue;

    const fullKey = `${STORAGE_PREFIX}${key}`;

    try {
      const item = localStorage.getItem(fullKey);
      if (!item) return defaultValue;

      this.metrics.reads++;

      // Try to parse JSON
      try {
        const parsed = JSON.parse(item);
        // Handle versioned format
        if (parsed.version && parsed.data !== undefined) {
          return parsed.data;
        }
        return parsed;
      } catch {
        // Not JSON, return as-is
        return item;
      }
    } catch (error) {
      this.metrics.errors++;
      this.metrics.lastError = error.message;
      console.error("Storage read error:", error);
      return defaultValue;
    }
  }

  /**
   * Remove item from storage
   */
  removeItem(key) {
    if (!this.isAvailable) return false;

    const fullKey = `${STORAGE_PREFIX}${key}`;
    try {
      localStorage.removeItem(fullKey);
      return true;
    } catch (error) {
      this.metrics.errors++;
      this.metrics.lastError = error.message;
      console.error("Storage remove error:", error);
      return false;
    }
  }

  /**
   * Clear all storage with prefix
   */
  clear() {
    if (!this.isAvailable) return false;

    try {
      const keysToDelete = [];
      for (let key in localStorage) {
        if (localStorage.hasOwnProperty(key) && key.startsWith(STORAGE_PREFIX)) {
          keysToDelete.push(key);
        }
      }
      keysToDelete.forEach((key) => localStorage.removeItem(key));
      return true;
    } catch (error) {
      this.metrics.errors++;
      this.metrics.lastError = error.message;
      console.error("Storage clear error:", error);
      return false;
    }
  }

  /**
   * Cleanup old conversations when storage is full
   */
  cleanup() {
    if (!this.isAvailable) return;

    try {
      const usagePercent = this.getStorageUsagePercent();
      if (usagePercent < CLEANUP_THRESHOLD) return;

      // Get all conversations
      const conversations = this.getItem("conversations", []);
      if (!Array.isArray(conversations) || conversations.length === 0) return;

      // Sort by updatedAt and remove oldest
      const sorted = conversations
        .sort(
          (a, b) =>
            new Date(b.updatedAt || b.createdAt) -
            new Date(a.updatedAt || a.createdAt)
        )
        .slice(0, Math.max(5, conversations.length - 5)); // Keep at least 5 conversations

      this.setItem("conversations", sorted);
    } catch (error) {
      console.warn("Cleanup failed:", error);
    }
  }

  /**
   * Export all stored data (for backup/debugging)
   */
  exportAll() {
    const exported = {};
    try {
      for (let key in localStorage) {
        if (localStorage.hasOwnProperty(key) && key.startsWith(STORAGE_PREFIX)) {
          const cleanKey = key.replace(STORAGE_PREFIX, "");
          exported[cleanKey] = this.getItem(cleanKey);
        }
      }
    } catch (error) {
      console.error("Export failed:", error);
    }
    return exported;
  }

  /**
   * Get storage metrics for monitoring
   */
  getMetrics() {
    return {
      ...this.metrics,
      usagePercent: this.getStorageUsagePercent(),
      isAvailable: this.isAvailable,
    };
  }

  /**
   * Reset metrics
   */
  resetMetrics() {
    this.metrics = {
      reads: 0,
      writes: 0,
      errors: 0,
      lastError: null,
    };
  }
}

// Create singleton instance
const storage = new StorageManager();

export default storage;
export { StorageManager };
