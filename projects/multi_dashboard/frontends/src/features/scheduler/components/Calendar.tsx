import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import {
  Box,
  ButtonBase,
  Grid,
  IconButton,
  Paper,
  Typography,
} from "@mui/material";
import {
  addDays,
  addMonths,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  parseISO,
  startOfMonth,
  startOfWeek,
} from "date-fns";

export interface CalendarEventSummary {
  id: number;
  start_time: string;
}

interface CalendarProps {
  currentMonth: Date;
  events: CalendarEventSummary[];
  selectedDate: Date;
  onSelectDate: (date: Date) => void;
  onMonthChange: (nextMonth: Date) => void;
}

export function Calendar({
  currentMonth,
  events,
  selectedDate,
  onSelectDate,
  onMonthChange,
}: CalendarProps) {
  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(monthStart);
  const startDate = startOfWeek(monthStart);
  const endDate = endOfWeek(monthEnd);

  const eventsPerDay = events.reduce<Record<string, number>>((acc, event) => {
    const dateKey = format(parseISO(event.start_time), "yyyy-MM-dd");
    acc[dateKey] = (acc[dateKey] ?? 0) + 1;
    return acc;
  }, {});

  const rows: JSX.Element[] = [];
  let day = startDate;
  while (day <= endDate) {
    const days: JSX.Element[] = [];

    for (let i = 0; i < 7; i += 1) {
      const cloneDay = day;
      const formattedDate = format(day, "d");
      const key = format(day, "yyyy-MM-dd");
      const inMonth = isSameMonth(day, monthStart);
      const isSelected = isSameDay(day, selectedDate);
      const count = eventsPerDay[key] ?? 0;

      days.push(
        <Grid size={{ xs: 1 }} key={key}>
          <ButtonBase
            onClick={() => onSelectDate(cloneDay)}
            sx={{
              width: "100%",
              height: 80,
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start",
              justifyContent: "flex-start",
              gap: 1,
              borderRadius: 3,
              p: 1,
              bgcolor: isSelected
                ? "rgba(var(--mui-palette-primary-mainChannel) / 0.1)"
                : "grey.50",
              color: isSelected
                ? "primary.main"
                : inMonth
                ? "text.primary"
                : "text.disabled",
              border: 1,
              borderColor: isSelected ? "primary.main" : "transparent",
              transition: "all 0.2s",
              "&:hover": {
                bgcolor: isSelected
                  ? "rgba(var(--mui-palette-primary-mainChannel) / 0.2)"
                  : "rgba(var(--mui-palette-primary-mainChannel) / 0.05)",
              },
            }}
          >
            <Typography variant="body2" fontWeight="medium">
              {formattedDate}
            </Typography>
            {count > 0 && (
              <Box
                sx={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: 999,
                  bgcolor: "primary.main",
                  px: 1,
                  py: 0.25,
                  color: "white",
                  fontSize: "0.75rem",
                  fontWeight: "bold",
                }}
              >
                {count}
              </Box>
            )}
          </ButtonBase>
        </Grid>
      );

      day = addDays(day, 1);
    }

    const weekKey = format(addDays(day, -1), "yyyy-MM-dd");
    rows.push(
      <Grid container spacing={1} columns={7} key={weekKey} sx={{ mb: 1 }}>
        {days}
      </Grid>
    );
  }

  return (
    <Paper
      elevation={3}
      sx={{
        p: 3,
        borderRadius: 4,
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <IconButton
          onClick={() => onMonthChange(addMonths(monthStart, -1))}
          aria-label="Previous month"
          sx={{ bgcolor: "grey.200", "&:hover": { bgcolor: "grey.300" } }}
        >
          <ChevronLeftIcon />
        </IconButton>
        <Typography variant="h6" fontWeight="bold">
          {format(monthStart, "LLLL yyyy")}
        </Typography>
        <IconButton
          onClick={() => onMonthChange(addMonths(monthStart, 1))}
          aria-label="Next month"
          sx={{ bgcolor: "grey.200", "&:hover": { bgcolor: "grey.300" } }}
        >
          <ChevronRightIcon />
        </IconButton>
      </Box>

      <Grid container spacing={1} columns={7}>
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((weekday) => (
          <Grid size={{ xs: 1 }} key={weekday}>
            <Typography
              variant="caption"
              fontWeight="bold"
              sx={{
                display: "block",
                textAlign: "center",
                textTransform: "uppercase",
                letterSpacing: 1,
                color: "text.secondary",
                mb: 1,
              }}
            >
              {weekday}
            </Typography>
          </Grid>
        ))}
      </Grid>

      <Box sx={{ display: "flex", flexDirection: "column" }}>{rows}</Box>
    </Paper>
  );
}
