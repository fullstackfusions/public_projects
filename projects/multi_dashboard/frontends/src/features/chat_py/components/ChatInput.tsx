import SendIcon from "@mui/icons-material/Send";
import { IconButton, InputAdornment, Paper, TextField } from "@mui/material";
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
    <Paper
      component="form"
      onSubmit={handleSubmit}
      elevation={0}
      sx={{
        p: "2px 4px",
        display: "flex",
        alignItems: "center",
        width: "100%",
        background: "transparent",
      }}
    >
      <TextField
        fullWidth
        variant="outlined"
        size="small"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={placeholder || "Type a message..."}
        disabled={disabled}
        sx={{
          mr: 1,
          bgcolor: "background.paper",
          "& .MuiOutlinedInput-root": {
            borderRadius: 3, // rounded-xl equivalent
          },
        }}
        InputProps={{
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                type="submit"
                color="primary"
                disabled={disabled || !input.trim()}
                edge="end"
              >
                <SendIcon />
              </IconButton>
            </InputAdornment>
          ),
        }}
      />
    </Paper>
  );
}
