/**
 * Root application component with routing and auth protection.
 *
 * Route structure:
 * - /login         → LoginPage (public, no auth needed)
 * - /              → Layout (protected) containing:
 *   - /            → DashboardPage (NL query + chart)
 *   - /saved       → SavedVisualizationsPage
 *   - /settings    → SettingsPage
 *
 * Auth check happens once on mount: checkSession() calls GET /auth/me
 * to see if the existing session cookie is still valid.
 *
 * ProtectedRoute is a wrapper that:
 * 1. Shows "Loading..." while session check is in progress
 * 2. Redirects to /login if no valid session
 * 3. Renders children if authenticated
 *
 * The nested <Route> structure inside the Layout route means Layout
 * renders the sidebar + nav, and <Outlet /> renders the active child page.
 */

import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import SavedVisualizationsPage from "./pages/SavedVisualizationsPage";
import SettingsPage from "./pages/SettingsPage";
import { useAuthStore } from "./stores/authStore";

/**
 * Guard component for authenticated routes.
 * - While auth is loading: show spinner (prevents login page flash)
 * - If not logged in: redirect to /login
 * - If logged in: render the protected content
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { orgId, isLoading } = useAuthStore();
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }
  if (!orgId) return <Navigate to="/login" />;
  return <>{children}</>;
}

export default function App() {
  const checkSession = useAuthStore((s) => s.checkSession);

  // On mount, check if the session cookie is still valid
  useEffect(() => {
    checkSession();
  }, [checkSession]);

  return (
    <Routes>
      {/* Public route - login page */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected routes - wrapped in Layout (sidebar + nav) */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        {/* index = default child route, renders at "/" */}
        <Route index element={<DashboardPage />} />
        <Route path="saved" element={<SavedVisualizationsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
