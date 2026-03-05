/**
 * App shell layout with sidebar navigation.
 *
 * Uses React Router's <Outlet /> pattern:
 * - Layout renders the sidebar (nav links + logout button)
 * - <Outlet /> is a placeholder that React Router fills with the active child route
 * - When you navigate to "/saved", Layout stays mounted and Outlet swaps to SavedVisualizationsPage
 *
 * This avoids re-rendering the sidebar on every page navigation.
 *
 * Active nav highlighting: compares current location.pathname to each nav item's
 * path and applies indigo styles to the matching one.
 */

import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";

export default function Layout() {
  const { orgName, logout } = useAuthStore();
  const location = useLocation();

  const navItems = [
    { path: "/", label: "Dashboard" },
    { path: "/saved", label: "Saved" },
    { path: "/settings", label: "Settings" },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-lg font-bold text-gray-900">Event Analytics</h1>
          <p className="text-xs text-gray-500 mt-1 truncate">{orgName}</p>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                location.pathname === item.path
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-3 border-t border-gray-200">
          <button
            onClick={logout}
            className="w-full px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
          >
            Logout
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <div className="p-6 max-w-6xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
