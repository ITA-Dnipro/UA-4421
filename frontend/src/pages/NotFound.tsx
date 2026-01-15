import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        gap: '20px',
      }}
    >
      <h1 style={{ fontSize: '3rem', margin: 0 }}>404</h1>
      <p style={{ fontSize: '1.2rem' }}>Сторінку не знайдено</p>

      <Link
        to="/"
        style={{
          padding: '10px 20px',
          background: '#4f46e5',
          color: 'white',
          borderRadius: '8px',
          textDecoration: 'none',
          fontWeight: 'bold',
        }}
      >
        Go Home
      </Link>
    </div>
  )
}
