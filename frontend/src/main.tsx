/**
 * Application entry point.
 *
 * Sets up:
 * - StrictMode: enables extra React dev checks (double-renders in dev to catch bugs)
 * - BrowserRouter: provides client-side routing via the History API
 *   (placed here, outside App, so App can use useNavigate/useLocation hooks)
 * - index.css: Tailwind CSS base styles + any custom CSS
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.tsx";
import "./index.css";

// The "!" asserts that #root exists (it's in index.html)
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);
