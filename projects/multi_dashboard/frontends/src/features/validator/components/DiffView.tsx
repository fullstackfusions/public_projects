import {
  Box,
  CircularProgress,
  Grid,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { useCallback, useRef } from "react";
import type {
  CommandOutputState,
  CommandStreamState,
  OutputStreamState,
} from "../types";

/**
 * Props for network validation diff viewer
 * - preCheckCommands/postCheckCommands: Command metadata (name, size, loaded state)
 * - outputStream: Per-command chunk state tracking (offset, hasMore, isLoadingMore)
 * - onLoadMore: Callback triggered on scroll threshold to fetch next 4KB chunk
 */
interface DiffViewProps {
  preCheckCommands: CommandOutputState[];
  postCheckCommands: CommandOutputState[];
  outputStream?: OutputStreamState;
  onLoadMore?: (side: "pre" | "post", commandIndex: number) => void;
}

/**
 * Orchestrates rendering of multiple command boxes with side-by-side pre/post comparison
 * Each command independently manages its own scroll-based chunk loading
 */
export const DiffView = ({
  preCheckCommands,
  postCheckCommands,
  outputStream,
  onLoadMore,
}: DiffViewProps) => {
  /**
   * Line-by-line renderer with numbering - optimized for large outputs
   * Streaming indicator remains visible until hasMore=false received
   */
  const renderOutput = (output: string, isStreaming: boolean) => {
    const lines = output.split("\n");
    return (
      <Box sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}>
        {lines.map((line, idx) => (
          <Box
            key={idx}
            sx={{
              px: 2,
              py: 0.5,
              borderBottom: 1,
              borderColor: "grey.100",
              "&:hover": { bgcolor: "grey.50" },
              display: "flex",
            }}
          >
            <Typography
              component="span"
              sx={{
                color: "text.disabled",
                userSelect: "none",
                mr: 2,
                display: "inline-block",
                width: 48,
                textAlign: "right",
                fontSize: "inherit",
              }}
            >
              {idx + 1}
            </Typography>
            <Typography
              component="span"
              sx={{
                color: "text.primary",
                fontSize: "inherit",
                whiteSpace: "pre-wrap",
                wordBreak: "break-all",
              }}
            >
              {line || " "}
            </Typography>
          </Box>
        ))}
        {isStreaming && (
          <Box
            sx={{ px: 2, py: 1, color: "text.secondary", fontStyle: "italic" }}
          >
            Streaming data...
          </Box>
        )}
      </Box>
    );
  };

  const maxCommands = Math.max(
    preCheckCommands.length,
    postCheckCommands.length
  );

  if (maxCommands === 0) {
    return (
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 256,
          color: "text.secondary",
        }}
      >
        No data available
      </Box>
    );
  }

  return (
    <Stack spacing={3} sx={{ pb: 2 }}>
      {Array.from({ length: maxCommands }).map((_, idx) => {
        const preCheckCommand = preCheckCommands[idx] || null;
        const postCheckCommand = postCheckCommands[idx] || null;
        const commandName =
          preCheckCommand?.command ||
          postCheckCommand?.command ||
          `Command ${idx + 1}`;

        // Retrieve per-command stream state for chunk management
        const preStreamState = outputStream?.preCheckCommands.get(idx);
        const postStreamState = outputStream?.postCheckCommands.get(idx);

        return (
          <CommandDiffBox
            key={idx}
            commandIndex={idx}
            commandName={commandName}
            preCheckCommand={preCheckCommand}
            postCheckCommand={postCheckCommand}
            preStreamState={preStreamState}
            postStreamState={postStreamState}
            onLoadMore={onLoadMore}
            renderOutput={renderOutput}
          />
        );
      })}
    </Stack>
  );
};

/**
 * Individual command comparison box with synchronized scroll and incremental loading
 * - Prefers stream state for output (chunked) over legacy full-load command state
 * - Triggers chunk fetch when user scrolls within 200px of bottom
 * - Maintains scroll sync between pre/post panes for parallel comparison
 */
interface CommandDiffBoxProps {
  commandIndex: number;
  commandName: string;
  preCheckCommand?: CommandOutputState | null;
  postCheckCommand?: CommandOutputState | null;
  preStreamState?: CommandStreamState;
  postStreamState?: CommandStreamState;
  onLoadMore?: (side: "pre" | "post", commandIndex: number) => void;
  renderOutput: (output: string, isStreaming: boolean) => JSX.Element;
}

