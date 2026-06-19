import AssignmentIcon from "@mui/icons-material/Assignment";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import { Box, Paper, Tab, Tabs, Typography } from "@mui/material";
import { useState } from "react";
import { DiffViewTab } from "./components/DiffViewTab";
import { TasksTable } from "./components/TasksTable";

type TabType = "tasks" | "diff";

/**
 * Network validator page with tabbed interface
 * - Tasks Tab: Paginated table with filtering and sorting demo
 * - Diff View Tab: SSE streaming device validation with per-command chunks
 */
export const ValidatorPage = () => {
  const [activeTab, setActiveTab] = useState<TabType>("tasks");

  const handleChange = (_event: React.SyntheticEvent, newValue: TabType) => {
    setActiveTab(newValue);
  };

  return (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "grey.50",
        borderRadius: 4,
        overflow: "hidden",
        border: 1,
        borderColor: "divider",
      }}
    >
      {/* Header with Tabs */}
      <Paper
        elevation={0}
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        <Box sx={{ px: 3, py: 2 }}>
          <Typography variant="h5" fontWeight="bold" color="text.primary">
            Network Validator
          </Typography>
        </Box>

        {/* Tab Navigation */}
        <Tabs
          value={activeTab}
          onChange={handleChange}
          aria-label="validator tabs"
          sx={{ px: 2 }}
        >
          <Tab
            icon={<AssignmentIcon />}
            iconPosition="start"
            label="Validation Tasks"
            value="tasks"
            sx={{ minHeight: 48 }}
          />
          <Tab
            icon={<CompareArrowsIcon />}
            iconPosition="start"
            label="Device Diff View"
            value="diff"
            sx={{ minHeight: 48 }}
          />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      <Box sx={{ flex: 1, overflow: "hidden" }}>
        {activeTab === "tasks" && (
          <Box sx={{ height: "100%", p: 3, overflow: "auto" }}>
            <TasksTable />
          </Box>
        )}
        {activeTab === "diff" && <DiffViewTab />}
      </Box>
    </Box>
  );
};
