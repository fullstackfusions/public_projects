import { keyframes } from "@emotion/react";
import { Box, Paper, Typography } from "@mui/material";

const bounce = keyframes`
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
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
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <Box sx={{ display: "flex", gap: 0.5 }}>
            {[0, 150, 300].map((delay) => (
              <Box
                key={delay}
                sx={{
                  width: 8,
                  height: 8,
                  bgcolor: "primary.main",
                  borderRadius: "50%",
                  animation: `${bounce} 1s infinite ${delay}ms`,
                }}
              />
            ))}
          </Box>
          <Typography variant="body2" color="text.secondary">
            {status}
          </Typography>
          {progress > 0 && (
            <Typography variant="caption" color="text.disabled">
              ({progress}%)
            </Typography>
          )}
        </Box>
      )}

      {/* Streaming content preview */}
      {streamingContent && (
        <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
          <Paper
            elevation={0}
            sx={{
              maxWidth: "80%",
              borderRadius: 4,
              borderBottomLeftRadius: 4,
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
                  animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                  "@keyframes pulse": {
                    "0%, 100%": { opacity: 1 },
                    "50%": { opacity: 0.5 },
                  },
                }}
              />
            </Typography>
          </Paper>
        </Box>
      )}
    </Box>
  );
}
