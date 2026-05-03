import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Request deduplication cache
const requestCache = new Map();
const pendingRequests = new Map();

// Axios instance with defaults
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Track online/offline status
let isOnline = navigator.onLine;
window.addEventListener("online", () => {
  isOnline = true;
  console.log("Back online");
});
window.addEventListener("offline", () => {
  isOnline = false;
  console.log("Offline detected");
});

/**
 * Sanitize input to prevent XSS
 */
const sanitizeInput = (input) => {
  if (typeof input !== "string") return input;
  return input
    .replace(/[<>]/g, "")
    .trim()
    .substring(0, 10000); // Max length
};

/**
 * Generate cache key for requests
 */
const getCacheKey = (method, url, data) => {
  return `${method}:${url}:${JSON.stringify(data || {})}`;
};

/**
 * Retry logic with exponential backoff
 */
const retryWithBackoff = async (
  fn,
  maxRetries = 3,
  initialDelay = 1000,
  backoffMultiplier = 2
) => {
  let lastError;
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (i < maxRetries - 1) {
        const delay = initialDelay * Math.pow(backoffMultiplier, i);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }
  throw lastError;
};

/**
 * Check if response is successful
 */
const isSuccessfulResponse = (response) => {
  return response && response.status >= 200 && response.status < 300;
};

/**
 * API Client with all industry-grade features
 */
const apiClient = {
  /**
   * POST request with deduplication and retry
   */
  post: async (url, data = {}, options = {}) => {
    const { bypassCache = false, retries = 3, cacheTime = 0 } = options;

    if (!isOnline) {
      throw new Error("No internet connection");
    }

    // Sanitize input
    const sanitizedData = typeof data === "object" 
      ? Object.keys(data).reduce((acc, key) => {
          acc[key] = sanitizeInput(data[key]);
          return acc;
        }, {})
      : data;

    const cacheKey = getCacheKey("POST", url, sanitizedData);

    // Check cache
    if (!bypassCache && requestCache.has(cacheKey)) {
      const cached = requestCache.get(cacheKey);
      if (Date.now() - cached.timestamp < cacheTime) {
        return cached.data;
      }
    }

    // Check if request already pending (deduplication)
    if (pendingRequests.has(cacheKey)) {
      return pendingRequests.get(cacheKey);
    }

    // Create request promise with retry
    const requestPromise = retryWithBackoff(
      () => axiosInstance.post(url, sanitizedData),
      retries
    )
      .then((response) => {
        if (cacheTime > 0) {
          requestCache.set(cacheKey, {
            data: response.data,
            timestamp: Date.now(),
          });
        }
        return response.data;
      })
      .finally(() => {
        pendingRequests.delete(cacheKey);
      });

    pendingRequests.set(cacheKey, requestPromise);
    return requestPromise;
  },

  /**
   * POST with FormData (for file uploads)
   */
  postFormData: async (url, formData, onProgress = null, options = {}) => {
    if (!isOnline) {
      throw new Error("No internet connection");
    }

    const { retries = 1 } = options;

    return retryWithBackoff(
      () =>
        axiosInstance.post(url, formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          onUploadProgress: (progressEvent) => {
            if (onProgress) {
              const progress = Math.round(
                (progressEvent.loaded / progressEvent.total) * 100
              );
              onProgress(progress);
            }
          },
        }),
      retries
    ).then((response) => response.data);
  },

  /**
   * Batch multiple requests
   */
  batch: async (requests) => {
    return Promise.all(
      requests.map((req) => apiClient.post(req.url, req.data, req.options))
    );
  },

  /**
   * Clear cache
   */
  clearCache: () => {
    requestCache.clear();
  },

  /**
   * Check online status
   */
  isOnline: () => isOnline,

  /**
   * Get pending requests count
   */
  getPendingCount: () => pendingRequests.size,
};

export default apiClient;
