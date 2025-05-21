import {
  useQuery,
  useMutation,
  UseQueryOptions,
  UseMutationOptions,
} from "@tanstack/react-query";

// --- Helper function for GET requests ---
const apiGet = async <T>(url: string): Promise<T> => {
  const response = await fetch(`/api/${url}`, {
    credentials: "include", // Added credentials
  });
  if (!response.ok) {
    let errorMessage = `HTTP error! Status: ${response.status}`;
    try {
      const errorData: any = await response.json(); // Type as 'any' temporarily, refine later
      errorMessage = errorData?.message || errorMessage; // Adjust based on your backend's error format
    } catch (jsonError: any) {
      // Type as 'any' temporarily, refine later
      console.error("Error parsing error response:", jsonError);
    }
    throw new Error(errorMessage);
  }
  return await response.json();
};

/**
 * Sends an HTTP request to the API.
 *
 * @template T - The type of the response data.
 * @template V - The type of the request body data.
 * @param {string} url - The endpoint URL (relative to the API base URL).
 * @param {string} method - The HTTP method (e.g., 'GET', 'POST', etc.).
 * @param {V | null} [data=null] - The request body data (optional).
 * @returns {Promise<T>} - A promise resolving to the response data.
 * @throws {Error} - Throws an error if the response is not ok.
 */
const apiSend = async <T, V>(
  url: string,
  method: string,
  data: V | null = null
): Promise<T> => {
  const response = await fetch(`/api/${url}`, {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: data ? JSON.stringify(data) : null,
    credentials: "include", // Added credentials
  });
  if (!response.ok) {
    let errorMessage = `HTTP error! Status: ${response.status}`;
    try {
      const errorData: any = await response.json(); // Type as 'any' temporarily, refine later
      errorMessage = errorData?.message || errorMessage; // Adjust based on your backend's error format
    } catch (jsonError: any) {
      // Type as 'any' temporarily, refine later
      console.error("Error parsing error response:", jsonError);
    }
    throw new Error(errorMessage);
  }
  return await response.json();
};

/**
 * React Query hook for fetching data from the API.
 *
 * @template T - The type of the response data.
 * @template TQueryKey - The type of the query key (must be a readonly array).
 * @param {TQueryKey} queryKey - The unique key for the query.
 * @param {string} url - The endpoint URL (relative to the API base URL).
 * @param {Omit<UseQueryOptions<T, Error, T, TQueryKey>, 'queryKey' | 'queryFn'>} [options] - Additional options for the query.
 * @returns {UseQueryResult<T, Error>} - The result of the query.
 */
export function useApiQuery<T, TQueryKey extends readonly unknown[]>(
  queryKey: TQueryKey,
  url: string,
  options?: Omit<
    UseQueryOptions<T, Error, T, TQueryKey>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery<T, Error, T, TQueryKey>({
    queryKey,
    queryFn: () => apiGet<T>(url),
    ...options,
  });
}

/**
 * React Query hook for performing mutations (e.g., POST, PUT, DELETE).
 *
 * @template TData - The type of the response data.
 * @template TVariables - The type of the request body data.
 * @template TContext - The type of the context (optional).
 * @param {string} url - The endpoint URL (relative to the API base URL).
 * @param {'post' | 'put' | 'patch' | 'delete'} method - The HTTP method.
 * @param {Omit<UseMutationOptions<TData, Error, TVariables, TContext>, 'mutationFn'>} [options] - Additional options for the mutation.
 * @returns {UseMutationResult<TData, Error, TVariables, TContext>} - The result of the mutation.
 */
export function useApiMutation<TData, TVariables, TContext = unknown>(
  url: string,
  method: "post" | "put" | "patch" | "delete",
  options?: Omit<
    UseMutationOptions<TData, Error, TVariables, TContext>,
    "mutationFn"
  >
) {
  return useMutation<TData, Error, TVariables, TContext>({
    mutationFn: (data: TVariables) =>
      apiSend<TData, TVariables>(url, method, data),
    ...options,
  });
}

/**
 * Uploads a file to the API.
 *
 * @template T - The type of the response data.
 * @param {string} url - The endpoint URL (relative to the API base URL).
 * @param {File} file - The file to upload.
 * @param {Record<string, unknown>} [additionalData] - Additional data to send with the file (optional).
 * @returns {Promise<T>} - A promise resolving to the response data.
 * @throws {Error} - Throws an error if the response is not ok.
 */
export const uploadFile = async <T>(
  url: string,
  file: File,
  metadata?: Record<string, unknown>
): Promise<T> => {
  const formData = new FormData();
  formData.append("audio_file", file);

  if (metadata) {
    Object.entries(metadata).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        formData.append(key, value as string | Blob);
      }
    });
  }

  const response = await fetch(`/api/${url}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = `HTTP error! Status: ${response.status}`;
    try {
      const errorData: { message?: string } = await response.json();
      errorMessage = errorData?.message || errorMessage;
    } catch (jsonError: unknown) {
      console.error("Error parsing error response:", jsonError);
    }
    throw new Error(errorMessage);
  }

  return await response.json();
};
