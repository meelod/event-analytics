import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import SavedVisualizationsPage from "./pages/SavedVisualizationsPage";
import SettingsPage from "./pages/SettingsPage";
import { useAuthStore } from "./stores/authStore";

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
  useEffect(() => {
    checkSession();
  }, [checkSession]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="saved" element={<SavedVisualizationsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
