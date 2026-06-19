/**
 * Shared axios instance used by all feature API modules.
 *
 * Interceptors:
 *  - Request: attaches JWT from localStorage as `Authorization: Bearer <token>`
 *  - Response: on 401, attempts a token refresh via /auth/refresh; if that fails
 *    clears storage and redirects to /login.
 */
import axios, { type AxiosInstance } from "axios";

const AUTH_API_URL = import.meta.env.VITE_AUTH_API_URL || "http://localhost:8005";

// Generic API client — used by most feature modules
export const apiClient: AxiosInstance = axios.create({
  headers: { "Content-Type": "application/json" },
});

// Auth-specific client — form-encoded by default; same interceptors
export const authApiClient: AxiosInstance = axios.create({
  baseURL: AUTH_API_URL,
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
});

// ---- request interceptor: attach access token --------------------------------

function attachToken(config: Parameters<Parameters<AxiosInstance["interceptors"]["request"]["use"]>[0]>[0]) {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}

apiClient.interceptors.request.use(attachToken, (err) => Promise.reject(err));
authApiClient.interceptors.request.use(attachToken, (err) => Promise.reject(err));

// ---- response interceptor: refresh on 401 ------------------------------------

async function refreshOnUnauthorized(
  error: unknown,
  instance: AxiosInstance,
): Promise<unknown> {
  const axiosError = error as { config?: { _retry?: boolean }; response?: { status: number } };
  const originalRequest = axiosError.config;

  if (axiosError.response?.status === 401 && originalRequest && !originalRequest._retry) {
    originalRequest._retry = true;
    const refreshToken = localStorage.getItem("refresh_token");

    if (refreshToken) {
      try {
        const resp = await axios.post(
          `${AUTH_API_URL}/auth/refresh`,
          { refresh_token: refreshToken },
          { headers: { "Content-Type": "application/json" } },
        );
        const { access_token, refresh_token: newRefresh } = resp.data as {
          access_token: string;
          refresh_token: string;
        };
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", newRefresh);
        (originalRequest as Record<string, unknown>).headers = {
          ...(originalRequest as Record<string, unknown>).headers,
          Authorization: `Bearer ${access_token}`,
        };
        return instance(originalRequest as Parameters<AxiosInstance>[0]);
      } catch {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        window.location.href = "/login";
      }
    }
  }

  return Promise.reject(error);
}

apiClient.interceptors.response.use(
  (r) => r,
  (err) => refreshOnUnauthorized(err, apiClient),
);
authApiClient.interceptors.response.use(
  (r) => r,
  (err) => refreshOnUnauthorized(err, authApiClient),
);
