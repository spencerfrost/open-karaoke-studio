/**
 * Base API configuration and utility functions
 */

// Base API URL - will be replaced with environment variable
const API_BASE_URL = "http://localhost:5000";
export const API_BASE = API_BASE_URL;

// Types
export type HttpMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

interface ApiOptions {
  method?: HttpMethod;
  headers?: Record<string, string>;
  body?: unknown;
}

export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
}

/**
 * Base API request function
 */
export async function apiRequest<T>(
  endpoint: string,
  options: ApiOptions = {},
): Promise<ApiResponse<T>> {
  try {
    const { method = "GET", headers = {}, body } = options;

    const requestOptions: RequestInit = {
      method,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      credentials: "include",
    };

    if (body) {
      requestOptions.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, requestOptions);

    // Handle non-JSON responses
    const contentType = response.headers.get("Content-Type") || "";
    if (!contentType.includes("application/json")) {
      if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`);
      }
      // For download endpoints or other non-JSON responses
      return { data: response as any, error: null };
    }

    const data = await response.json();

    if (!response.ok) {
      const errorMessage =
        data.error || `API request failed with status ${response.status}`;
      throw new Error(errorMessage);
    }

    return { data, error: null };
  } catch (error) {
    console.error("API request error:", error);
    return {
      data: null,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

/**
 * File upload function
 */
export async function uploadFile<T>(
  endpoint: string,
  file: File,
  additionalData?: Record<string, any>,
): Promise<ApiResponse<T>> {
  try {
    const formData = new FormData();
    formData.append("audio_file", file);

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, String(value));
      });
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });

    const data = await response.json();

    if (!response.ok) {
      const errorMessage =
        data.error ?? `File upload failed with status ${response.status}`;
      throw new Error(errorMessage);
    }

    return { data, error: null };
  } catch (error) {
    console.error("File upload error:", error);
    return {
      data: null,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

/**
 * Download file function
 */
export async function downloadFile(
  endpoint: string,
  filename: string,
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error(`Download failed with status ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Download error:", error);
    throw error;
  }
}
