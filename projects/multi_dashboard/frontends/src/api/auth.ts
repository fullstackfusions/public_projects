import axios from "axios";

const AUTH_API_URL =
  import.meta.env.VITE_AUTH_API_URL || "http://localhost:8005";

const authApi = axios.create({
  baseURL: AUTH_API_URL,
  headers: {
    "Content-Type": "application/x-www-form-urlencoded",
  },
});

// Request interceptor to add auth token
authApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
authApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and we haven't tried to refresh yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${AUTH_API_URL}/auth/refresh`,
            {
              refresh_token: refreshToken,
            },
            {
              headers: { "Content-Type": "application/json" },
            }
          );

          const { access_token, refresh_token } = response.data;
          localStorage.setItem("access_token", access_token);
          localStorage.setItem("refresh_token", refresh_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return authApi(originalRequest);
        } catch (refreshError) {
          // Refresh failed, clear tokens
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("user");
          window.location.href = "/login";
          return Promise.reject(refreshError);
        }
      }
    }

    return Promise.reject(error);
  }
);

export interface User {
  username: string;
  email: string;
  full_name: string | null;
  role: string;
  disabled: boolean;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface DevUser {
  username: string;
  role: string;
  email: string;
}

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const response = await authApi.post<LoginResponse>("/auth/login", formData);

    // Store tokens and user
    localStorage.setItem("access_token", response.data.access_token);
    localStorage.setItem("refresh_token", response.data.refresh_token);
    localStorage.setItem("user", JSON.stringify(response.data.user));

    return response.data;
  },

  async logout(): Promise<void> {
    try {
      await authApi.post("/logout");
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await authApi.get<User>("/auth/me");
    return response.data;
  },

  async validateToken(): Promise<{
    valid: boolean;
    username: string;
    role: string;
  }> {
    const response = await authApi.get("/auth/me");
    return response.data;
  },

  async refreshToken(): Promise<TokenResponse> {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      throw new Error("No refresh token available");
    }

    const response = await axios.post<TokenResponse>(
      `${AUTH_API_URL}/auth/refresh`,
      { refresh_token: refreshToken },
      { headers: { "Content-Type": "application/json" } }
    );

    localStorage.setItem("access_token", response.data.access_token);
    localStorage.setItem("refresh_token", response.data.refresh_token);

    return response.data;
  },

  async getDevUsers(): Promise<{ users: DevUser[]; note: string }> {
    const response = await axios.get(`${AUTH_API_URL}/dev/users`);
    return response.data;
  },

  getStoredUser(): User | null {
    const userStr = localStorage.getItem("user");
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch {
        return null;
      }
    }
    return null;
  },

  getAccessToken(): string | null {
    return localStorage.getItem("access_token");
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem("access_token");
  },
};

export default authService;
