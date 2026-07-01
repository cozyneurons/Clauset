import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function Topbar() {
  const [status, setStatus] = useState('checking') // checking | online | offline

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(4000) })
        setStatus(res.ok ? 'online' : 'offline')
      } catch {
        setStatus('offline')
      }
    }
    check()
    const id = setInterval(check, 30_000)
    return () => clearInterval(id)
  }, [])

  const label = status === 'checking' ? 'Checking API…'
              : status === 'online'   ? 'API online'
              :                         'API offline'

  return (
    <header className="topbar">
      <div>
        <h2>Analyze Contract</h2>
        <p>Upload a Railway contract PDF for AI-powered GCC compliance analysis</p>
      </div>
      <div className="status-badge">
        <span className={`status-dot${status === 'online' ? ' online' : status === 'offline' ? ' offline' : ''}`} />
        {label}
      </div>
    </header>
  )
}
