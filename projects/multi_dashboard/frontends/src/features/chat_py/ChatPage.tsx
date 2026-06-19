import { Box, Card, CardContent, Grid, Typography } from "@mui/material";
import { ChatPanel } from "./components/ChatPanel";

export function ChatPage() {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 3,
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Page header */}
      <Box sx={{ flexShrink: 0 }}>
        <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
          Chat Communication Comparison
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Compare three different approaches to real-time chat: WebSocket, REST
          API, and Server-Sent Events (SSE). Each panel demonstrates a different
          communication pattern with live status updates.
        </Typography>
      </Box>

      {/* Three-column chat layout */}
      <Box sx={{ flex: 1, minHeight: 0 }}>
        <Grid container spacing={3} sx={{ height: "100%" }}>
          <Grid size={{ xs: 12, lg: 4 }} sx={{ height: "100%" }}>
            <ChatPanel
              mode="websocket"
              title="WebSocket"
              description="Real-time bidirectional"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 4 }} sx={{ height: "100%" }}>
            <ChatPanel
              mode="rest"
              title="REST API"
              description="Polling for status updates"
            />
          </Grid>
          <Grid size={{ xs: 12, lg: 4 }} sx={{ height: "100%" }}>
            <ChatPanel
              mode="sse"
              title="SSE (Server-Sent Events)"
              description="Streaming like MCP"
            />
          </Grid>
        </Grid>
      </Box>

      {/* Info cards */}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card
            variant="outlined"
            sx={{ bgcolor: "#ecfdf5", borderColor: "#d1fae5" }}
          >
            <CardContent>
              <Typography
                variant="subtitle1"
                fontWeight="bold"
                sx={{ color: "#065f46", mb: 1 }}
              >
                WebSocket
              </Typography>
              <Box
                component="ul"
                sx={{ m: 0, pl: 2, color: "#047857", fontSize: "0.875rem" }}
              >
                <li>Full duplex communication</li>
                <li>Persistent connection</li>
                <li>Lowest latency for real-time</li>
                <li>Best for chat applications</li>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card
            variant="outlined"
            sx={{ bgcolor: "#eff6ff", borderColor: "#dbeafe" }}
          >
            <CardContent>
              <Typography
                variant="subtitle1"
                fontWeight="bold"
                sx={{ color: "#1e40af", mb: 1 }}
              >
                REST API + Polling
              </Typography>
              <Box
                component="ul"
                sx={{ m: 0, pl: 2, color: "#1d4ed8", fontSize: "0.875rem" }}
              >
                <li>Standard HTTP requests</li>
                <li>Async request with status polling</li>
                <li>Simple to implement</li>
                <li>Good for simple interactions</li>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card
            variant="outlined"
            sx={{ bgcolor: "#faf5ff", borderColor: "#f3e8ff" }}
          >
            <CardContent>
              <Typography
                variant="subtitle1"
                fontWeight="bold"
                sx={{ color: "#6b21a8", mb: 1 }}
              >
                SSE (Server-Sent Events)
              </Typography>
              <Box
                component="ul"
                sx={{ m: 0, pl: 2, color: "#7e22ce", fontSize: "0.875rem" }}
              >
                <li>One-way server-to-client stream</li>
                <li>HTTP-based, easy to implement</li>
                <li>Used by MCP protocol</li>
                <li>Great for streaming responses</li>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
