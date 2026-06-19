export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    status?: 'sending' | 'streaming' | 'complete' | 'error';
}

export interface ChatState {
    messages: ChatMessage[];
    currentStatus: string | null;
    currentProgress: number;
    isLoading: boolean;
    streamingContent: string;
    error: string | null;
}

export type ChatMode = 'websocket' | 'rest' | 'sse';
