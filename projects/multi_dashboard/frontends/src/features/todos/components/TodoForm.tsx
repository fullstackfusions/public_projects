import { Box, Button, TextField, Typography } from "@mui/material";
import { FormEvent, useState } from "react";

interface TodoFormProps {
  isSubmitting: boolean;
  onSubmit: (payload: {
    title: string;
    description?: string;
  }) => Promise<void> | void;
}

export function TodoForm({ isSubmitting, onSubmit }: TodoFormProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) {
      return;
    }
    await onSubmit({
      title: title.trim(),
      description: description.trim() || undefined,
    });
    setTitle("");
    setDescription("");
  }

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{ display: "flex", flexDirection: "column", gap: 2 }}
    >
      <Box>
        <Typography
          variant="subtitle2"
          fontWeight="bold"
          color="text.primary"
          gutterBottom
        >
          Title
        </Typography>
        <TextField
          fullWidth
          variant="outlined"
          size="small"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Buy groceries"
          required
          sx={{
            "& .MuiOutlinedInput-root": {
              borderRadius: 3,
              bgcolor: "background.paper",
            },
          }}
        />
      </Box>

      <Box>
        <Typography
          variant="subtitle2"
          fontWeight="bold"
          color="text.primary"
          gutterBottom
        >
          Description
        </Typography>
        <TextField
          fullWidth
          variant="outlined"
          size="small"
          multiline
          minRows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What needs to be done?"
          sx={{
            "& .MuiOutlinedInput-root": {
              borderRadius: 3,
              bgcolor: "background.paper",
            },
          }}
        />
      </Box>

      <Button
        type="submit"
        variant="contained"
        disabled={isSubmitting}
        sx={{
          borderRadius: 3,
          textTransform: "none",
          fontWeight: 600,
          py: 1,
          boxShadow: "none",
          "&:hover": {
            boxShadow: "none",
          },
        }}
      >
        {isSubmitting ? "Adding…" : "Add Todo"}
      </Button>
    </Box>
  );
}
