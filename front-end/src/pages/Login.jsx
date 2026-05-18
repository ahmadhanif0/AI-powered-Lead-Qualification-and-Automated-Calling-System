import { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { LogIn, RefreshCw } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Spinner } from "../components/Spinner";

export default function Login() {
  const { login }    = useAuth();
  const navigate     = useNavigate();
  const location     = useLocation();
  const from         = location.state?.from?.pathname || "/";

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState(null);
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      // Try to parse the FastAPI error body
      try {
        const parsed = JSON.parse(err.message);
        setError(parsed.detail || err.message);
      } catch {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  const inputCls =
    "w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm " +
    "focus:outline-none focus:border-blue-500 transition-colors placeholder-gray-500";

  return (
    <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">

        {/* Logo */}
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center">
            <RefreshCw size={22} className="text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold">AI Lead System</h1>
            <p className="text-gray-400 text-sm mt-1">Sign in to your account</p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Email</label>
            <input
              type="email"
              className={inputCls}
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Password</label>
            <input
              type="password"
              className={inputCls}
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <p className="text-red-400 text-xs bg-red-900/30 border border-red-800 rounded-lg p-3">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50
                       text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            {loading ? <Spinner size={16} /> : <LogIn size={16} />}
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500">
          Don't have an account?{" "}
          <Link to="/signup" className="text-blue-400 hover:text-blue-300 transition-colors">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
