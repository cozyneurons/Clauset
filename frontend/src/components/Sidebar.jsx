import { useAuth } from '../context/AuthContext'

const IconUpload  = () => <svg width="17" height="17" viewBox="0 0 17 17" fill="none"><path d="M8.5 12V4M5 7.5l3.5-3.5L12 7.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/><path d="M2.5 13.5h12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>
const IconDocs    = () => <svg width="17" height="17" viewBox="0 0 17 17" fill="none"><rect x="2" y="2" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="1.4"/><path d="M5 6h7M5 9h7M5 12h4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>
const IconHistory = () => <svg width="17" height="17" viewBox="0 0 17 17" fill="none"><circle cx="8.5" cy="8.5" r="6.5" stroke="currentColor" strokeWidth="1.4"/><path d="M8.5 5v3.8l2.5 1.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>
const IconOut     = () => <svg width="17" height="17" viewBox="0 0 17 17" fill="none"><path d="M6.5 3H4A1.5 1.5 0 002.5 4.5v8A1.5 1.5 0 004 14h2.5M11 11.5L14 8.5 11 5.5M14 8.5H6.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>

const NAV = [
  { id: 'upload',   label: 'Analyze Contract', icon: <IconUpload /> },
  { id: 'library',  label: 'GCC Library',      icon: <IconDocs /> },
  { id: 'history',  label: 'History',          icon: <IconHistory /> },
]

export default function Sidebar({ user, onSignOut }) {
  return (
    <aside className="sidebar">
      {/* logo */}
      <div className="sidebar-logo">
        <div className="logo-icon" style={{ width: 32, height: 32, borderRadius: 8 }}>
          <svg width="20" height="20" viewBox="0 0 26 26" fill="none">
            <path d="M3 4.5C3 3.395 3.895 2.5 5 2.5h8l8 8v10c0 1.105-.895 2-2 2H5c-1.105 0-2-.895-2-2v-16z" fill="url(#sg)"/>
            <path d="M13 2.5l8 8h-5a2 2 0 01-2-2v-6z" fill="rgba(255,255,255,.2)"/>
            <path d="M7 12h12M7 16h8" stroke="white" strokeWidth="1.4" strokeLinecap="round"/>
            <defs>
              <linearGradient id="sg" x1="3" y1="2.5" x2="21" y2="22.5" gradientUnits="userSpaceOnUse">
                <stop stopColor="#6366f1"/><stop offset="1" stopColor="#8b5cf6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span className="logo-text">Clauset</span>
      </div>

      {/* nav */}
      <nav className="sidebar-nav">
        {NAV.map(item => (
          <div key={item.id} className={`nav-item${item.id === 'upload' ? ' active' : ''}`}>
            {item.icon}
            {item.label}
          </div>
        ))}
      </nav>

      {/* footer */}
      <div className="sidebar-footer">
        <div className="user-avatar">{user?.avatar || 'U'}</div>
        <div className="user-info">
          <span className="user-name">{user?.name || 'User'}</span>
          <span className="user-role">Analyst</span>
        </div>
        <button className="sign-out-btn" onClick={onSignOut} title="Sign out">
          <IconOut />
        </button>
      </div>
    </aside>
  )
}
