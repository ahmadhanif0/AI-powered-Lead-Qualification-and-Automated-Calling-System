import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, Bot, RefreshCw, Database } from "lucide-react";

const NAV = [
  { to: "/",           label: "Dashboard",  icon: LayoutDashboard },
  { to: "/assistants", label: "Assistants", icon: Bot },
  { to: "/hubspot",    label: "HubSpot",    icon: Database },
];

const linkCls = ({ isActive }) =>
  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
    isActive
      ? "bg-blue-600 text-white font-medium"
      : "text-gray-400 hover:text-white hover:bg-gray-800"
  }`;

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-950 text-white flex">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 border-r border-gray-800 flex flex-col p-4 gap-1">
        {/* Logo */}
        <div className="flex items-center gap-2 px-3 py-3 mb-4">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <RefreshCw size={14} className="text-white" />
          </div>
          <span className="font-bold text-sm">AI Lead System</span>
        </div>

        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === "/"} className={linkCls}>
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
