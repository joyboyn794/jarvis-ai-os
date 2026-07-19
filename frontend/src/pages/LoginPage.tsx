import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { authApi } from '../services/api';

export function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const setAuth = useAuthStore((s) => s.setAuth);
  const navigate = useNavigate();

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
    <div className="min-h-screen flex items-center justify-center bg-jarvis-bg p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-full bg-jarvis-accent/20 flex items-center justify-center mx-auto mb-4 jarvis-glow">
            <div className="w-8 h-8 rounded-full bg-jarvis-accent jarvis-orb" />
          </div>
          <h1 className="text-2xl font-bold text-jarvis-text">Jarvis AI OS</h1>
          <p className="text-jarvis-text-muted mt-1 text-sm">
            Your intelligent assistant
          </p>
        </div>

        {/* Form */}
        <div className="bg-jarvis-surface border border-jarvis-border rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4">
            {isRegister ? 'Create Account' : 'Welcome Back'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="block text-sm text-jarvis-text-muted mb-1">
                  Display Name
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-3 py-2 bg-jarvis-bg border border-jarvis-border rounded-lg text-jarvis-text placeholder:text-jarvis-text-muted focus:border-jarvis-accent transition-colors"
                  placeholder="Tony Stark"
                  required={isRegister}
                  minLength={2}
                />
              </div>
            )}

            <div>
              <label className="block text-sm text-jarvis-text-muted mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 bg-jarvis-bg border border-jarvis-border rounded-lg text-jarvis-text placeholder:text-jarvis-text-muted focus:border-jarvis-accent transition-colors"
                placeholder="tony@starkindustries.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm text-jarvis-text-muted mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 bg-jarvis-bg border border-jarvis-border rounded-lg text-jarvis-text placeholder:text-jarvis-text-muted focus:border-jarvis-accent transition-colors"
                placeholder="••••••••"
                required
                minLength={8}
              />
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-jarvis-accent hover:bg-jarvis-accent/90 disabled:opacity-50 text-white font-medium rounded-lg transition-colors"
            >
              {loading ? 'Processing...' : isRegister ? 'Create Account' : 'Sign In'}
            </button>
          </form>

          <div className="mt-4 text-center">
            <button
              onClick={() => {
                setIsRegister(!isRegister);
                setError('');
              }}
              className="text-sm text-jarvis-text-muted hover:text-jarvis-accent transition-colors"
            >
              {isRegister
                ? 'Already have an account? Sign in'
                : "Don't have an account? Register"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
