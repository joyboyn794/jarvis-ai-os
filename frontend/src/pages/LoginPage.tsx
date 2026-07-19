import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authApi } from '../services/api';
import { Eye, EyeOff, Mail, Lock, User, Sparkles, ArrowRight, Cpu } from 'lucide-react';

export function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [mounted, setMounted] = useState(false);

  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 100);
    return () => clearTimeout(t);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        await authApi.register(email, password, displayName);
      }
      const tokens = await authApi.login(email, password);
      const user = await authApi.getMe();
      setAuth(user, tokens.access_token, tokens.refresh_token);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-jarvis-bg p-4 relative overflow-hidden">
      {/* Background Grid Effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, #3b82f6 1px, transparent 0)`,
            backgroundSize: '32px 32px',
          }}
        />
        <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-jarvis-accent/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-blue-400/5 rounded-full blur-[100px]" />
      </div>

      <div
        className={`w-full max-w-[420px] transition-all duration-700 ease-out ${
          mounted ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
      >
        {/* Logo & Header */}
        <div className="text-center mb-8">
          {/* Arc Reactor Logo */}
          <div className="relative w-20 h-20 mx-auto mb-5">
            {/* Outer Ring */}
            <div className="absolute inset-0 rounded-full border-2 border-jarvis-accent/30 animate-[spin_8s_linear_infinite]" />
            {/* Middle Ring */}
            <div
              className="absolute inset-[6px] rounded-full border border-jarvis-accent/20 animate-spin"
              style={{ animationDuration: '6s', animationDirection: 'reverse' }}
            />
            {/* Inner Ring */}
            <div className="absolute inset-[14px] rounded-full bg-jarvis-accent/10 flex items-center justify-center">
              <div className="w-6 h-6 rounded-full bg-jarvis-accent jarvis-orb" />
            </div>
            {/* Glow */}
            <div className="absolute -inset-4 rounded-full bg-jarvis-accent/10 blur-2xl" />
          </div>

          <h1 className="text-3xl font-bold text-jarvis-text tracking-tight">
            Jarvis AI OS
          </h1>
          <p className="text-jarvis-text-muted mt-2 text-sm">
            Intelligent assistant at your service
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-jarvis-surface/80 backdrop-blur-xl border border-jarvis-border/80 rounded-2xl p-6 shadow-2xl shadow-jarvis-accent/5">
          {/* Tab Switcher */}
          <div className="flex bg-jarvis-bg rounded-xl p-1 mb-6">
            <button
              onClick={() => { setIsRegister(false); setError(''); }}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-300 ${
                !isRegister
                  ? 'bg-jarvis-accent text-white shadow-lg shadow-jarvis-accent/25'
                  : 'text-jarvis-text-muted hover:text-jarvis-text'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => { setIsRegister(true); setError(''); }}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-300 ${
                isRegister
                  ? 'bg-jarvis-accent text-white shadow-lg shadow-jarvis-accent/25'
                  : 'text-jarvis-text-muted hover:text-jarvis-text'
              }`}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Display Name (Register only) */}
            <div
              className={`transition-all duration-300 ease-out overflow-hidden ${
                isRegister ? 'max-h-20 opacity-100 mb-0' : 'max-h-0 opacity-0 mb-0'
              }`}
            >
              <div className="relative">
                <User
                  size={16}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-text-muted pointer-events-none"
                />
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full pl-10 pr-3 py-2.5 bg-jarvis-bg border border-jarvis-border rounded-xl text-jarvis-text placeholder:text-jarvis-text-muted/60 focus:border-jarvis-accent focus:ring-2 focus:ring-jarvis-accent/20 transition-all outline-none text-sm"
                  placeholder="Tony Stark"
                  required={isRegister}
                  minLength={2}
                  tabIndex={isRegister ? 0 : -1}
                />
              </div>
            </div>

            {/* Email */}
            <div className="relative">
              <Mail
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-text-muted pointer-events-none"
              />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-3 py-2.5 bg-jarvis-bg border border-jarvis-border rounded-xl text-jarvis-text placeholder:text-jarvis-text-muted/60 focus:border-jarvis-accent focus:ring-2 focus:ring-jarvis-accent/20 transition-all outline-none text-sm"
                placeholder="tony@starkindustries.com"
                required
              />
            </div>

            {/* Password */}
            <div className="relative">
              <Lock
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-jarvis-text-muted pointer-events-none"
              />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-10 py-2.5 bg-jarvis-bg border border-jarvis-border rounded-xl text-jarvis-text placeholder:text-jarvis-text-muted/60 focus:border-jarvis-accent focus:ring-2 focus:ring-jarvis-accent/20 transition-all outline-none text-sm"
                placeholder="••••••••"
                required
                minLength={8}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-jarvis-text-muted hover:text-jarvis-text transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {/* Error */}
            <div
              className={`transition-all duration-300 overflow-hidden ${
                error ? 'max-h-20 opacity-100' : 'max-h-0 opacity-0'
              }`}
            >
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-2 text-red-400 text-sm">
                <div className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
                {error}
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full relative py-2.5 bg-jarvis-accent hover:bg-jarvis-accent/90 disabled:opacity-60 text-white font-medium rounded-xl transition-all duration-300 hover:shadow-lg hover:shadow-jarvis-accent/25 active:scale-[0.98] overflow-hidden group"
            >
              <span
                className={`inline-flex items-center gap-2 transition-all duration-300 ${
                  loading ? 'opacity-0' : 'opacity-100'
                }`}
              >
                {isRegister ? 'Create Account' : 'Sign In'}
                <ArrowRight
                  size={16}
                  className="group-hover:translate-x-1 transition-transform"
                />
              </span>
              {loading && (
                <span className="absolute inset-0 flex items-center justify-center">
                  <svg
                    className="animate-spin h-5 w-5 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12" cy="12" r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                </span>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-jarvis-border/50" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-3 text-xs text-jarvis-text-muted bg-jarvis-surface rounded-full">
                JARVIS v0.1
              </span>
            </div>
          </div>

          {/* Status */}
          <div className="flex items-center justify-center gap-4 text-xs text-jarvis-text-muted">
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-jarvis-success" />
              Systems Online
            </div>
            <div className="flex items-center gap-1.5">
              <Cpu size={12} />
              Groq / Llama 3.1
            </div>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-jarvis-text-muted/50 mt-6">
          Powered by Groq · Free & Open Source
        </p>
      </div>
    </div>
  );
}
