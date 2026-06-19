import DeleteIcon from "@mui/icons-material/Delete";
import PublicIcon from "@mui/icons-material/Public";
import RadioIcon from "@mui/icons-material/Radio";
import WifiIcon from "@mui/icons-material/Wifi";
import {
  Alert,
  Box,
  IconButton,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import type { ChatMode } from "../types";
import { useChat } from "../useChat";
import { ChatInput } from "./ChatInput";
import { ChatMessageBubble } from "./ChatMessageBubble";
import { StatusIndicator } from "./StatusIndicator";

interface ChatPanelProps {
  mode: ChatMode;
  title: string;
  description: string;
}

const modeIcons = {
  websocket: WifiIcon,
  rest: PublicIcon,
  sse: RadioIcon,
};

const modeColors = {
  websocket: "linear-gradient(to right, #06b6d4, #0d9488)", // cyan-500 to teal-600
  rest: "linear-gradient(to right, #14b8a6, #059669)", // teal-500 to emerald-600
  sse: "linear-gradient(to right, #0ea5e9, #2563eb)", // sky-500 to blue-600
};

export function ChatPanel({ mode, title, description }: ChatPanelProps) {
  const {
    messages,
    currentStatus,
    currentProgress,
    isLoading,
    streamingContent,
    error,
    sendMessage,
    clearMessages,
    messagesEndRef,
  } = useChat(mode);

  const Icon = modeIcons[mode];

  return (
    <Paper
      elevation={3}
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        borderRadius: 4,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          background: modeColors[mode],
          color: "white",
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
        >
          <Stack direction="row" alignItems="center" spacing={1.5}>
            <Box
              sx={{
                p: 1,
                bgcolor: "rgba(255, 255, 255, 0.2)",
                borderRadius: 2,
                display: "flex",
              }}
            >
              <Icon fontSize="small" />
            </Box>
            <Box>
              <Typography
                variant="subtitle1"
                fontWeight="bold"
                lineHeight={1.2}
              >
                {title}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.8 }}>
                {description}
              </Typography>
            </Box>
          </Stack>
          <IconButton
            onClick={clearMessages}
            sx={{
              color: "white",
              "&:hover": { bgcolor: "rgba(255, 255, 255, 0.2)" },
            }}
            title="Clear chat"
            size="small"
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Stack>
      </Box>

      {/* Messages area */}
      <Box
        sx={{
          flex: 1,
          overflowY: "auto",
          p: 2,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
          gap: 2,
        }}
      >
        {messages.length === 0 && !isLoading && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "text.disabled",
              fontSize: "0.875rem",
            }}
          >
            Send a message to start chatting
          </Box>
        )}

        {messages.map((message) => (
          <ChatMessageBubble key={message.id} message={message} />
        ))}

        <StatusIndicator
          status={currentStatus}
          progress={currentProgress}
          streamingContent={streamingContent}
        />

        {error && (
          <Alert severity="error" sx={{ mb: 1 }}>
            {error}
          </Alert>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Input area */}
      <Box sx={{ p: 2, borderTop: 1, borderColor: "divider" }}>
        <ChatInput
          onSend={sendMessage}
          disabled={isLoading}
          placeholder={
            isLoading ? "Waiting for response..." : "Type a message..."
          }
        />
      </Box>
    </Paper>
  );
}
