export interface StreamingMetadata {
    stream_id: string;
}

export interface CommandOutput {
    command: string;
    output: string;
    size: string;
}

export interface ValidationDeviceResult {
    change_request_id: string;
    device_id: string;
    device_name: string;
    device_status: string;
    validation_status: string;
    pre_check_output: CommandOutput[] | null;
    post_check_output: CommandOutput[] | null;
    llm_analysis: string;
    streaming_metadata: StreamingMetadata | null;
}

// ---------- Validation Tasks (Pagination Demo) ----------

export interface ValidationTask {
    change_request_id: string;
    change_description: string;
    change_status: string;
    created_at: string;
    path: string;
}

export interface PaginatedTasksResponse {
    tasks: ValidationTask[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export type SortOrder = "asc" | "desc" | null;

export interface TaskFilters {
    change_request_id: string;
    change_description: string;
    change_status: string;
    path: string;
}

export interface TaskSortState {
    column: keyof ValidationTask | null;
    order: SortOrder;
}

// ---------- Streaming event types ----------
export interface StreamMetadata {
    change_request_id: string;
    device_id: string;
    device_name: string;
    device_status: string;
    validation_status: string;
    streaming_metadata: StreamingMetadata | null;
}

export interface StreamCommandInfo {
    index: number;
    command: string;
    size: string;
    total_commands: number;
}

export interface StreamDataChunk {
    index: number;
    chunk: string;
    offset: number;
    is_last: boolean;
}

export interface StreamInitialData {
    side: "pre" | "post";
    command_index: number;
    chunk: string;
    offset: number;
    total_size: number;
    has_more: boolean;
}export interface StreamChunkData {
    side: "pre" | "post";
    command_index: number;
    chunk: string;
    offset: number;
    total_size: number;
    has_more: boolean;
}export interface StreamAnalysis {
    analysis: string;
}

export interface StreamError {
    error: string;
}

export interface StreamComplete {
    message: string;
}

export type StreamEventType =
    | "metadata"
    | "pre_check_command"
    | "pre_check_data"
    | "post_check_command"
    | "post_check_data"
    | "initial_data"
    | "chunk_data"
    | "llm_analysis"
    | "initial_complete"
    | "chunk_complete"
    | "complete"
    | "error";

export interface StreamEvent {
    type: StreamEventType;
    data: StreamMetadata | StreamCommandInfo | StreamDataChunk | StreamInitialData | StreamChunkData | StreamAnalysis | StreamError | StreamComplete;
}

// UI state types
export interface CommandOutputState {
    command: string;
    size: string;
    output: string;
    loaded: boolean;
}

export interface CommandStreamState {
    output: string;
    offset: number;
    totalSize: number;
    hasMore: boolean;
    isLoadingMore: boolean;
}

export interface OutputStreamState {
    // Map of command_index to its stream state for pre-check
    preCheckCommands: Map<number, CommandStreamState>;
    // Map of command_index to its stream state for post-check
    postCheckCommands: Map<number, CommandStreamState>;
}export interface ValidationState {
    metadata: StreamMetadata | null;
    preCheckCommands: CommandOutputState[];
    postCheckCommands: CommandOutputState[];
    outputStream: OutputStreamState;
    llmAnalysis: string;
    isStreaming: boolean;
    isComplete: boolean;
    error: string | null;
}
