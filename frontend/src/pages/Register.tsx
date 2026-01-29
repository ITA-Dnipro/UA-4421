import { Link } from 'react-router-dom'

export default function Register() {
  return (
    <div style={{ maxWidth: 560, width: '100%', margin: '0 auto', textAlign: 'left' }}>
      <h1 style={{ fontSize: 28, marginBottom: 16 }}>Registration</h1>

      <div style={{ display: 'grid', gap: 12 }}>
        <Link to="/register/startup" style={{ textDecoration: 'none' }}>
          <button type="button" style={{ width: '100%' }}>
            I'm a startup
          </button>
        </Link>

        <button type="button" disabled style={{ width: '100%' }}>
          I'm an investor
        </button>
      </div>
    </div>
  )
}