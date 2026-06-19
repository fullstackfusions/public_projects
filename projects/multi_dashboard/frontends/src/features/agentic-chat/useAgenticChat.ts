import { useCallback, useEffect, useRef, useState } from 'react';
import { getMessageStatus, postMessage } from '../../api/agentic_chat';
import type { AgentStep, ChatMessage, ChatState } from './types';

const POLL_INTERVAL_MS = 500;

const initialState: ChatState = {
    messages: [],
    isLoading: false,
    liveSteps: [],
    conversationId: null,
    error: null,
};

export function useAgenticChat() {
    const [state, setState] = useState<ChatState>(initialState);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    // Keep conversationId in a ref so the poll closure always sees the latest value
    const conversationIdRef = useRef<string | null>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [state.messages, state.liveSteps]);

    const stopPolling = () => {
        if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }
    };

    const sendMessage = useCallback(async (content: string) => {
        if (!content.trim()) return;

        const userMessage: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: content.trim(),
            timestamp: new Date().toISOString(),
        };

        setState(prev => ({
            ...prev,
            messages: [...prev.messages, userMessage],
            isLoading: true,
            liveSteps: [],
            error: null,
        }));

        try {
            const { msg_id, conversation_id } = await postMessage(
                content.trim(),
                conversationIdRef.current ?? undefined,
            );

            conversationIdRef.current = conversation_id;
            setState(prev => ({ ...prev, conversationId: conversation_id }));

            stopPolling();
            pollRef.current = setInterval(async () => {
                try {
                    const status = await getMessageStatus(msg_id);

                    setState(prev => ({
                        ...prev,
                        liveSteps: status.steps as AgentStep[],
                    }));

                    if (status.status === 'complete') {
                        stopPolling();
                        const assistantMessage: ChatMessage = {
                            id: msg_id,
                            role: 'assistant',
                            content: status.result ?? '',
                            timestamp: new Date().toISOString(),
                            steps: status.steps as AgentStep[],
                        };
                        setState(prev => ({
                            ...prev,
                            messages: [...prev.messages, assistantMessage],
                            isLoading: false,
                            liveSteps: [],
                        }));
                    } else if (status.status === 'error') {
                        stopPolling();
                        setState(prev => ({
                            ...prev,
                            isLoading: false,
                            liveSteps: [],
                            error: status.error ?? 'An error occurred',
                        }));
                    }
                } catch (err) {
                    stopPolling();
                    setState(prev => ({
                        ...prev,
                        isLoading: false,
                        liveSteps: [],
                        error: err instanceof Error ? err.message : 'Polling failed',
                    }));
                }
            }, POLL_INTERVAL_MS);
        } catch (err) {
            setState(prev => ({
                ...prev,
                isLoading: false,
                error: err instanceof Error ? err.message : 'Failed to send message',
            }));
        }
    }, []);

    const clearMessages = useCallback(() => {
        stopPolling();
        conversationIdRef.current = null;
        setState(initialState);
    }, []);

    useEffect(() => () => stopPolling(), []);

    return { ...state, sendMessage, clearMessages, messagesEndRef };
}
