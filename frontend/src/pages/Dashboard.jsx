import { useAuth } from '../context/AuthContext'
import Sidebar from '../components/Sidebar'
import Topbar from '../components/Topbar'
import UploadPanel from '../components/UploadPanel'

export default function Dashboard() {
  const { user, signOut } = useAuth()

  return (
    <div className="app-layout">
      <Sidebar user={user} onSignOut={signOut} />
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <Topbar />
        <div className="content-area">
          <UploadPanel />
        </div>
      </div>
    </div>
  )
}
