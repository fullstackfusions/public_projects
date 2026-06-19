import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  CircularProgress,
  Grid,
  Paper,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { fetchNextChunk, streamValidationResult } from "../../../api/validator";
import type {
  StreamAnalysis,
  StreamChunkData,
  StreamCommandInfo,
  StreamEvent,
  StreamInitialData,
  StreamMetadata,
  ValidationState,
} from "../types";
import { DiffView } from "./DiffView";

/**
 * Diff View Tab - SSE streaming device validation with per-command chunk management
 * Extracted from original ValidatorPage to support tabbed UI
 */
export const DiffViewTab = () => {
  const [changeRequestId, setChangeRequestId] = useState("CR123456");
  const [deviceId, setDeviceId] = useState("DEV001");
  const [validationState, setValidationState] = useState<ValidationState>({
    metadata: null,
    preCheckCommands: [],
    postCheckCommands: [],
    llmAnalysis: "",
    isStreaming: false,
    isComplete: false,
    error: null,
    outputStream: {
      preCheckCommands: new Map(),
      postCheckCommands: new Map(),
    },
  });

  /**
   * SSE event handler - maintains dual state for backwards compatibility and optimization
   */
  const handleStreamEvent = (event: StreamEvent) => {
    setValidationState((prev) => {
      const newState = { ...prev };

      switch (event.type) {
        case "metadata": {
          const metadata = event.data as StreamMetadata;
          newState.metadata = metadata;
          break;
        }

        case "pre_check_command": {
          const cmdInfo = event.data as StreamCommandInfo;
          if (!newState.preCheckCommands[cmdInfo.index]) {
            const newCommands = [...newState.preCheckCommands];
            newCommands[cmdInfo.index] = {
              command: cmdInfo.command,
              size: cmdInfo.size,
              output: "",
              loaded: false,
            };
            newState.preCheckCommands = newCommands;
          }
          break;
        }

        case "post_check_command": {
          const cmdInfo = event.data as StreamCommandInfo;
          if (!newState.postCheckCommands[cmdInfo.index]) {
            const newCommands = [...newState.postCheckCommands];
            newCommands[cmdInfo.index] = {
              command: cmdInfo.command,
              size: cmdInfo.size,
              output: "",
              loaded: false,
            };
            newState.postCheckCommands = newCommands;
          }
          break;
        }

        case "initial_data": {
          const initialData = event.data as StreamInitialData;
          const commandMap =
            initialData.side === "pre"
              ? new Map(newState.outputStream.preCheckCommands)
              : new Map(newState.outputStream.postCheckCommands);

          commandMap.set(initialData.command_index, {
            output: initialData.chunk,
            offset: initialData.offset + initialData.chunk.length,
            totalSize: initialData.total_size,
            hasMore: initialData.has_more,
            isLoadingMore: false,
          });

          if (initialData.side === "pre") {
            newState.outputStream.preCheckCommands = commandMap;
            if (newState.preCheckCommands[initialData.command_index]) {
              newState.preCheckCommands[initialData.command_index].output =
                initialData.chunk;
              newState.preCheckCommands[initialData.command_index].loaded =
                !initialData.has_more;
            }
          } else {
            newState.outputStream.postCheckCommands = commandMap;
            if (newState.postCheckCommands[initialData.command_index]) {
              newState.postCheckCommands[initialData.command_index].output =
                initialData.chunk;
              newState.postCheckCommands[initialData.command_index].loaded =
                !initialData.has_more;
            }
          }
          break;
        }

        case "chunk_data": {
          const chunkData = event.data as StreamChunkData;
          const commandMap =
            chunkData.side === "pre"
              ? new Map(newState.outputStream.preCheckCommands)
              : new Map(newState.outputStream.postCheckCommands);

          const existingState = commandMap.get(chunkData.command_index);
          if (existingState) {
            commandMap.set(chunkData.command_index, {
              output: existingState.output + chunkData.chunk,
              offset: chunkData.offset + chunkData.chunk.length,
              totalSize: chunkData.total_size,
              hasMore: chunkData.has_more,
              isLoadingMore: false,
            });

            if (chunkData.side === "pre") {
              newState.outputStream.preCheckCommands = commandMap;
              if (newState.preCheckCommands[chunkData.command_index]) {
                newState.preCheckCommands[chunkData.command_index].output =
                  commandMap.get(chunkData.command_index)!.output;
                newState.preCheckCommands[chunkData.command_index].loaded =
                  !chunkData.has_more;
              }
            } else {
              newState.outputStream.postCheckCommands = commandMap;
              if (newState.postCheckCommands[chunkData.command_index]) {
                newState.postCheckCommands[chunkData.command_index].output =
                  commandMap.get(chunkData.command_index)!.output;
                newState.postCheckCommands[chunkData.command_index].loaded =
                  !chunkData.has_more;
              }
            }
          }
          break;
        }

        case "llm_analysis": {
          const analysis = event.data as StreamAnalysis;
          newState.llmAnalysis = analysis.analysis;
          break;
        }

        case "initial_complete":
        case "chunk_complete": {
          break;
        }

        case "complete": {
          newState.isStreaming = false;
          newState.isComplete = true;
          break;
        }

        case "error": {
          const errorData = event.data as { error: string };
          newState.error = errorData.error;
          newState.isStreaming = false;
          break;
        }
      }

      return newState;
    });
  };

  const loadMoreChunks = async (side: "pre" | "post", commandIndex: number) => {
    const commandMap =
      side === "pre"
        ? validationState.outputStream.preCheckCommands
        : validationState.outputStream.postCheckCommands;

    const commandState = commandMap.get(commandIndex);

    if (!commandState || !commandState.hasMore || commandState.isLoadingMore) {
      return;
    }

    const newCommandMap = new Map(commandMap);
    newCommandMap.set(commandIndex, {
      ...commandState,
      isLoadingMore: true,
    });

    setValidationState((prev) => ({
      ...prev,
      outputStream: {
        ...prev.outputStream,
        [side === "pre" ? "preCheckCommands" : "postCheckCommands"]:
          newCommandMap,
      },
    }));

    await fetchNextChunk(
      changeRequestId,
      deviceId,
      commandState.offset,
      side,
      commandIndex,
      {
        onEvent: handleStreamEvent,
        onError: (error: Error) => {
          setValidationState((prev) => ({
            ...prev,
            error: error.message,
          }));
        },
        onComplete: () => {},
      }
    );
  };

  const startStreaming = async () => {
    setValidationState({
      metadata: null,
      preCheckCommands: [],
      postCheckCommands: [],
      llmAnalysis: "",
      isStreaming: true,
      isComplete: false,
      error: null,
      outputStream: {
        preCheckCommands: new Map(),
        postCheckCommands: new Map(),
      },
    });

    await streamValidationResult(changeRequestId, deviceId, {
      onEvent: handleStreamEvent,
      onError: (error) => {
        setValidationState((prev) => ({
          ...prev,
          error: error.message,
          isStreaming: false,
        }));
      },
      onComplete: () => {
        setValidationState((prev) => ({
          ...prev,
          isStreaming: false,
          isComplete: true,
        }));
      },
    });
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Input Controls */}
      <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Stack
          direction="row"
          spacing={2}
          alignItems="flex-start"
          sx={{ mb: 3 }}
        >
          <TextField
            label="Change Request ID"
            value={changeRequestId}
            onChange={(e) => setChangeRequestId(e.target.value)}
            placeholder="CR123456"
            disabled={validationState.isStreaming}
            fullWidth
            variant="outlined"
          />
          <TextField
            label="Device ID"
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
            placeholder="DEV001"
            disabled={validationState.isStreaming}
            fullWidth
            variant="outlined"
          />
          <Button
            onClick={startStreaming}
            disabled={validationState.isStreaming}
            variant="contained"
            size="large"
            startIcon={
              validationState.isStreaming ? (
                <CircularProgress size={20} color="inherit" />
              ) : (
                <PlayArrowIcon />
              )
            }
            sx={{ height: 56, minWidth: 180 }}
          >
            {validationState.isStreaming ? "Streaming..." : "Start Validation"}
          </Button>
        </Stack>

        {/* Device Info */}
        {validationState.metadata && (
          <Alert severity="info" icon={false} sx={{ mb: 2 }}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 3 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Device
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  {validationState.metadata.device_name}
                </Typography>
              </Grid>
              <Grid size={{ xs: 3 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Status
                </Typography>
                <Typography
                  variant="body2"
                  fontWeight="medium"
                  color={
                    validationState.metadata.device_status === "Success"
                      ? "success.main"
                      : "error.main"
                  }
                >
                  {validationState.metadata.device_status}
                </Typography>
              </Grid>
              <Grid size={{ xs: 3 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Validation
                </Typography>
                <Typography
                  variant="body2"
                  fontWeight="medium"
                  color={
                    validationState.metadata.validation_status === "Passed"
                      ? "success.main"
                      : "error.main"
                  }
                >
                  {validationState.metadata.validation_status}
                </Typography>
              </Grid>
              <Grid size={{ xs: 3 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Stream ID
                </Typography>
                <Typography variant="caption" fontFamily="monospace">
                  {validationState.metadata.streaming_metadata?.stream_id}
                </Typography>
              </Grid>
            </Grid>
          </Alert>
        )}

        {/* Error Display */}
        {validationState.error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            <AlertTitle>Error</AlertTitle>
            {validationState.error}
          </Alert>
        )}
      </Paper>

      {/* Main Content - Diff View */}
      <Box sx={{ flex: 1, overflowY: "auto", px: 1, pb: 2 }}>
        {validationState.preCheckCommands.length > 0 ||
        validationState.postCheckCommands.length > 0 ? (
          <DiffView
            preCheckCommands={validationState.preCheckCommands}
            postCheckCommands={validationState.postCheckCommands}
            outputStream={validationState.outputStream}
            onLoadMore={loadMoreChunks}
          />
        ) : (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "text.secondary",
            }}
          >
            <Typography>
              {validationState.isStreaming
                ? "Waiting for data..."
                : "Enter Change Request ID and Device ID, then click Start Validation"}
            </Typography>
          </Box>
        )}
      </Box>

      {/* LLM Analysis Footer */}
      {validationState.llmAnalysis && (
        <Paper sx={{ p: 3, mt: 2, borderTop: 1, borderColor: "divider" }}>
          <Typography variant="h6" gutterBottom>
            LLM Analysis
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {validationState.llmAnalysis}
          </Typography>
        </Paper>
      )}

      {/* Streaming Status */}
      <Snackbar
        open={validationState.isStreaming}
        message={
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <CircularProgress size={16} color="inherit" />
            <Typography variant="body2">Streaming data...</Typography>
          </Box>
        }
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      />
    </Box>
  );
};
