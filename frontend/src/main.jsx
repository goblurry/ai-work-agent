import React from "react";
import { createRoot } from "react-dom/client";
import ErrorBoundary from "./shared/ErrorBoundary";
import Root from "./Root";
import "./shared/styles.css";
createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <Root />
    </ErrorBoundary>
  </React.StrictMode>,
);
