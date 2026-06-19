import FilterListOffIcon from "@mui/icons-material/FilterListOff";
import RefreshIcon from "@mui/icons-material/Refresh";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  TextField,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";
import { clearTasksCache, fetchValidationTasks } from "../../../api/validator";
import type {
  PaginatedTasksResponse,
  SortOrder,
  TaskFilters,
  TaskSortState,
  ValidationTask,
} from "../types";

/**
 * Sortable column header with visual sort direction indicator
 */
interface SortableHeaderProps {
  column: keyof ValidationTask;
  label: string;
  currentSort: TaskSortState;
  onSort: (column: keyof ValidationTask) => void;
}

const SortableHeader = ({
  column,
  label,
  currentSort,
  onSort,
}: SortableHeaderProps) => {
  const isActive = currentSort.column === column;
  const direction = isActive && currentSort.order ? currentSort.order : "asc";

  return (
    <TableSortLabel
      active={isActive}
      direction={direction}
      onClick={() => onSort(column)}
    >
      {label}
    </TableSortLabel>
  );
};

/**
 * Filter input row - renders filter inputs for each column
 */
interface FilterRowProps {
  filters: TaskFilters;
  onFilterChange: (key: keyof TaskFilters, value: string) => void;
}

const FilterRow = ({ filters, onFilterChange }: FilterRowProps) => {
  return (
    <TableRow sx={{ bgcolor: "grey.50" }}>
      <TableCell>
        <TextField
          placeholder="Filter ID..."
          value={filters.change_request_id}
          onChange={(e) => onFilterChange("change_request_id", e.target.value)}
          size="small"
          fullWidth
          variant="outlined"
          sx={{ bgcolor: "white" }}
        />
      </TableCell>
      <TableCell>
        <TextField
          placeholder="Filter description..."
          value={filters.change_description}
          onChange={(e) => onFilterChange("change_description", e.target.value)}
          size="small"
          fullWidth
          variant="outlined"
          sx={{ bgcolor: "white" }}
        />
      </TableCell>
      <TableCell>
        <TextField
          placeholder="Filter status..."
          value={filters.change_status}
          onChange={(e) => onFilterChange("change_status", e.target.value)}
          size="small"
          fullWidth
          variant="outlined"
          sx={{ bgcolor: "white" }}
        />
      </TableCell>
      <TableCell>{/* Created at - no filter for date simplicity */}</TableCell>
      <TableCell>
        <TextField
          placeholder="Filter path..."
          value={filters.path}
          onChange={(e) => onFilterChange("path", e.target.value)}
          size="small"
          fullWidth
          variant="outlined"
          sx={{ bgcolor: "white" }}
        />
      </TableCell>
    </TableRow>
  );
};

/**
 * Status badge with color coding based on task status
 */
const StatusBadge = ({ status }: { status: string }) => {
  const getStatusColor = () => {
    switch (status.toLowerCase()) {
      case "completed":
        return "success";
      case "in progress":
        return "info";
      case "pending":
        return "warning";
      case "failed":
        return "error";
      case "cancelled":
        return "default";
      default:
        return "default";
    }
  };

  return (
    <Chip
      label={status}
      color={getStatusColor() as any}
      size="small"
      variant="outlined"
      sx={{ fontWeight: "medium" }}
    />
  );
};

/**
 * Main tasks table component with pagination, filtering, and sorting
 * Uses server-side operations for all data manipulation
 */
