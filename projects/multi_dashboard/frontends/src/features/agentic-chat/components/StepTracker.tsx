import { keyframes } from '@emotion/react';
import { Box, Chip, Typography } from '@mui/material';
import type { AgentStep } from '../types';

const bounce = keyframes`
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
`;

type ChipColor = 'default' | 'primary' | 'success' | 'error' | 'warning';

const ACTION_COLOR: Record<string, ChipColor> = {
    started: 'primary',
    tool_called: 'warning',
    completed: 'success',
    error: 'error',
};

interface Props {
    steps: AgentStep[];
    isLoading: boolean;
}

export function StepTracker({ steps, isLoading }: Props) {
    if (!isLoading && steps.length === 0) return null;

    return (
        <Box sx={{ mb: 1.5, pl: 0.5 }}>
            {steps.map((step, i) => (
                <Box
                    key={i}
                    sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}
                >
                    <Chip
                        label={step.agent}
                        size="small"
                        color={ACTION_COLOR[step.action] ?? 'default'}
                        variant="outlined"
                        sx={{ fontSize: '0.68rem', height: 20, minWidth: 110 }}
                    />
                    <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 400 }}>
                        {step.action}
                        {step.detail
                            ? ` — ${step.detail.length > 90 ? step.detail.slice(0, 90) + '…' : step.detail}`
                            : ''}
                    </Typography>
                </Box>
            ))}

            {isLoading && (
                <Box sx={{ display: 'flex', gap: 0.5, mt: 0.75, pl: 0.5 }}>
                    {[0, 150, 300].map((delay) => (
                        <Box
                            key={delay}
                            sx={{
                                width: 7,
                                height: 7,
                                bgcolor: 'primary.main',
                                borderRadius: '50%',
                                animation: `${bounce} 1s infinite ${delay}ms`,
                            }}
                        />
                    ))}
                </Box>
            )}
        </Box>
    );
}
