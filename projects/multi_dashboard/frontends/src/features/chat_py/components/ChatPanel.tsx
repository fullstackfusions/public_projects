import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import PublicIcon from "@mui/icons-material/Public";
import RadioIcon from "@mui/icons-material/Radio";
import WifiIcon from "@mui/icons-material/Wifi";
import { Box, Divider, IconButton, Paper, Typography } from "@mui/material";
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
  websocket: "linear-gradient(to right, #10b981, #0d9488)", // emerald-500 to teal-600
  rest: "linear-gradient(to right, #3b82f6, #4f46e5)", // blue-500 to indigo-600
  sse: "linear-gradient(to right, #a855f7, #db2777)", // purple-500 to pink-600
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
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Box
            sx={{
              p: 1,
              bgcolor: "rgba(255,255,255,0.2)",
              borderRadius: 3,
              display: "flex",
            }}
          >
            <Icon sx={{ fontSize: 20 }} />
          </Box>
          <Box>
            <Typography variant="subtitle1" fontWeight="bold" lineHeight={1.2}>
              {title}
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.8 }}>
              {description}
            </Typography>
          </Box>
        </Box>
        <IconButton
          onClick={clearMessages}
          sx={{
            color: "white",
            "&:hover": { bgcolor: "rgba(255,255,255,0.2)" },
          }}
          title="Clear chat"
          size="small"
        >
          <DeleteOutlineIcon sx={{ fontSize: 16 }} />
        </IconButton>
      </Box>

      {/* Messages area */}
      <Box sx={{ flex: 1, overflowY: "auto", p: 2 }}>
        {messages.length === 0 && !isLoading && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "text.disabled",
            }}
          >
            <Typography variant="body2">
              Send a message to start chatting
            </Typography>
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
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              mb: 1.5,
              bgcolor: "#fff1f2", // rose-50
              borderColor: "#fecdd3", // rose-200
              color: "#e11d48", // rose-600
            }}
          >
            <Typography variant="body2">{error}</Typography>
          </Paper>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Input area */}
      <Divider />
      <Box sx={{ p: 2, bgcolor: "background.paper" }}>
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
