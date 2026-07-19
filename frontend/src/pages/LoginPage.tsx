import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authApi } from '../services/api';
import { Eye, EyeOff, Mail, Lock, User, ArrowRight, Cpu } from 'lucide-react';

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
      const user = await authApi.getMe(tokens.access_token);
      setAuth(user, tokens.access_token, tokens.refresh_token);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f] p-4 relative overflow-hidden">
      {/* ── Animated Gradient Background ── */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Gradient waves */}
        <div className="absolute top-[-10%] left-[-20%] w-[600px] h-[600px] rounded-full opacity-20 animate-[float_12s_ease-in-out_infinite]"
          style={{
            background: 'radial-gradient(circle, rgba(59,130,246,0.3) 0%, transparent 70%)',
            filter: 'blur(80px)',
          }}
        />
        <div className="absolute bottom-[-10%] right-[-15%] w-[500px] h-[500px] rounded-full opacity-20 animate-[float_10s_ease-in-out_infinite_2s]"
          style={{
            background: 'radial-gradient(circle, rgba(139,92,246,0.3) 0%, transparent 70%)',
            filter: 'blur(80px)',
          }}
        />
        <div className="absolute top-[40%] left-[50%] w-[400px] h-[400px] rounded-full opacity-15 animate-[float_14s_ease-in-out_infinite_4s]"
          style={{
            background: 'radial-gradient(circle, rgba(6,182,212,0.25) 0%, transparent 70%)',
            filter: 'blur(60px)',
          }}
        />
        
        {/* Grid */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, #3b82f6 1px, transparent 0)`,
            backgroundSize: '32px 32px',
          }}
        />
      </div>

      <div
        className={`w-full max-w-[420px] transition-all duration-700 ease-out ${
          mounted ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}
      >
        {/* ── Logo & Header ── */}
        <div className="text-center mb-8">
          {/* Arc Reactor with Gradient Glow */}
          <div className="relative w-24 h-24 mx-auto mb-6">
            {/* Outer Glow */}
            <div className="absolute -inset-6 rounded-full opacity-40 animate-[pulse_3s_ease-in-out_infinite]"
              style={{
                background: 'radial-gradient(circle, rgba(59,130,246,0.4), rgba(139,92,246,0.2), transparent)',
                filter: 'blur(20px)',
              }}
            />
            {/* Outer Ring - slow spin */}
            <div className="absolute inset-0 rounded-full animate-[spin_8s_linear_infinite]"
              style={{
                background: 'conic-gradient(from 0deg, #3b82f6, #8b5cf6, #06b6d4, #3b82f6)',
                padding: '2px',
                mask: 'radial-gradient(transparent 55%, black 60%)',
                WebkitMask: 'radial-gradient(transparent 55%, black 60%)',
              }}
            />
            {/* Middle Ring - reverse spin */}
            <div className="absolute inset-[8px] rounded-full animate-spin"
              style={{
                animationDuration: '4s',
                animationDirection: 'reverse',
                background: 'conic-gradient(from 180deg, #06b6d4, #3b82f6, #8b5cf6, #06b6d4)',
                mask: 'radial-gradient(transparent 60%, black 65%)',
                WebkitMask: 'radial-gradient(transparent 60%, black 65%)',
              }}
            />
            {/* Inner Core */}
            <div className="absolute inset-[18px] rounded-full flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(139,92,246,0.1))' }}
            >
              <div className="w-6 h-6 rounded-full jarvis-orb"
                style={{ background: 'linear-gradient(135deg, #3b82f6, #8b5cf6, #06b6d4)' }}
              />
            </div>
          </div>

          {/* Gradient Title */}
          <h1 className="text-4xl font-extrabold tracking-tight mb-2"
            style={{
              background: 'linear-gradient(135deg, #60a5fa 0%, #a78bfa 40%, #22d3ee 70%, #60a5fa 100%)',
              backgroundSize: '200% auto',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              animation: 'shimmer 4s linear infinite',
            }}
          >
            Jarvis AI OS
          </h1>
          <p className="text-gray-500 mt-2 text-sm tracking-wide">
            Intelligent assistant at your service
          </p>
        </div>

        {/* ── Form Card with Gradient Border ── */}
        <div className="relative rounded-2xl p-[1px]"
          style={{
            background: 'linear-gradient(135deg, rgba(59,130,246,0.3), rgba(139,92,246,0.3), rgba(6,182,212,0.2), rgba(59,130,246,0.3))',
          }}
        >
          <div className="bg-[#0f0f1a]/90 backdrop-blur-2xl rounded-2xl p-6 shadow-2xl"
            style={{ boxShadow: '0 0 40px rgba(59,130,246,0.08), 0 0 80px rgba(139,92,246,0.04)' }}
          >
            {/* Tab Switcher */}
            <div className="flex bg-[#0a0a12] rounded-xl p-1 mb-6">
              <button
                onClick={() => { setIsRegister(false); setError(''); }}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-300 ${
                  !isRegister
                    ? 'text-white shadow-lg'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
                style={!isRegister ? {
                  background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                  boxShadow: '0 4px 15px rgba(59,130,246,0.3)',
                } : {}}
              >
                Sign In
              </button>
              <button
                onClick={() => { setIsRegister(true); setError(''); }}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-300 ${
                  isRegister
                    ? 'text-white shadow-lg'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
                style={isRegister ? {
                  background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                  boxShadow: '0 4px 15px rgba(59,130,246,0.3)',
                } : {}}
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
                <div className="relative group">
                  <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-blue-400 transition-colors pointer-events-none z-10" />
                  <input
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    className="w-full pl-10 pr-3 py-2.5 bg-[#0a0a12] border border-gray-800 rounded-xl text-gray-200 placeholder:text-gray-600 focus:outline-none transition-all text-sm"
                    style={{
                      borderImage: 'linear-gradient(135deg, rgba(59,130,246,0.5), rgba(139,92,246,0.5)) 1',
                    }}
                    placeholder="Tony Stark"
                    required={isRegister}
                    minLength={2}
                    tabIndex={isRegister ? 0 : -1}
                  />
                </div>
              </div>

              {/* Email */}
              <div className="relative group">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-blue-400 transition-colors pointer-events-none z-10" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-3 py-2.5 bg-[#0a0a12] border border-gray-800 rounded-xl text-gray-200 placeholder:text-gray-600 focus:outline-none transition-all text-sm focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/10"
                  placeholder="tony@starkindustries.com"
                  required
                />
              </div>

              {/* Password */}
              <div className="relative group">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-blue-400 transition-colors pointer-events-none z-10" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-10 py-2.5 bg-[#0a0a12] border border-gray-800 rounded-xl text-gray-200 placeholder:text-gray-600 focus:outline-none transition-all text-sm focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/10"
                  placeholder="••••••••"
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
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

              {/* ── Gradient Submit Button ── */}
              <button
                type="submit"
                disabled={loading}
                className="w-full relative py-3 text-white font-semibold rounded-xl transition-all duration-300 active:scale-[0.98] disabled:opacity-50 overflow-hidden group"
                style={{
                  background: 'linear-gradient(135deg, #3b82f6, #8b5cf6, #06b6d4)',
                  backgroundSize: '200% 200%',
                  animation: 'gradient-shift 3s ease infinite',
                  boxShadow: '0 4px 25px rgba(59,130,246,0.35)',
                }}
              >
                {/* Hover shine */}
                <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                  style={{
                    background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)',
                    transform: 'translateX(-100%)',
                    animation: 'shine 1.5s ease-in-out infinite',
                  }}
                />
                <span
                  className={`inline-flex items-center gap-2 transition-all duration-300 ${
                    loading ? 'opacity-0' : 'opacity-100'
                  }`}
                >
                  {isRegister ? 'Create Account' : 'Sign In'}
                  <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </span>
                {loading && (
                  <span className="absolute inset-0 flex items-center justify-center">
                    <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  </span>
                )}
              </button>
            </form>

            {/* Gradient Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full h-px"
                  style={{ background: 'linear-gradient(90deg, transparent, rgba(59,130,246,0.3), rgba(139,92,246,0.3), transparent)' }}
                />
              </div>
              <div className="relative flex justify-center">
                <span className="px-4 text-xs text-gray-600 bg-[#0f0f1a] rounded-full tracking-widest">
                  JARVIS v0.1
                </span>
              </div>
            </div>

            {/* Status */}
            <div className="flex items-center justify-center gap-4 text-xs text-gray-500">
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]" />
                Systems Online
              </div>
              <div className="flex items-center gap-1.5">
                <Cpu size={12} className="text-blue-400" />
                Groq / Llama 3.1
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-gray-700 mt-6 tracking-wide">
          Powered by Groq · Free &amp; Open Source
        </p>
      </div>

      {/* ── CSS Animations ── */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(30px, -30px) scale(1.05); }
          66% { transform: translate(-20px, 20px) scale(0.95); }
        }
        @keyframes shimmer {
          0% { background-position: 0% center; }
          100% { background-position: 200% center; }
        }
        @keyframes gradient-shift {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        @keyframes shine {
          100% { transform: translateX(100%); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.6; }
        }
      `}</style>
    </div>
  );
}
