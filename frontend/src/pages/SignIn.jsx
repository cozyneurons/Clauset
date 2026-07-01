import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

/* ── tiny SVG icons ── */
const IconMail = () => (
  <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
    <rect x="1.5" y="3.5" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="1.4"/>
    <path d="M1.5 6l7 4.5L15.5 6" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
  </svg>
)
const IconLock = () => (
  <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
    <rect x="3" y="8" width="11" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
    <path d="M5.5 8V6a3 3 0 016 0v2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
)
const IconEye = () => (
  <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
    <ellipse cx="8.5" cy="8.5" rx="6.5" ry="4" stroke="currentColor" strokeWidth="1.4"/>
    <circle cx="8.5" cy="8.5" r="1.8" stroke="currentColor" strokeWidth="1.4"/>
  </svg>
)
const IconEyeOff = () => (
  <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
    <path d="M2 2l13 13M6.5 6.5A2 2 0 0110.5 10M3.5 5C2 6.3 1 7.5 1 8.5S5 13 8.5 13c1.2 0 2.3-.3 3.3-.8M5.5 3.5C6.4 3.2 7.4 3 8.5 3c3.5 0 7 4 7 5.5 0 .8-.5 1.8-1.4 2.8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
)
const IconInfo = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2"/>
    <path d="M7 6v4M7 4.5v.3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
  </svg>
)
const IconAlert = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
    <circle cx="7.5" cy="7.5" r="6.5" stroke="currentColor" strokeWidth="1.3"/>
    <path d="M7.5 5v3.5M7.5 10v.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
)
const IconDoc = () => (
  <svg width="26" height="26" viewBox="0 0 26 26" fill="none">
    <path d="M4 5C4 3.895 4.895 3 6 3h8l8 8v10c0 1.105-.895 2-2 2H6c-1.105 0-2-.895-2-2V5z" fill="url(#dg)"/>
    <path d="M14 3l8 8h-5a2 2 0 01-2-2V3z" fill="rgba(255,255,255,.2)"/>
    <path d="M8 13h10M8 17h7" stroke="white" strokeWidth="1.4" strokeLinecap="round"/>
    <defs>
      <linearGradient id="dg" x1="4" y1="3" x2="22" y2="23" gradientUnits="userSpaceOnUse">
        <stop stopColor="#6366f1"/><stop offset="1" stopColor="#8b5cf6"/>
      </linearGradient>
    </defs>
  </svg>
)

export default function SignIn() {
  const { signIn } = useAuth()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await signIn(email.trim(), password)
    } catch (err) {
      setError(err.message || 'Sign in failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-wrapper">
      {/* animated blobs */}
      <div className="auth-bg">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
        <div className="blob blob-3" />
      </div>

      <div className="auth-card">
        {/* logo */}
        <div className="auth-logo">
          <div className="logo-icon">
            <IconDoc />
          </div>
          <span className="logo-text">Clauset</span>
        </div>

        <div className="auth-heading">
          <h1>Welcome back</h1>
          <p>Sign in to analyze your Railway GCC contracts</p>
        </div>

        {/* error */}
        {error && (
          <div className="auth-alert">
            <IconAlert />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          {/* email */}
          <div className="form-group">
            <label className="form-label" htmlFor="email">Email address</label>
            <div className="input-wrap">
              <span className="input-icon"><IconMail /></span>
              <input
                id="email"
                type="email"
                className={`form-input${error ? ' error' : ''}`}
                placeholder="you@example.com"
                autoComplete="email"
                value={email}
                onChange={e => { setEmail(e.target.value); setError('') }}
                required
              />
            </div>
          </div>

          {/* password */}
          <div className="form-group">
            <label className="form-label" htmlFor="password">
              Password
              <a href="#" onClick={e => e.preventDefault()}>Forgot password?</a>
            </label>
            <div className="input-wrap">
              <span className="input-icon"><IconLock /></span>
              <input
                id="password"
                type={showPw ? 'text' : 'password'}
                className={`form-input${error ? ' error' : ''}`}
                placeholder="••••••••"
                autoComplete="current-password"
                value={password}
                onChange={e => { setPassword(e.target.value); setError('') }}
                required
              />
              <button
                type="button"
                className="pw-toggle"
                onClick={() => setShowPw(v => !v)}
                aria-label={showPw ? 'Hide password' : 'Show password'}
              >
                {showPw ? <IconEyeOff /> : <IconEye />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
            id="sign-in-submit"
          >
            {loading ? <span className="spinner" /> : null}
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="demo-hint">
          <IconInfo />
          Demo: use any email &amp; password to sign in
        </div>
      </div>
    </div>
  )
}
