export interface AgentStep {
    agent: string;
    action: 'started' | 'tool_called' | 'completed' | 'error' | string;
    detail: string | null;
    timestamp: string;
}

export interface MessageResponse {
    msg_id: string;
    conversation_id: string;
    status: 'processing' | 'complete' | 'error';
    timestamp: string;
}

export interface MessageStatusResponse {
    msg_id: string;
    conversation_id: string;
    status: 'processing' | 'complete' | 'error';
    steps: AgentStep[];
    result: string | null;
    error: string | null;
    created_at: string;
    updated_at: string;
}

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    steps?: AgentStep[];
}

export interface ChatState {
    messages: ChatMessage[];
    isLoading: boolean;
    liveSteps: AgentStep[];
    conversationId: string | null;
    error: string | null;
}
