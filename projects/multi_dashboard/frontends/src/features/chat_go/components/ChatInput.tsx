import SendIcon from "@mui/icons-material/Send";
import { Box, IconButton, InputAdornment, TextField } from "@mui/material";
import { FormEvent, useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input);
      setInput("");
    }
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{ display: "flex", gap: 1 }}
    >
      <TextField
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={placeholder || "Type a message..."}
        disabled={disabled}
        fullWidth
        size="small"
        variant="outlined"
        sx={{
          "& .MuiOutlinedInput-root": {
            borderRadius: 3,
            bgcolor: "grey.50",
          },
        }}
        InputProps={{
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                type="submit"
                disabled={disabled || !input.trim()}
                color="primary"
                edge="end"
                size="small"
              >
                <SendIcon fontSize="small" />
              </IconButton>
            </InputAdornment>
          ),
        }}
      />
    </Box>
  );
}