export const TasksTable = () => {
  const [data, setData] = useState<PaginatedTasksResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pagination state
  const [page, setPage] = useState(0); // MUI TablePagination is 0-indexed
  const [rowsPerPage, setRowsPerPage] = useState(5);

  // Sort state - cycles: null → asc → desc → null
  const [sort, setSort] = useState<TaskSortState>({
    column: null,
    order: null,
  });

  // Filter state
  const [filters, setFilters] = useState<TaskFilters>({
    change_request_id: "",
    change_description: "",
    change_status: "",
    path: "",
  });

  // Debounce timer for filter inputs
  const [filterDebounce, setFilterDebounce] = useState<ReturnType<
    typeof setTimeout
  > | null>(null);

  /**
   * Fetches data from server with current pagination, sort, and filter state
   */
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchValidationTasks({
        page: page + 1, // Convert 0-indexed to 1-indexed for API
        pageSize: rowsPerPage,
        sortBy: sort.column,
        sortOrder: sort.order,
        filters,
      });
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch tasks");
    } finally {
      setLoading(false);
    }
  }, [page, rowsPerPage, sort, filters]);

  // Initial load and reload on state changes
  useEffect(() => {
    loadData();
  }, [loadData]);

  /**
   * Handles column header click - cycles sort order
   * Resets to page 0 when sort changes
   */
  const handleSort = (column: keyof ValidationTask) => {
    setSort((prev) => {
      let newOrder: SortOrder;

      if (prev.column !== column) {
        // New column - start with ascending
        newOrder = "asc";
      } else {
        // Same column - cycle: asc → desc → null
        if (prev.order === "asc") newOrder = "desc";
        else if (prev.order === "desc") newOrder = null;
        else newOrder = "asc";
      }

      return {
        column: newOrder ? column : null,
        order: newOrder,
      };
    });
    setPage(0); // Reset to first page on sort change
  };

  /**
   * Handles filter input changes with debouncing
   * Resets to page 0 when filters change
   */
  const handleFilterChange = (key: keyof TaskFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));

    // Debounce API calls
    if (filterDebounce) clearTimeout(filterDebounce);
    setFilterDebounce(
      setTimeout(() => {
        setPage(0); // Reset to first page on filter change
      }, 300)
    );
  };

  /**
   * Clears all filters and resets to initial state
   */
  const handleClearFilters = () => {
    setFilters({
      change_request_id: "",
      change_description: "",
      change_status: "",
      path: "",
    });
    setSort({ column: null, order: null });
    setPage(0);
  };

  /**
   * Regenerates server data and reloads
   */
  const handleRefreshData = async () => {
    try {
      await clearTasksCache();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh data");
    }
  };

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <Paper sx={{ width: "100%", overflow: "hidden", borderRadius: 2 }}>
      {/* Header with actions */}
      <Box
        sx={{
          px: 3,
          py: 2,
          borderBottom: 1,
          borderColor: "divider",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Typography variant="h6" fontWeight="bold">
          Validation Tasks
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button
            startIcon={<FilterListOffIcon />}
            onClick={handleClearFilters}
            variant="outlined"
            size="small"
            color="inherit"
          >
            Clear Filters
          </Button>
          <Button
            startIcon={<RefreshIcon />}
            onClick={handleRefreshData}
            disabled={loading}
            variant="contained"
            size="small"
          >
            {loading ? "Loading..." : "Refresh Data"}
          </Button>
        </Stack>
      </Box>

      {/* Error display */}
      {error && (
        <Alert severity="error" sx={{ borderRadius: 0 }}>
          {error}
        </Alert>
      )}

      {/* Table */}
      <TableContainer sx={{ maxHeight: "calc(100vh - 250px)" }}>
        <Table stickyHeader aria-label="tasks table">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: "bold", width: "15%" }}>
                <SortableHeader
                  column="change_request_id"
                  label="Change ID"
                  currentSort={sort}
                  onSort={handleSort}
                />
              </TableCell>
              <TableCell sx={{ fontWeight: "bold", width: "30%" }}>
                <SortableHeader
                  column="change_description"
                  label="Description"
                  currentSort={sort}
                  onSort={handleSort}
                />
              </TableCell>
              <TableCell sx={{ fontWeight: "bold", width: "15%" }}>
                <SortableHeader
                  column="change_status"
                  label="Status"
                  currentSort={sort}
                  onSort={handleSort}
                />
              </TableCell>
              <TableCell sx={{ fontWeight: "bold", width: "20%" }}>
                <SortableHeader
                  column="created_at"
                  label="Created At"
                  currentSort={sort}
                  onSort={handleSort}
                />
              </TableCell>
              <TableCell sx={{ fontWeight: "bold", width: "20%" }}>
                <SortableHeader
                  column="path"
                  label="Path"
                  currentSort={sort}
                  onSort={handleSort}
                />
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {/* Filter row */}
            <FilterRow filters={filters} onFilterChange={handleFilterChange} />

            {/* Data rows */}
            {loading && !data ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 8 }}>
                  <CircularProgress size={40} />
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 2 }}
                  >
                    Loading tasks...
                  </Typography>
                </TableCell>
              </TableRow>
            ) : data?.tasks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 8 }}>
                  <Typography variant="body1" color="text.secondary">
                    No tasks found matching your filters
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              data?.tasks.map((task, idx) => (
                <TableRow
                  key={`${task.change_request_id}-${idx}`}
                  hover
                  sx={{ "&:last-child td, &:last-child th": { border: 0 } }}
                >
                  <TableCell
                    sx={{ fontFamily: "monospace", color: "primary.main" }}
                  >
                    {task.change_request_id}
                  </TableCell>
                  <TableCell>{task.change_description}</TableCell>
                  <TableCell>
                    <StatusBadge status={task.change_status} />
                  </TableCell>
                  <TableCell
                    sx={{ color: "text.secondary", fontSize: "0.875rem" }}
                  >
                    {task.created_at}
                  </TableCell>
                  <TableCell
                    sx={{
                      fontFamily: "monospace",
                      color: "text.secondary",
                      fontSize: "0.875rem",
                    }}
                  >
                    {task.path}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {data && (
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={data.total}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      )}
    </Paper>
  );
};
