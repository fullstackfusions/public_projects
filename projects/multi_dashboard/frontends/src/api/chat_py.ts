/**
 * Chat API Client
 *
 * Provides three different communication methods:
 * 1. WebSocket - Real-time bidirectional
 * 2. REST API - Traditional request/response with polling
 * 3. SSE - Server-Sent Events for streaming
 */

const CHAT_API_BASE =
  import.meta.env.VITE_CHAT_API_URL || "http://localhost:8003";
const CHAT_WS_BASE = import.meta.env.VITE_CHAT_WS_URL || "ws://localhost:8003";

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ---------- Types ----------

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  status?: string;
}

export interface StatusUpdate {
  type: "received" | "status" | "chunk" | "complete" | "error";
  status?: string;
  content?: string;
  progress?: number;
  message_id?: string;
  conversation_id?: string;
  is_final?: boolean;
  timestamp: string;
}

export interface ChatCallbacks {
  onReceived?: (data: StatusUpdate) => void;
  onStatus?: (data: StatusUpdate) => void;
  onChunk?: (data: StatusUpdate) => void;
  onComplete?: (data: StatusUpdate) => void;
  onError?: (error: string) => void;
}

// ---------- WebSocket Client ----------

export class WebSocketChatClient {
  private ws: WebSocket | null = null;
  private conversationId: string | null = null;
  private callbacks: ChatCallbacks = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

  connect(callbacks: ChatCallbacks): Promise<void> {
    this.callbacks = callbacks;

    return new Promise((resolve, reject) => {
      this.attemptConnect(resolve, reject);
    });
  }

  private attemptConnect(
    resolve: () => void,
    reject: (error: unknown) => void,
  ): void {
    try {
      console.log(
        `WebSocket connecting to ${CHAT_WS_BASE}/ws/chat (attempt ${this.reconnectAttempts + 1})`,
      );
      this.ws = new WebSocket(`${CHAT_WS_BASE}/ws/chat`);

      this.ws.onopen = () => {
        console.log("WebSocket connected");
        this.reconnectAttempts = 0;
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const data: StatusUpdate = JSON.parse(event.data);

          if (data.conversation_id) {
            this.conversationId = data.conversation_id;
          }

          switch (data.type) {
            case "received":
              this.callbacks.onReceived?.(data);
              break;
            case "status":
              this.callbacks.onStatus?.(data);
              break;
            case "chunk":
              this.callbacks.onChunk?.(data);
              break;
            case "complete":
              this.callbacks.onComplete?.(data);
              break;
            case "error":
              this.callbacks.onError?.(data.content || "Unknown error");
              break;
          }
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      this.ws.onclose = (event) => {
        console.log("WebSocket disconnected", event.code, event.reason);

        // Try to reconnect if not manually closed
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          const delay = Math.min(
            1000 * Math.pow(2, this.reconnectAttempts - 1),
            10000,
          );
          console.log(`Reconnecting in ${delay}ms...`);
          this.reconnectTimeout = setTimeout(() => {
            this.attemptConnect(resolve, reject);
          }, delay);
        } else {
          this.callbacks.onError?.(
            "WebSocket connection failed after multiple attempts",
          );
          reject(new Error("WebSocket connection failed"));
        }
      };
    } catch (error) {
      reject(error);
    }
  }

  sendMessage(message: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.callbacks.onError?.("WebSocket not connected");
      return;
    }

    this.ws.send(
      JSON.stringify({
        message,
        conversation_id: this.conversationId,
      }),
    );
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto-reconnect
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getConversationId(): string | null {
    return this.conversationId;
  }
}

// ---------- REST API Client ----------

export class RestAPIChatClient {
  private conversationId: string | null = null;
  private pollingInterval: number | null = null;

