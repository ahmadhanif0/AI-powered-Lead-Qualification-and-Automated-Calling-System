import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LayoutDashboard, Users, Bot, Database, Shield, LogOut, RefreshCw, ChevronDown, Settings, Calendar, BarChart2 } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

const USER_NAV = [
  { to: "/",          label: "Dashboard",  icon: LayoutDashboard },
  { to: "/leads",     label: "Leads",      icon: Users },
  { to: "/assistants",label: "Assistants", icon: Bot },
  { to: "/scheduled", label: "Scheduled",  icon: Calendar },
  { to: "/hubspot",   label: "HubSpot",    icon: Database },
  { to: "/settings",  label: "Settings",   icon: Settings },
];

const ADMIN_NAV = [
  { to: "/admin/users",     label: "Users",     icon: Shield },
  { to: "/admin/analytics", label: "Analytics", icon: BarChart2 },
];

const linkCls = ({ isActive }) =>
  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
    isActive ? "bg-blue-600 text-white font-medium" : "text-gray-400 hover:text-white hover:bg-gray-800"
  }`;

export default function Layout() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex">
      <aside className="w-56 shrink-0 border-r border-gray-800 flex flex-col p-4">
        {/* Logo */}
        <div className="flex items-center gap-2 px-3 py-3 mb-4">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <RefreshCw size={14} className="text-white" />
          </div>
          <span className="font-bold text-sm">AI Lead System</span>
        </div>

        <nav className="flex flex-col gap-1 flex-1">
          {USER_NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"} className={linkCls}>
              <Icon size={16} /> {label}
            </NavLink>
          ))}

          {isAdmin && (
            <>
              <div className="mt-4 mb-1 px-3 text-xs text-gray-600 uppercase tracking-wider">Admin</div>
              {ADMIN_NAV.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} className={linkCls}>
                  <Icon size={16} /> {label}
                </NavLink>
              ))}
            </>
          )}
        </nav>

        {/* User info */}
        <div className="border-t border-gray-800 pt-3 mt-3">
          <button onClick={() => setShowUserMenu(v => !v)}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-800 transition-colors text-left">
            <div className="w-7 h-7 rounded-full bg-blue-700 flex items-center justify-center text-xs font-bold shrink-0">
              {user?.full_name?.[0]?.toUpperCase() || "U"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium truncate">{user?.full_name}</div>
              <div className="text-xs text-gray-500 capitalize">{user?.role}</div>
            </div>
            <ChevronDown size={13} className={`text-gray-500 transition-transform ${showUserMenu ? "rotate-180" : ""}`} />
          </button>
          {showUserMenu && (
            <button onClick={handleLogout}
              className="w-full flex items-center gap-2 px-3 py-2 mt-1 rounded-lg text-red-400 hover:bg-red-900/20 transition-colors text-sm">
              <LogOut size={14} /> Sign Out
            </button>
          )}
        </div>
      </aside>

      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
