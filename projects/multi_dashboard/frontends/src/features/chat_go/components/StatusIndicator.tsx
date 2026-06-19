import { Box, Paper, Stack, Typography, keyframes } from "@mui/material";

const bounce = keyframes`
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
`;

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
`;

interface StatusIndicatorProps {
  status: string | null;
  progress: number;
  streamingContent: string;
}

export function StatusIndicator({
  status,
  progress,
  streamingContent,
}: StatusIndicatorProps) {
  if (!status && !streamingContent) return null;

  return (
    <Box sx={{ mb: 1.5 }}>
      {/* Status indicator */}
      {status && (
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
          <Stack direction="row" spacing={0.5}>
            {[0, 150, 300].map((delay) => (
              <Box
                key={delay}
                sx={{
                  width: 8,
                  height: 8,
                  bgcolor: "primary.main",
                  borderRadius: "50%",
                  animation: `${bounce} 1s infinite`,
                  animationDelay: `${delay}ms`,
                }}
              />
            ))}
          </Stack>
          <Typography variant="body2" color="text.secondary">
            {status}
          </Typography>
          {progress > 0 && (
            <Typography variant="caption" color="text.secondary">
              ({progress}%)
            </Typography>
          )}
        </Stack>
      )}

      {/* Streaming content preview */}
      {streamingContent && (
        <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
          <Paper
            elevation={0}
            sx={{
              maxWidth: "80%",
              borderRadius: 4,
              borderBottomLeftRadius: 1,
              px: 2,
              py: 1.25,
              bgcolor: "grey.100",
              color: "text.primary",
            }}
          >
            <Typography
              variant="body2"
              sx={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}
            >
              {streamingContent}
              <Box
                component="span"
                sx={{
                  display: "inline-block",
                  width: 6,
                  height: 16,
                  bgcolor: "primary.main",
                  ml: 0.5,
                  verticalAlign: "middle",
                  animation: `${pulse} 1s infinite`,
                }}
              />
            </Typography>
          </Paper>
        </Box>
      )}
    </Box>
  );
}
