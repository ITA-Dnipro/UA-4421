import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'

type Props = {
  children: ReactNode
}

export default function ProtectedRoute({ children }: Props) {
  const isAuthenticated = !!localStorage.getItem('token')

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}
