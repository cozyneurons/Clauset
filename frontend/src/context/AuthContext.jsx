import { createContext, useContext, useState, useCallback } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('clauset_user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })

  const signIn = useCallback(async (email, password) => {
    // Simulate network latency (replace with real API call)
    await new Promise(r => setTimeout(r, 900))

    // Simple demo auth — accept any non-empty email + password
    if (!email || !password) {
      throw new Error('Please fill in all fields.')
    }

    const userData = {
      email,
      name: email.split('@')[0].replace(/[._-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      avatar: email[0].toUpperCase(),
    }

    localStorage.setItem('clauset_user', JSON.stringify(userData))
    setUser(userData)
    return userData
  }, [])

  const signOut = useCallback(() => {
    localStorage.removeItem('clauset_user')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
