import { useCallback, useEffect, useRef, useState } from 'react';
import {
    WebSocketChatClient,
    RestAPIChatClient,
    SSEChatClient,
    ChatCallbacks,
} from '../../api/chat_go';
import type { ChatMessage, ChatState, ChatMode } from './types';

const initialState: ChatState = {
    messages: [],
    currentStatus: null,
    currentProgress: 0,
    isLoading: false,
    streamingContent: '',
    error: null,
};

export function useChat(mode: ChatMode) {
    const [state, setState] = useState<ChatState>(initialState);

    const wsClientRef = useRef<WebSocketChatClient | null>(null);
    const restClientRef = useRef<RestAPIChatClient | null>(null);
    const sseClientRef = useRef<SSEChatClient | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [state.messages, state.streamingContent]);

    // Initialize WebSocket client
    useEffect(() => {
        if (mode === 'websocket') {
            const client = new WebSocketChatClient();
            wsClientRef.current = client;

            // Show connecting status
            setState((prev) => ({ ...prev, currentStatus: '🔌 Connecting to Go WebSocket...' }));

            const callbacks: ChatCallbacks = {
                onReceived: (data) => {
                    setState((prev) => ({ ...prev, currentStatus: 'Message received' }));
                },
                onStatus: (data) => {
                    setState((prev) => ({
                        ...prev,
                        currentStatus: data.status || null,
                        currentProgress: data.progress || 0,
                    }));
                },
                onChunk: (data) => {
                    setState((prev) => ({
                        ...prev,
                        streamingContent: data.content || '',
                        currentStatus: null,
                    }));
                },
                onComplete: (data) => {
                    setState((prev) => {
                        const newMessage: ChatMessage = {
                            id: data.message_id || Date.now().toString(),
                            role: 'assistant',
                            content: data.content || '',
                            timestamp: new Date().toISOString(),
                            status: 'complete',
                        };
                        return {
                            ...prev,
                            messages: [...prev.messages, newMessage],
                            isLoading: false,
                            streamingContent: '',
                            currentStatus: null,
                            currentProgress: 0,
                        };
                    });
                },
                onError: (error) => {
                    setState((prev) => ({
                        ...prev,
                        error,
                        isLoading: false,
                        currentStatus: null,
                    }));
                },
            };

            client.connect(callbacks)
                .then(() => {
                    setState((prev) => ({ ...prev, currentStatus: null, error: null }));
                })
                .catch((error) => {
                    setState((prev) => ({
                        ...prev,
                        error: 'Failed to connect to Go WebSocket. Make sure the backend is running on port 8004.',
                        currentStatus: null
                    }));
                });

            return () => {
                client.disconnect();
            };
        }
    }, [mode]);

    // Initialize REST client
    useEffect(() => {
        if (mode === 'rest') {
            restClientRef.current = new RestAPIChatClient();
        }
    }, [mode]);

    // Initialize SSE client
    useEffect(() => {
        if (mode === 'sse') {
            sseClientRef.current = new SSEChatClient();
        }

        return () => {
            if (sseClientRef.current) {
                sseClientRef.current.abort();
            }
        };
    }, [mode]);

    const sendMessage = useCallback(
        async (content: string) => {
            if (!content.trim()) return;

            // Add user message
            const userMessage: ChatMessage = {
                id: Date.now().toString(),
                role: 'user',
                content: content.trim(),
                timestamp: new Date().toISOString(),
                status: 'complete',
            };

            setState((prev) => ({
                ...prev,
                messages: [...prev.messages, userMessage],
                isLoading: true,
                error: null,
                streamingContent: '',
                currentStatus: null,
                currentProgress: 0,
            }));

            const callbacks: ChatCallbacks = {
                onReceived: () => {
                    setState((prev) => ({ ...prev, currentStatus: 'Message received' }));
                },
                onStatus: (data) => {
                    setState((prev) => ({
                        ...prev,
                        currentStatus: data.status || null,
                        currentProgress: data.progress || 0,
                    }));
                },
                onChunk: (data) => {
                    setState((prev) => ({
                        ...prev,
                        streamingContent: data.content || '',
                        currentStatus: null,
                    }));
                },
                onComplete: (data) => {
                    setState((prev) => {
                        const newMessage: ChatMessage = {
                            id: data.message_id || Date.now().toString(),
                            role: 'assistant',
                            content: data.content || '',
                            timestamp: new Date().toISOString(),
                            status: 'complete',
                        };
                        return {
                            ...prev,
                            messages: [...prev.messages, newMessage],
                            isLoading: false,
                            streamingContent: '',
                            currentStatus: null,
                            currentProgress: 0,
                        };
                    });
                },
                onError: (error) => {
                    setState((prev) => ({
                        ...prev,
                        error,
                        isLoading: false,
                        currentStatus: null,
                    }));
                },
            };

            switch (mode) {
                case 'websocket':
                    if (wsClientRef.current?.isConnected()) {
                        wsClientRef.current.sendMessage(content.trim());
                    } else {
                        setState((prev) => ({
                            ...prev,
                            error: 'WebSocket not connected',
                            isLoading: false,
                        }));
                    }
                    break;

                case 'rest':
                    if (restClientRef.current) {
                        await restClientRef.current.sendMessage(content.trim(), callbacks);
                    }
                    break;

                case 'sse':
                    if (sseClientRef.current) {
                        await sseClientRef.current.sendMessage(content.trim(), callbacks);
                    }
                    break;
            }
        },
        [mode]
    );

    const clearMessages = useCallback(() => {
        setState(initialState);
    }, []);

    return {
        ...state,
        sendMessage,
        clearMessages,
        messagesEndRef,
    };
}
