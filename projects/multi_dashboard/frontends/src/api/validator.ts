import type { StreamEvent, PaginatedTasksResponse, TaskFilters, SortOrder } from "../features/validator/types";

const API_BASE_URL = import.meta.env.VITE_VALIDATOR_API_URL || "http://localhost:8000";

/**
 * Callbacks for SSE stream event handling
 * - onEvent: Per-event handler for incremental data processing
 * - onError: Centralized error handler for both transport and application errors
 * - onComplete: Stream termination signal for cleanup/finalization
 */
export interface StreamCallbacks {
    onEvent?: (event: StreamEvent) => void;
    onError?: (error: Error) => void;
    onComplete?: () => void;
}

/**
 * Core SSE processor - handles ReadableStream to structured events
 * Maintains buffer for incomplete SSE frames across chunk boundaries
 * Auto-invokes error callback for malformed events while preserving stream
 */
async function processSSEStream(
    response: Response,
    callbacks: StreamCallbacks
): Promise<void> {
    const reader = response.body?.getReader();
    if (!reader) throw new Error("Response body is not readable");

    const decoder = new TextDecoder();
    let buffer = "";

    try {
        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                callbacks.onComplete?.();
                break;
            }

            buffer += decoder.decode(value, { stream: true });

            // SSE frame delimiter - incomplete frames remain buffered
            const messages = buffer.split("\n\n");
            buffer = messages.pop() || "";

            for (const message of messages) {
                if (!message.trim().startsWith("data: ")) continue;

                try {
                    const jsonData = message.slice(6); // Strip SSE "data: " prefix
                    const event = JSON.parse(jsonData) as StreamEvent;
                    callbacks.onEvent?.(event);

                    // Propagate application-level errors from stream
                    if (event.type === "error") {
                        const errorData = event.data as { error: string };
                        callbacks.onError?.(new Error(errorData.error));
                    }
                } catch (e) {
                    console.error("SSE frame parse failure:", e);
                }
            }
        }
    } catch (error) {
        callbacks.onError?.(error instanceof Error ? error : new Error(String(error)));
    }
}

/**
 * Initiates validation stream - sends metadata, command structure, and initial 4KB chunks
 * Backend determines optimal chunking based on command boundaries
 * Use fetchNextChunk for subsequent data retrieval on scroll
 */
export async function streamValidationResult(
    changeRequestId: string,
    deviceId: string,
    callbacks: StreamCallbacks
): Promise<void> {
    const url = `${API_BASE_URL}/${changeRequestId}/${deviceId}/stream`;

    try {
        const response = await fetch(url, {
            method: "GET",
            headers: { Accept: "text/event-stream" },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        await processSSEStream(response, callbacks);
    } catch (error) {
        callbacks.onError?.(error instanceof Error ? error : new Error(String(error)));
    }
}

/**
 * Fetches incremental 4KB chunk for specific command when scroll threshold reached
 * Prevents memory bloat by loading output on-demand rather than full dataset upfront
 *
 * @param offset - Byte offset within command's output (tracked per-command)
 * @param side - pre/post check output stream selector
 * @param commandIndex - Command array index for backend retrieval
 */
export async function fetchNextChunk(
    changeRequestId: string,
    deviceId: string,
    offset: number,
    side: "pre" | "post",
    commandIndex: number,
    callbacks: StreamCallbacks
): Promise<void> {
    const params = new URLSearchParams({
        offset: offset.toString(),
        side,
        command_index: commandIndex.toString(),
    });
    const url = `${API_BASE_URL}/${changeRequestId}/${deviceId}/stream?${params}`;

    try {
        const response = await fetch(url, {
            method: "GET",
            headers: { Accept: "text/event-stream" },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        await processSSEStream(response, callbacks);
    } catch (error) {
        callbacks.onError?.(error instanceof Error ? error : new Error(String(error)));
    }
}


// ---------- Validation Tasks API (Pagination Demo) ----------

export interface FetchTasksParams {
    page?: number;
    pageSize?: number;
    sortBy?: string | null;
    sortOrder?: SortOrder;
    filters?: Partial<TaskFilters>;
}

/**
 * Fetches paginated validation tasks with server-side filtering and sorting
 * All query params are optional - defaults: page=1, pageSize=5, no filters/sort
 */
export async function fetchValidationTasks(
    params: FetchTasksParams = {}
): Promise<PaginatedTasksResponse> {
    const { page = 1, pageSize = 5, sortBy, sortOrder, filters } = params;

    const queryParams = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
    });

    // Add sort params if specified
    if (sortBy && sortOrder) {
        queryParams.set("sort_by", sortBy);
        queryParams.set("sort_order", sortOrder);
    }

    // Add filter params (only non-empty values)
    if (filters) {
        if (filters.change_request_id) queryParams.set("change_request_id", filters.change_request_id);
        if (filters.change_description) queryParams.set("change_description", filters.change_description);
        if (filters.change_status) queryParams.set("change_status", filters.change_status);
        if (filters.path) queryParams.set("path", filters.path);
    }

    const url = `${API_BASE_URL}/tasks?${queryParams}`;

    const response = await fetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
}

/**
 * Clears the tasks cache on server - generates fresh random data on next fetch
 */
export async function clearTasksCache(): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/tasks/cache`, {
        method: "DELETE",
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
}
