import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { AuthCallbackPage } from "./features/auth/AuthCallbackPage";
import { LoginPage } from "./features/auth/LoginPage";
import { ProtectedRoute } from "./features/auth/ProtectedRoute";
import { AgenticChatPage } from "./features/agentic-chat/AgenticChatPage";
import { ChatPage as ChatPageGo } from "./features/chat_go/ChatPage";
import { ChatPage as ChatPagePy } from "./features/chat_py/ChatPage";
import { HousingComparisonPage } from "./features/finance/housing/HousingComparisonPage";
import { InvestmentPage } from "./features/finance/investment/InvestmentPage";
import { MortgagePage } from "./features/finance/mortgage/MortgagePage";
import { SalaryProjectionPage } from "./features/finance/salary/SalaryProjectionPage";
import { FeatureHubPage } from "./features/home/FeatureHubPage";
import MarketplacePage from "./features/marketplace/MarketplacePage";
import { RemindersPage } from "./features/scheduler/RemindersPage";
import { SchedulerPage } from "./features/scheduler/SchedulerPage";
import { CorporationPage } from "./features/tax/CorporationPage";
import { NilT2Page } from "./features/tax/NilT2Page";
import { TaxDashboardPage } from "./features/tax/TaxDashboardPage";
import { TodosPage } from "./features/todos/TodosPage";
import { ValidatorPage } from "./features/validator/ValidatorPage";
import { PreferencesPage } from "./features/preferences/PreferencesPage";

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />

      {/* Protected routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/features" replace />} />
        <Route path="features" element={<FeatureHubPage />} />
        <Route path="agentic-chat" element={<AgenticChatPage />} />
        <Route path="chat-py" element={<ChatPagePy />} />
        <Route path="chat-go" element={<ChatPageGo />} />
        <Route path="scheduler" element={<SchedulerPage />} />
        <Route path="reminders" element={<RemindersPage />} />
        <Route path="todos" element={<TodosPage />} />
        <Route path="investment" element={<InvestmentPage />} />
        <Route path="mortgage" element={<MortgagePage />} />
        <Route path="housing-compare" element={<HousingComparisonPage />} />
        <Route path="salary-projection" element={<SalaryProjectionPage />} />
        <Route path="validator" element={<ValidatorPage />} />
        <Route path="marketplace" element={<MarketplacePage />} />
        <Route path="tax/corporations" element={<CorporationPage />} />
        <Route path="tax/dashboard" element={<TaxDashboardPage />} />
        <Route path="tax/nil-t2" element={<NilT2Page />} />
        <Route path="preferences" element={<PreferencesPage />} />
        <Route path="*" element={<Navigate to="/features" replace />} />
      </Route>
    </Routes>
  );
}
