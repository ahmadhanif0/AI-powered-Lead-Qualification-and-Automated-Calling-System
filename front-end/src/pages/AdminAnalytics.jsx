import { useState, useEffect } from "react";
import { BarChart2, Users, Phone, Bot, RefreshCw, TrendingUp } from "lucide-react";
import { api }     from "../api/client";
import { Spinner } from "../components/Spinner";
import { Badge }   from "../components/Badge";
import { useToast } from "../components/Toast";

function StatCard({ icon: Icon, color, label, value, sub }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-start gap-3">
      <Icon className={color} size={20} />
      <div>
        <div className="text-xs text-gray-400">{label}</div>
        <div className="text-2xl font-bold">{value ?? "—"}</div>
        {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

export default function AdminAnalytics() {
  const [overview,    setOverview]    = useState(null);
  const [global,      setGlobal]      = useState(null);
  const [assistants,  setAssistants]  = useState([]);
  const [loading,     setLoading]     = useState(true);
  const { show, ToastEl } = useToast();

  async function load() {
    setLoading(true);
    try {
      const [ov, gl, ast] = await Promise.all([
        api.admin.analytics.overview(),
        api.admin.analytics.global(),
        api.admin.analytics.assistants(),
      ]);
      setOverview(ov);
      setGlobal(gl);
      setAssistants(ast.assistants || []);
    } catch (e) { show(e.message, "error"); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <div className="flex justify-center py-20"><Spinner /></div>;

  const maxCalls = Math.max(...(global?.calls_per_day?.map(d => d.calls) || [1]), 1);

  return (
    <div className="space-y-6">
      {ToastEl}

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2"><BarChart2 size={22} /> Analytics</h1>
        <button onClick={load} className="text-gray-400 hover:text-white"><RefreshCw size={15} /></button>
      </div>

      {/* Overview stats */}
      {overview && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Users}     color="text-blue-400"   label="Total Users"       value={overview.users.total}      sub={`${overview.users.active} active`} />
          <StatCard icon={Phone}     color="text-green-400"  label="Calls Today"       value={overview.calls.today}      sub={`${overview.calls.this_week} this week`} />
          <StatCard icon={Bot}       color="text-purple-400" label="Assistants"        value={overview.assistants} />
          <StatCard icon={TrendingUp}color="text-yellow-400" label="Total Leads"       value={overview.leads} />
        </div>
      )}

      {/* Calls per day chart */}
      {global?.calls_per_day && (
        <div className="bg-gray-900 rounded-xl p-5">
          <h2 className="font-semibold mb-4 text-sm text-gray-400 uppercase tracking-wide">Calls — Last 7 Days</h2>
          <div className="flex items-end gap-2 h-32">
            {global.calls_per_day.map(d => (
              <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-xs text-gray-400">{d.calls}</span>
                <div
                  className="w-full bg-blue-600 rounded-t transition-all"
                  style={{ height: `${Math.max(4, (d.calls / maxCalls) * 100)}%` }}
                />
                <span className="text-xs text-gray-600 rotate-45 origin-left">{d.date.slice(5)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lead status breakdown */}
      {global?.lead_status_breakdown && (
        <div className="bg-gray-900 rounded-xl p-5">
          <h2 className="font-semibold mb-4 text-sm text-gray-400 uppercase tracking-wide">Lead Status Breakdown</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(global.lead_status_breakdown).filter(([k]) => k !== "total").map(([k, v]) => (
              <div key={k} className="bg-gray-800 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-white">{v}</div>
                <div className="text-xs text-gray-400 mt-1">{k}</div>
                <div className="text-xs text-gray-600">
                  {global.lead_status_breakdown.total > 0
                    ? `${Math.round(v / global.lead_status_breakdown.total * 100)}%`
                    : "0%"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Assistant performance */}
      {assistants.length > 0 && (
        <div className="bg-gray-900 rounded-xl overflow-x-auto">
          <div className="p-4 border-b border-gray-800 font-semibold text-sm text-gray-400 uppercase tracking-wide flex items-center gap-2">
            <Bot size={15} /> Assistant Performance
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-gray-800">
                <th className="text-left p-3">Assistant</th>
                <th className="text-left p-3">Owner</th>
                <th className="text-left p-3">Total Calls</th>
                <th className="text-left p-3">Success Rate</th>
                <th className="text-left p-3">Avg Duration</th>
              </tr>
            </thead>
            <tbody>
              {assistants.map(a => (
                <tr key={a.assistant_id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="p-3 font-medium">{a.name}</td>
                  <td className="p-3 text-gray-400 text-xs">User #{a.owner_user_id}</td>
                  <td className="p-3">{a.total_calls}</td>
                  <td className="p-3">
                    <span className={a.success_rate >= 50 ? "text-green-400" : "text-yellow-400"}>
                      {a.success_rate}%
                    </span>
                  </td>
                  <td className="p-3 text-gray-400">{a.avg_duration_sec}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Retry trends */}
      {global?.retry_trends && (
        <div className="bg-gray-900 rounded-xl p-5">
          <h2 className="font-semibold mb-3 text-sm text-gray-400 uppercase tracking-wide">Retry Queue Trends</h2>
          <div className="flex gap-4">
            {Object.entries(global.retry_trends).map(([k, v]) => (
              <div key={k} className="bg-gray-800 rounded-lg px-4 py-3 text-center">
                <div className="text-xl font-bold">{v}</div>
                <div className="text-xs text-gray-400 capitalize mt-1">{k}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
