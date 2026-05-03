import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    if (import.meta.env.VITE_DEBUG_MODE === "true") {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  (error) => {
    console.error("[API] Request error:", error);
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    if (import.meta.env.VITE_DEBUG_MODE === "true") {
      console.log(`[API] Response: ${response.status}`, response.data);
    }
    return response;
  },
  (error) => {
    const errorMessage =
      error.response?.data?.error ||
      error.response?.data?.message ||
      error.message ||
      "An error occurred";

    console.error("[API] Response error:", errorMessage);

    // Create custom error with more details
    const customError = new Error(errorMessage);
    customError.status = error.response?.status;
    customError.data = error.response?.data;
    customError.originalError = error;

    return Promise.reject(customError);
  }
);

/**
 * Upload a PDF file
 */
export const uploadFile = async (file, conversationId, onProgress) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("conversationId", conversationId);

  try {
    const response = await apiClient.post("/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded / progressEvent.total) * 100
          );
          onProgress(progress);
        }
      },
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * Send a chat message
 */
export const sendMessage = async (message, conversationId, files = []) => {
  try {
    const response = await apiClient.post("/chat", {
      message,
      conversationId,
      files,
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * Handle API errors consistently
 */
const handleApiError = (error) => {
  if (error.status === 408 || error.originalError?.code === "ECONNABORTED") {
    return new Error("Request timed out. Please try again.");
  }
  if (error.status === 413) {
    return new Error("File size is too large. Maximum is 50MB.");
  }
  if (error.status === 400) {
    return new Error(error.message || "Invalid request. Please check your input.");
  }
  if (error.status === 500) {
    return new Error(
      "Server error. Please try again later or contact support."
    );
  }
  return error;
};

export default apiClient;
