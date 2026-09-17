import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./styles.css";
import Landing from "./views/Landing";
import Admin from "./views/Admin";
import Agent from "./views/Agent";
import Customer from "./views/Customer";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/agent" element={<Agent />} />
        <Route path="/customer" element={<Customer />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
