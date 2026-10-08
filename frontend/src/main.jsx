import React from "react";
import { createRoot } from "react-dom/client";
import StudentApp from "./student/StudentApp";
import "./shared/styles.css";
createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <StudentApp />
  </React.StrictMode>,
);
