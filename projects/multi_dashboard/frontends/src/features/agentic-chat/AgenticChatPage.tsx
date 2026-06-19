import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import {
    Box,
    Chip,
    Divider,
    IconButton,
    Paper,
    Typography,
} from '@mui/material';
import { ChatInput } from './components/ChatInput';
import { ChatMessage } from './components/ChatMessage';
import { StepTracker } from './components/StepTracker';
import { useAgenticChat } from './useAgenticChat';

const SUB_AGENTS = [
    { label: 'InventoryAgent', color: '#0ea5e9' },
    { label: 'NetworkAgent', color: '#10b981' },
    { label: 'GrafanaAgent', color: '#f59e0b' },
    { label: 'FlowIqAgent', color: '#8b5cf6' },
];

export function AgenticChatPage() {
    const {
        messages,
        isLoading,
        liveSteps,
        error,
        sendMessage,
        clearMessages,
        messagesEndRef,
    } = useAgenticChat();

    return (
        <Box
            sx={{
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                gap: 2,
                overflow: 'hidden',
            }}
        >
            {/* Page header */}
            <Box sx={{ flexShrink: 0 }}>
                <Typography variant="h4" fontWeight="bold" gutterBottom>
                    Agentic Chat
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                    Multi-agent assistant powered by LangGraph. Queries are routed to
                    specialised sub-agents and results are synthesised by the central agent.
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                    <Typography variant="caption" color="text.disabled" sx={{ mr: 0.5 }}>
                        Sub-agents:
                    </Typography>
                    {SUB_AGENTS.map((a) => (
                        <Chip
                            key={a.label}
                            label={a.label}
                            size="small"
                            variant="outlined"
                            sx={{ borderColor: a.color, color: a.color, fontSize: '0.7rem' }}
                        />
                    ))}
                </Box>
            </Box>

            {/* Chat panel */}
            <Paper
                elevation={3}
                sx={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    borderRadius: 4,
                    overflow: 'hidden',
                    minHeight: 0,
                }}
            >
                {/* Header */}
                <Box
                    sx={{
                        p: 2,
                        background: 'linear-gradient(to right, #6366f1, #8b5cf6)',
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        flexShrink: 0,
                    }}
                >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                        <Box
                            sx={{
                                p: 1,
                                bgcolor: 'rgba(255,255,255,0.2)',
                                borderRadius: 2,
                                display: 'flex',
                            }}
                        >
                            <SmartToyIcon sx={{ fontSize: 20 }} />
                        </Box>
                        <Box>
                            <Typography variant="subtitle1" fontWeight="bold" lineHeight={1.2}>
                                Central Agent
                            </Typography>
                            <Typography variant="caption" sx={{ opacity: 0.8 }}>
                                LangGraph · ReAct · MCP tool integrations
                            </Typography>
                        </Box>
                    </Box>
                    <IconButton
                        onClick={clearMessages}
                        sx={{
                            color: 'white',
                            '&:hover': { bgcolor: 'rgba(255,255,255,0.2)' },
                        }}
                        size="small"
                        title="Clear conversation"
                    >
                        <DeleteOutlineIcon sx={{ fontSize: 16 }} />
                    </IconButton>
                </Box>

                {/* Messages area */}
                <Box sx={{ flex: 1, overflowY: 'auto', p: 2, minHeight: 0 }}>
                    {messages.length === 0 && !isLoading && (
                        <Box
                            sx={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                height: '100%',
                                color: 'text.disabled',
                                flexDirection: 'column',
                                gap: 1,
                            }}
                        >
                            <SmartToyIcon sx={{ fontSize: 40, opacity: 0.3 }} />
                            <Typography variant="body2">
                                Ask about your network infrastructure…
                            </Typography>
                        </Box>
                    )}

                    {messages.map((msg) => (
                        <ChatMessage key={msg.id} message={msg} />
                    ))}

                    <StepTracker steps={liveSteps} isLoading={isLoading} />

                    {error && (
                        <Paper
                            variant="outlined"
                            sx={{
                                p: 1.5,
                                mb: 1.5,
                                bgcolor: '#fff1f2',
                                borderColor: '#fecdd3',
                                color: '#e11d48',
                            }}
                        >
                            <Typography variant="body2">{error}</Typography>
                        </Paper>
                    )}

                    <div ref={messagesEndRef} />
                </Box>

                {/* Input */}
                <Divider />
                <Box sx={{ p: 2, bgcolor: 'background.paper', flexShrink: 0 }}>
                    <ChatInput onSend={sendMessage} disabled={isLoading} />
                </Box>
            </Paper>
        </Box>
    );
}
