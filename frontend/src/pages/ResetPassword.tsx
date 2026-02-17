import { Link } from 'react-router-dom'

export default function ResetPassword() {
  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ marginTop: 0 }}>Reset password</h1>
      <p>This page is a placeholder for the password reset flow.</p>
      <Link to="/login">Back to login</Link>
    </div>
  )
}