  async sendMessage(message: string, callbacks: ChatCallbacks): Promise<void> {
    try {
      // Send initial request
      const response = await fetch(`${CHAT_API_BASE}/api/chat/async`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({
          message,
          conversation_id: this.conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      this.conversationId = data.conversation_id;

      callbacks.onReceived?.({
        type: "received",
        message_id: data.request_id,
        conversation_id: data.conversation_id,
        timestamp: data.timestamp,
      });

      // Start polling for status
      await this.pollForStatus(data.request_id, callbacks);
    } catch (error) {
      callbacks.onError?.(
        error instanceof Error ? error.message : "Unknown error",
      );
    }
  }

  private async pollForStatus(
    requestId: string,
    callbacks: ChatCallbacks,
  ): Promise<void> {
    let lastStatusCount = 0;

    const poll = async (): Promise<boolean> => {
      try {
        const response = await fetch(
          `${CHAT_API_BASE}/api/chat/status/${requestId}`,
          {
            headers: { ...getAuthHeaders() },
          },
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Send any new status updates
        if (data.statuses && data.statuses.length > lastStatusCount) {
          for (let i = lastStatusCount; i < data.statuses.length; i++) {
            callbacks.onStatus?.({
              type: "status",
              status: data.statuses[i].status,
              progress: data.statuses[i].progress,
              timestamp: data.statuses[i].timestamp,
            });
          }
          lastStatusCount = data.statuses.length;
        }

        if (data.status === "complete" && data.response) {
          callbacks.onComplete?.({
            type: "complete",
            content: data.response.content,
            message_id: data.response.id,
            conversation_id: data.conversation_id,
            timestamp: data.response.timestamp,
          });
          return true; // Done
        }

        if (data.status === "error") {
          callbacks.onError?.(data.error || "Unknown error");
          return true; // Done
        }

        return false; // Keep polling
      } catch (error) {
        callbacks.onError?.(
          error instanceof Error ? error.message : "Polling error",
        );
        return true; // Stop on error
      }
    };

    // Poll every 300ms
    return new Promise((resolve) => {
      const interval = setInterval(async () => {
        const done = await poll();
        if (done) {
          clearInterval(interval);
          resolve();
        }
      }, 300);
    });
  }

  // Synchronous version (no status updates, just final response)
  async sendMessageSync(message: string): Promise<ChatMessage> {
    const response = await fetch(`${CHAT_API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify({
        message,
        conversation_id: this.conversationId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    this.conversationId = data.conversation_id;

    return data.message;
  }

  getConversationId(): string | null {
    return this.conversationId;
  }

  clearConversation(): void {
    this.conversationId = null;
  }
}

// ---------- SSE Client ----------

export class SSEChatClient {
  private conversationId: string | null = null;
  private abortController: AbortController | null = null;

  async sendMessage(message: string, callbacks: ChatCallbacks): Promise<void> {
    // Abort any existing request
    if (this.abortController) {
      this.abortController.abort();
    }

    this.abortController = new AbortController();

    try {
      const response = await fetch(`${CHAT_API_BASE}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({
          message,
          conversation_id: this.conversationId,
        }),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process complete events
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        let currentEvent = "";
        let currentData = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7);
          } else if (line.startsWith("data: ")) {
            currentData = line.slice(6);

            try {
              const data: StatusUpdate = JSON.parse(currentData);

              if (data.conversation_id) {
                this.conversationId = data.conversation_id;
              }

              switch (data.type) {
                case "received":
                  callbacks.onReceived?.(data);
                  break;
                case "status":
                  callbacks.onStatus?.(data);
                  break;
                case "chunk":
                  callbacks.onChunk?.(data);
                  break;
                case "complete":
                  callbacks.onComplete?.(data);
                  break;
                case "error":
                  callbacks.onError?.(data.content || "Unknown error");
                  break;
              }
            } catch (e) {
              // Ignore parse errors for incomplete data
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return; // Ignore abort errors
      }
      callbacks.onError?.(
        error instanceof Error ? error.message : "Unknown error",
      );
    }
  }

  abort(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  getConversationId(): string | null {
    return this.conversationId;
  }

  clearConversation(): void {
    this.conversationId = null;
  }
}
