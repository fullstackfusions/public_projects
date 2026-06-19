import DeleteIcon from "@mui/icons-material/Delete";
import {
  Box,
  Checkbox,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Paper,
  Typography,
} from "@mui/material";
import type { Todo } from "../types";

interface TodoListProps {
  todos: Todo[];
  onToggle: (id: string, completed: boolean) => void;
  onDelete: (id: string) => void;
}

export function TodoList({ todos, onToggle, onDelete }: TodoListProps) {
  if (todos.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No todos yet. Add one to get started.
      </Typography>
    );
  }

  return (
    <List sx={{ display: "flex", flexDirection: "column", gap: 2, p: 0 }}>
      {todos.map((todo) => (
        <Paper
          key={todo.id}
          elevation={0}
          variant="outlined"
          sx={{
            borderRadius: 4,
            bgcolor: todo.completed ? "grey.50" : "background.paper",
            transition: "all 0.2s",
            overflow: "hidden",
          }}
        >
          <ListItem
            disablePadding
            sx={{ p: 2 }}
            secondaryAction={
              <IconButton
                edge="end"
                aria-label="delete"
                onClick={() => onDelete(todo.id)}
                sx={{
                  bgcolor: "#e11d48", // rose-600
                  color: "white",
                  borderRadius: 3,
                  "&:hover": {
                    bgcolor: "#be123c", // rose-700
                  },
                  width: 36,
                  height: 36,
                }}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            }
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "flex-start",
                gap: 2,
                width: "100%",
                pr: 6,
              }}
            >
              <Checkbox
                checked={todo.completed}
                onChange={(e) => onToggle(todo.id, e.target.checked)}
                sx={{
                  p: 0.5,
                  "&.Mui-checked": {
                    color: "primary.main",
                  },
                }}
              />
              <ListItemText
                primary={
                  <Typography
                    variant="subtitle1"
                    fontWeight="bold"
                    sx={{
                      textDecoration: todo.completed ? "line-through" : "none",
                      color: todo.completed ? "text.disabled" : "text.primary",
                    }}
                  >
                    {todo.title}
                  </Typography>
                }
                secondary={
                  todo.description && (
                    <Typography
                      variant="body2"
                      sx={{
                        textDecoration: todo.completed
                          ? "line-through"
                          : "none",
                        color: todo.completed
                          ? "text.disabled"
                          : "text.secondary",
                        mt: 0.5,
                      }}
                    >
                      {todo.description}
                    </Typography>
                  )
                }
                sx={{ m: 0 }}
              />
            </Box>
          </ListItem>
        </Paper>
      ))}
    </List>
  );
}
