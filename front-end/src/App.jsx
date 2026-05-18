import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider }    from "./context/AuthContext";
import { ProtectedRoute }  from "./components/ProtectedRoute";
import Layout              from "./components/Layout";

// Public
import Login               from "./pages/Login";
import Signup              from "./pages/Signup";

// User pages
import Dashboard           from "./pages/Dashboard";
import Leads               from "./pages/Leads";
import Assistants          from "./pages/Assistants";
import AssistantDetail     from "./pages/AssistantDetail";
import HubSpot             from "./pages/HubSpot";
import ScheduledCalls      from "./pages/ScheduledCalls";
import Settings            from "./pages/Settings";

// Admin pages
import AdminUsers          from "./pages/AdminUsers";
import AdminAnalytics      from "./pages/AdminAnalytics";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* ── Public ── */}
          <Route path="/login"  element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* ── Protected (requires login) ── */}
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index                  element={<Dashboard />} />
            <Route path="leads"           element={<Leads />} />
            <Route path="assistants"      element={<Assistants />} />
            <Route path="assistants/:id"  element={<AssistantDetail />} />
            <Route path="hubspot"         element={<HubSpot />} />
            <Route path="scheduled"       element={<ScheduledCalls />} />
            <Route path="settings"        element={<Settings />} />

            {/* ── Admin-only ── */}
            <Route
              path="admin/users"
              element={
                <ProtectedRoute adminOnly>
                  <AdminUsers />
                </ProtectedRoute>
              }
            />
            <Route
              path="admin/analytics"
              element={
                <ProtectedRoute adminOnly>
                  <AdminAnalytics />
                </ProtectedRoute>
              }
            />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
