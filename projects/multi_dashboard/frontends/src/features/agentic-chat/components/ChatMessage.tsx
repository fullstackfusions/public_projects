import { Box, Paper, Typography } from '@mui/material';
import { format } from 'date-fns';
import type { ChatMessage as ChatMessageType } from '../types';

interface Props {
    message: ChatMessageType;
}

export function ChatMessage({ message }: Props) {
    const isUser = message.role === 'user';

    return (
        <Box
            sx={{
                display: 'flex',
                justifyContent: isUser ? 'flex-end' : 'flex-start',
                mb: 1.5,
            }}
        >
            <Paper
                elevation={0}
                sx={{
                    maxWidth: '82%',
                    borderRadius: 3,
                    px: 2,
                    py: 1.5,
                    bgcolor: isUser ? 'primary.main' : 'grey.100',
                    color: isUser ? 'primary.contrastText' : 'text.primary',
                    borderBottomRightRadius: isUser ? 4 : 16,
                    borderBottomLeftRadius: isUser ? 16 : 4,
                }}
            >
                {/* Render assistant content preserving whitespace/newlines for markdown-like display */}
                <Typography
                    variant="body2"
                    component="div"
                    sx={{
                        whiteSpace: 'pre-wrap',
                        lineHeight: 1.75,
                        fontFamily: isUser ? 'inherit' : 'inherit',
                        '& code': {
                            fontFamily: 'monospace',
                            bgcolor: isUser ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.06)',
                            px: 0.5,
                            borderRadius: 0.5,
                            fontSize: '0.85em',
                        },
                    }}
                >
                    {message.content}
                </Typography>
                <Typography
                    variant="caption"
                    sx={{
                        display: 'block',
                        mt: 0.5,
                        opacity: 0.65,
                        textAlign: 'right',
                    }}
                >
                    {format(new Date(message.timestamp), 'HH:mm:ss')}
                </Typography>
            </Paper>
        </Box>
    );
}
