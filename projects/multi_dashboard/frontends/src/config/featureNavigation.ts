export interface FeatureNavItem {
  path: string;
  label: string;
  description: string;
  keywords: string[];
  quickAccess?: boolean;
}

export interface FeatureNavGroup {
  id: string;
  label: string;
  description: string;
  items: FeatureNavItem[];
}

export const FEATURE_HUB_PATH = "/features";

export const FEATURE_NAV_GROUPS: FeatureNavGroup[] = [
  {
    id: "assistant",
    label: "Assistant",
    description: "Chat and validation workflows",
    items: [
      {
        path: "/agentic-chat",
        label: "Agentic Chat",
        description: "LangGraph multi-agent chat with Inventory, Network, Grafana & FlowIQ sub-agents",
        keywords: ["agentic", "langgraph", "agents", "mcp", "langchain", "network", "ai", "grafana", "flowiq"],
        quickAccess: true,
      },
      {
        path: "/chat-py",
        label: "Chat (Python)",
        description: "WebSocket, REST & SSE with Python/FastAPI backend",
        keywords: ["chat", "python", "fastapi", "assistant"],
        quickAccess: true,
      },
      {
        path: "/chat-go",
        label: "Chat (Go)",
        description: "WebSocket, REST & SSE with Go/Fiber backend",
        keywords: ["chat", "go", "fiber", "assistant"],
      },
      {
        path: "/validator",
        label: "Validator",
        description: "Diff view for pre/post network validation checks",
        keywords: ["validator", "diff", "network", "checks"],
      },
    ],
  },
  {
    id: "planning",
    label: "Planning",
    description: "Calendar and task management",
    items: [
      {
        path: "/scheduler",
        label: "Scheduler",
        description: "Plan events and visualize them on the calendar",
        keywords: ["calendar", "events", "plan", "schedule"],
        quickAccess: true,
      },
      {
        path: "/reminders",
        label: "Reminders",
        description: "Manage notification times tied to your events",
        keywords: ["reminder", "notification", "events"],
      },
      {
        path: "/todos",
        label: "Todos",
        description: "Track lightweight tasks with quick check-offs",
        keywords: ["todo", "tasks", "checklist", "productivity"],
      },
    ],
  },
  {
    id: "finance",
    label: "Finance",
    description: "Personal finance calculators",
    items: [
      {
        path: "/investment",
        label: "Investment",
        description: "CAGR projection with monthly & lumpsum inputs",
        keywords: ["investment", "cagr", "returns", "calculator"],
      },
      {
        path: "/mortgage",
        label: "Mortgage",
        description: "Amortization with optional extra payments",
        keywords: ["mortgage", "amortization", "loan", "finance"],
        quickAccess: true,
      },
      {
        path: "/housing-compare",
        label: "Buy vs Rent",
        description: "Combined mortgage, rent, and investment scenario view",
        keywords: ["buy vs rent", "housing", "comparison", "finance"],
      },
      {
        path: "/salary-projection",
        label: "Salary Projection",
        description: "Savings & investment projection from salary and expenses",
        keywords: ["salary", "savings", "projection", "investment", "expenses"],
      },
    ],
  },
  {
    id: "commerce",
    label: "Commerce",
    description: "Marketplace workflows",
    items: [
      {
        path: "/marketplace",
        label: "Marketplace",
        description: "Contract-first demo with Kafka event-driven architecture",
        keywords: ["marketplace", "contracts", "kafka", "events"],
      },
    ],
  },
  {
    id: "notifications",
    label: "Notifications",
    description: "Notification preferences and delivery settings",
    items: [
      {
        path: "/preferences",
        label: "Preferences",
        description: "Choose which channels (email, push, WhatsApp) receive tax filing reminders",
        keywords: ["notification", "preferences", "email", "push", "whatsapp", "ntfy", "reminder"],
        quickAccess: false,
      },
    ],
  },
  {
    id: "tax",
    label: "Tax",
    description: "Corporate tax filing reminders and preparation",
    items: [
      {
        path: "/tax/corporations",
        label: "Corporations",
        description: "Manage corporation profiles and details",
        keywords: ["tax", "corporation", "profile", "corp"],
      },
      {
        path: "/tax/dashboard",
        label: "Tax Deadlines",
        description: "Upcoming filing deadlines with scheduler reminders",
        keywords: ["tax", "deadline", "annual return", "gst", "hst", "t2", "reminder"],
        quickAccess: true,
      },
      {
        path: "/tax/nil-t2",
        label: "Nil T2 Report",
        description: "Generate a nil T2 return for zero-income corporations",
        keywords: ["t2", "nil", "zero income", "corporate tax", "cra"],
      },
    ],
  },
];

export const QUICK_ACCESS_ITEMS = FEATURE_NAV_GROUPS.flatMap((group) =>
  group.items.filter((item) => item.quickAccess),
);
