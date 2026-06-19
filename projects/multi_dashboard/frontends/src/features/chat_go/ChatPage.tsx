import {
  Box,
  Card,
  CardContent,
  Grid,
  List,
  ListItem,
  ListItemText,
  Typography,
} from "@mui/material";
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
          Chat Communication Comparison (Go Backend)
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Compare three different approaches to real-time chat using the{" "}
          <Box component="span" sx={{ fontWeight: "bold", color: "info.main" }}>
            Go backend
          </Box>
          : WebSocket, REST API, and Server-Sent Events (SSE). Each panel
          demonstrates a different communication pattern with live status
          updates.
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
            sx={{
              bgcolor: "rgba(6, 182, 212, 0.05)",
              borderColor: "rgba(6, 182, 212, 0.2)",
            }}
          >
            <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
              <Typography
                variant="subtitle1"
                fontWeight="bold"
                sx={{ color: "rgb(21, 94, 117)", mb: 1 }}
              >
                WebSocket (Go/Fiber)
              </Typography>
              <List dense disablePadding>
                {[
                  "Full duplex communication",
                  "Goroutine per connection",
                  "Lowest latency for real-time",
                  "Best for chat applications",
                ].map((text, i) => (
                  <ListItem
                    key={i}
                    disablePadding
                    sx={{ display: "list-item", listStyleType: "disc", ml: 2 }}
                  >
                    <ListItemText
                      primary={text}
                      primaryTypographyProps={{
                        variant: "body2",
                        color: "rgb(14, 116, 144)",
                      }}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card
            variant="outlined"
            sx={{
              bgcolor: "rgba(20, 184, 166, 0.05)",
              borderColor: "rgba(20, 184, 166, 0.2)",
            }}
          >
            <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
              <Typography
                variant="subtitle1"
                fontWeight="bold"
                sx={{ color: "rgb(17, 94, 89)", mb: 1 }}
              >
                REST API + Polling (Go)
              </Typography>
              <List dense disablePadding>
                {[
                  "Standard HTTP requests",
                  "Async request with status polling",
                  "Go's efficient concurrency",
                  "Good for simple interactions",
                ].map((text, i) => (
                  <ListItem
                    key={i}
                    disablePadding
                    sx={{ display: "list-item", listStyleType: "disc", ml: 2 }}
                  >
                    <ListItemText
                      primary={text}
                      primaryTypographyProps={{
                        variant: "body2",
                        color: "rgb(15, 118, 110)",
                      }}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card
            variant="outlined"
            sx={{
              bgcolor: "rgba(14, 165, 233, 0.05)",
              borderColor: "rgba(14, 165, 233, 0.2)",
            }}
          >
            <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
              <Typography
                variant="subtitle1"
                fontWeight="bold"
                sx={{ color: "rgb(7, 89, 133)", mb: 1 }}
              >
                SSE (Go StreamWriter)
              </Typography>
              <List dense disablePadding>
                {[
                  "One-way server-to-client stream",
                  "Fiber's StreamWriter API",
                  "Used by MCP protocol",
                  "Great for streaming responses",
                ].map((text, i) => (
                  <ListItem
                    key={i}
                    disablePadding
                    sx={{ display: "list-item", listStyleType: "disc", ml: 2 }}
                  >
                    <ListItemText
                      primary={text}
                      primaryTypographyProps={{
                        variant: "body2",
                        color: "rgb(3, 105, 161)",
                      }}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
