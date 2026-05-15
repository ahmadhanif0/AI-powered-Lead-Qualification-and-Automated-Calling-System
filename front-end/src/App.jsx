import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout           from "./components/Layout";
import Dashboard        from "./pages/Dashboard";
import Assistants       from "./pages/Assistants";
import AssistantDetail  from "./pages/AssistantDetail";
import HubSpot          from "./pages/HubSpot";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="assistants" element={<Assistants />} />
          <Route path="assistants/:id" element={<AssistantDetail />} />
          <Route path="hubspot" element={<HubSpot />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
