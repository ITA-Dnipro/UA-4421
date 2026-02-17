import { Link } from 'react-router-dom'

export default function ResetPassword() {
  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ marginTop: 0 }}>Reset password</h1>
      <p>
        Oops! This page isn’t ready yet 🙈<br />
        We’re actively working on the password recovery flow. Thanks for your patience!
    </p>
      <Link to="/login">Back to login</Link>
    </div>
  )
}
