import { BrowserRouter, Routes, Route } from 'react-router-dom'

import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'

import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import RegisterStartup from './pages/RegisterStartup'
import RegisterInvestor from './pages/RegisterInvestor'
import StartupView from './pages/StartupView'
import InvestorDashboard from './pages/InvestorDashboard'
import SavedPage from './pages/SavedPage'
import Inbox from './pages/Inbox'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />

      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/register/startup" element={<RegisterStartup />} />
        <Route path="/register/investor" element={<RegisterInvestor />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Home />
            </ProtectedRoute>
          }
        />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <InvestorDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/messages"
          element={
            <ProtectedRoute>
              <Inbox />
            </ProtectedRoute>
          }
        />

        <Route
          path="/saved"
          element={
            <ProtectedRoute>
              <SavedPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/startups/:id"
          element={
            <ProtectedRoute>
              <StartupView />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}
