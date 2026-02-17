import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'

function hasToken() {
  return Boolean(localStorage.getItem('token') || sessionStorage.getItem('token'))
}

export default function Navbar() {
  const [isAuthenticated, setIsAuthenticated] = useState(hasToken)

  useEffect(() => {
    const update = () => setIsAuthenticated(hasToken())

    window.addEventListener('auth:changed', update)

    window.addEventListener('storage', update)

    return () => {
      window.removeEventListener('auth:changed', update)
      window.removeEventListener('storage', update)
    }
  }, [])

  function handleLogout() {
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    sessionStorage.removeItem('token')
    sessionStorage.removeItem('refreshToken')

    window.dispatchEvent(new Event('auth:changed'))
    window.location.href = '/login'
  }

  return (
    <nav
      style={{
        display: 'flex',
        gap: '20px',
        padding: '15px',
        background: '#f3f4f6',
        borderBottom: '1px solid #ddd',
      }}
    >
      {isAuthenticated ? (
        <>
          <Link to="/">Home</Link>
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/messages">Messages</Link>
          <Link to="/startups/1">Startup</Link>

          <button
            onClick={handleLogout}
            style={{
              marginLeft: 'auto',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            Logout
          </button>
        </>
      ) : (
        <>
          <Link to="/login">Login</Link>
          <Link to="/register">Register</Link>
        </>
      )}
    </nav>
  )
}
