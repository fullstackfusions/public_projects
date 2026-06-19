import { Box, Paper, Typography } from "@mui/material";
import { format } from "date-fns";
import type { ChatMessage } from "../types";

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

export function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        mb: 1.5,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          maxWidth: "80%",
          borderRadius: 4,
          px: 2,
          py: 1.25,
          bgcolor: isUser ? "primary.main" : "grey.100",
          color: isUser ? "primary.contrastText" : "text.primary",
          borderBottomRightRadius: isUser ? 1 : 16,
          borderBottomLeftRadius: isUser ? 16 : 1,
        }}
      >
        <Typography
          variant="body2"
          sx={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}
        >
          {message.content}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            display: "block",
            mt: 0.5,
            color: isUser ? "rgba(255,255,255,0.7)" : "text.secondary",
            fontSize: "0.65rem",
          }}
        >
          {format(new Date(message.timestamp), "HH:mm:ss")}
        </Typography>
      </Paper>
    </Box>
  );
}
