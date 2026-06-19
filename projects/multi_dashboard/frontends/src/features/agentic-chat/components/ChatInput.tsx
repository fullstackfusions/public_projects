import SendIcon from '@mui/icons-material/Send';
import { IconButton, InputAdornment, TextField } from '@mui/material';
import { FormEvent, KeyboardEvent, useState } from 'react';

interface Props {
    onSend: (message: string) => void;
    disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
    const [value, setValue] = useState('');

    const submit = () => {
        const trimmed = value.trim();
        if (trimmed && !disabled) {
            onSend(trimmed);
            setValue('');
        }
    };

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        submit();
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
        // Enter submits; Shift+Enter inserts newline
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit();
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <TextField
                fullWidth
                multiline
                maxRows={5}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={disabled}
                placeholder={
                    disabled
                        ? 'Agents are working…'
                        : 'Ask about your network infrastructure… (Enter to send)'
                }
                size="small"
                InputProps={{
                    endAdornment: (
                        <InputAdornment position="end">
                            <IconButton
                                type="submit"
                                disabled={disabled || !value.trim()}
                                color="primary"
                                size="small"
                            >
                                <SendIcon fontSize="small" />
                            </IconButton>
                        </InputAdornment>
                    ),
                    sx: { borderRadius: 3, alignItems: 'flex-end' },
                }}
            />
        </form>
    );
}