const CommandDiffBox = ({
  commandIndex,
  commandName,
  preCheckCommand,
  postCheckCommand,
  preStreamState,
  postStreamState,
  onLoadMore,
  renderOutput,
}: CommandDiffBoxProps) => {
  const preCheckRef = useRef<HTMLDivElement>(null);
  const postCheckRef = useRef<HTMLDivElement>(null);

  // Prefer chunked stream state over legacy full-output state
  const preOutput = preStreamState?.output ?? preCheckCommand?.output ?? "";
  const postOutput = postStreamState?.output ?? postCheckCommand?.output ?? "";
  const preHasMore = preStreamState?.hasMore ?? false;
  const postHasMore = postStreamState?.hasMore ?? false;
  const preLoading =
    preStreamState?.isLoadingMore ??
    (preCheckCommand && !preCheckCommand.loaded) ??
    false;
  const postLoading =
    postStreamState?.isLoadingMore ??
    (postCheckCommand && !postCheckCommand.loaded) ??
    false;

  /**
   * Dual-purpose scroll handler:
   * 1. Maintains synchronized scroll position between pre/post panes
   * 2. Triggers chunk fetch when scroll approaches bottom (200px threshold)
   *
   * Debouncing handled by hasMore/isLoading guards to prevent duplicate fetches
   */
  const handleScroll = useCallback(
    (source: "pre" | "post") => (e: React.UIEvent<HTMLDivElement>) => {
      const target = e.currentTarget;
      const otherRef = source === "pre" ? postCheckRef : preCheckRef;

      // Synchronized scrolling for parallel comparison
      if (otherRef.current) {
        otherRef.current.scrollTop = target.scrollTop;
        otherRef.current.scrollLeft = target.scrollLeft;
      }

      // Incremental loading trigger - 200px threshold balances UX smoothness vs API calls
      const scrollThreshold = 200;
      const scrollBottom =
        target.scrollHeight - target.scrollTop - target.clientHeight;

      if (scrollBottom < scrollThreshold && onLoadMore) {
        const hasMore = source === "pre" ? preHasMore : postHasMore;
        const isLoading = source === "pre" ? preLoading : postLoading;
        if (hasMore && !isLoading) {
          onLoadMore(source, commandIndex);
        }
      }
    },
    [preHasMore, postHasMore, preLoading, postLoading, onLoadMore, commandIndex]
  );

  return (
    <Paper variant="outlined" sx={{ overflow: "hidden", borderRadius: 2 }}>
      {/* Command Header */}
      <Box
        sx={{
          bgcolor: "grey.100",
          borderBottom: 1,
          borderColor: "divider",
          px: 2,
          py: 1.5,
        }}
      >
        <Typography variant="subtitle1" fontWeight="bold" color="text.primary">
          Command: {commandName}
        </Typography>
        {(preCheckCommand || postCheckCommand) && (
          <Stack direction="row" spacing={2} sx={{ mt: 0.5 }}>
            {preCheckCommand && (
              <Typography variant="caption" color="text.secondary">
                Pre-check: {preCheckCommand.size} bytes
              </Typography>
            )}
            {postCheckCommand && (
              <Typography variant="caption" color="text.secondary">
                Post-check: {postCheckCommand.size} bytes
              </Typography>
            )}
          </Stack>
        )}
      </Box>

      {/* Side-by-side diff view */}
      <Grid container sx={{ borderTop: 1, borderColor: "divider" }}>
        {/* Pre-check output */}
        <Grid
          size={{ xs: 6 }}
          sx={{
            borderRight: 1,
            borderColor: "divider",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box
            sx={{
              bgcolor: "error.light",
              bgcolorOpacity: 0.1, // Note: MUI doesn't support bgcolorOpacity directly, using alpha color or custom style
              backgroundColor: "rgba(253, 237, 237, 1)", // red[50] equivalent
              borderBottom: 1,
              borderColor: "error.main",
              borderBottomColor: "rgba(239, 83, 80, 0.3)",
              px: 2,
              py: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              position: "sticky",
              top: 0,
              zIndex: 1,
            }}
          >
            <Typography
              variant="subtitle2"
              sx={{ color: "error.dark", fontWeight: "bold" }}
            >
              Pre-Check Output
            </Typography>
            {preLoading && (
              <Typography
                variant="caption"
                sx={{
                  color: "error.main",
                  display: "flex",
                  alignItems: "center",
                  gap: 0.5,
                }}
              >
                <CircularProgress size={10} color="error" /> Loading...
              </Typography>
            )}
            {preHasMore && !preLoading && (
              <Typography variant="caption" sx={{ color: "error.main" }}>
                Scroll for more...
              </Typography>
            )}
          </Box>
          <Box
            ref={preCheckRef}
            onScroll={handleScroll("pre")}
            sx={{
              overflow: "auto",
              maxHeight: 384,
              bgcolor: "rgba(253, 237, 237, 0.3)", // red[50] with opacity
            }}
          >
            {preOutput ? (
              renderOutput(preOutput, preLoading)
            ) : (
              <Box
                sx={{
                  p: 2,
                  color: "text.secondary",
                  fontStyle: "italic",
                  fontSize: "0.875rem",
                }}
              >
                No pre-check data
              </Box>
            )}
          </Box>
        </Grid>

        {/* Post-check output */}
        <Grid
          size={{ xs: 6 }}
          sx={{ display: "flex", flexDirection: "column" }}
        >
          <Box
            sx={{
              backgroundColor: "rgba(232, 245, 233, 1)", // green[50] equivalent
              borderBottom: 1,
              borderColor: "success.main",
              borderBottomColor: "rgba(102, 187, 106, 0.3)",
              px: 2,
              py: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              position: "sticky",
              top: 0,
              zIndex: 1,
            }}
          >
            <Typography
              variant="subtitle2"
              sx={{ color: "success.dark", fontWeight: "bold" }}
            >
              Post-Check Output
            </Typography>
            {postLoading && (
              <Typography
                variant="caption"
                sx={{
                  color: "success.main",
                  display: "flex",
                  alignItems: "center",
                  gap: 0.5,
                }}
              >
                <CircularProgress size={10} color="success" /> Loading...
              </Typography>
            )}
            {postHasMore && !postLoading && (
              <Typography variant="caption" sx={{ color: "success.main" }}>
                Scroll for more...
              </Typography>
            )}
          </Box>
          <Box
            ref={postCheckRef}
            onScroll={handleScroll("post")}
            sx={{
              overflow: "auto",
              maxHeight: 384,
              bgcolor: "rgba(232, 245, 233, 0.3)", // green[50] with opacity
            }}
          >
            {postOutput ? (
              renderOutput(postOutput, postLoading)
            ) : (
              <Box
                sx={{
                  p: 2,
                  color: "text.secondary",
                  fontStyle: "italic",
                  fontSize: "0.875rem",
                }}
              >
                No post-check data
              </Box>
            )}
          </Box>
        </Grid>
      </Grid>
    </Paper>
  );
};
