import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Login from './Login'

type Deferred<T> = {
  promise: Promise<T>
  resolve: (value: T) => void
  reject: (reason?: unknown) => void
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function renderWithRoutes() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<div>Home</div>} />
        <Route path="/dashboard" element={<div>Dashboard</div>} />
        <Route path="/reset-password" element={<div>Reset page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  localStorage.clear()
  sessionStorage.clear()
})

describe('LoginPage', () => {
  it('blocks submit and shows client-side validation errors when invalid', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    renderWithRoutes()

    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(fetchMock).not.toHaveBeenCalled()
    expect(await screen.findByText('Email is required.')).toBeInTheDocument()
    expect(screen.getByText('Password is required.')).toBeInTheDocument()
  })

  it('validates email format and blocks submit', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    renderWithRoutes()

    await user.type(screen.getByLabelText('Email'), 'not-an-email')
    await user.type(screen.getByLabelText('Password'), 'password123')

    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(fetchMock).not.toHaveBeenCalled()
    expect(await screen.findByText('Enter a valid email.')).toBeInTheDocument()
  })

  it('validates password min length and blocks submit', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    renderWithRoutes()

    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), '1234567')

    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(fetchMock).not.toHaveBeenCalled()
    expect(await screen.findByText('Password must be at least 8 characters.')).toBeInTheDocument()
  })

  it('shows loading UI while submitting and stores token in sessionStorage when Remember me is off', async () => {
    const user = userEvent.setup()

    const d = deferred<{
      ok: boolean
      status: number
      json: () => Promise<unknown>
    }>()

    const fetchMock = vi.fn().mockImplementation(() => d.promise)
    vi.stubGlobal('fetch', fetchMock)

    renderWithRoutes()

    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')

    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(await screen.findByRole('button', { name: 'Signing in...' })).toBeInTheDocument()

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/auth/login/')
    expect((options as any).method).toBe('POST')
    expect((options as any).headers).toEqual({ 'Content-Type': 'application/json' })

    const body = JSON.parse((options as any).body)
    expect(body).toEqual({ email: 'test@example.com', password: 'password123', remember: false })

    d.resolve({
      ok: true,
      status: 200,
      json: async () => ({ access: 'ACCESS', refresh: 'REFRESH', user: { role: 'startup' } }),
    })

    expect(await screen.findByText('Home')).toBeInTheDocument()

    expect(sessionStorage.getItem('token')).toBe('ACCESS')
    expect(sessionStorage.getItem('refreshToken')).toBe('REFRESH')
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('stores token in localStorage when Remember me is on and redirects investor to dashboard', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access: 'ACCESS2', refresh: 'REFRESH2', user: { role: 'investor' } }),
    })
    vi.stubGlobal('fetch', fetchMock)

    renderWithRoutes()

    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')

    await user.click(screen.getByLabelText('Remember me'))
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Dashboard')).toBeInTheDocument()

    expect(localStorage.getItem('token')).toBe('ACCESS2')
    expect(localStorage.getItem('refreshToken')).toBe('REFRESH2')
    expect(sessionStorage.getItem('token')).toBeNull()
  })

  it('shows credential error message on 401', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid credentials.' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    renderWithRoutes()

    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')

    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Invalid credentials.')).toBeInTheDocument()
  })

  it('shows lock message on 429', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      json: async () => ({ detail: 'Too many login attempts.' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    renderWithRoutes()

    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')

    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Too many login attempts.')).toBeInTheDocument()
  })

  it('navigates to reset page via Forgot password link', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    renderWithRoutes()

    await user.click(screen.getByRole('link', { name: 'Forgot password?' }))

    expect(await screen.findByText('Reset page')).toBeInTheDocument()
  })

  it('treats 200 OK without access token as a login failure (no redirect, no tokens stored)', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ refresh: 'REFRESH' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    renderWithRoutes()

    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(
      await screen.findByText('Login failed: server did not return an access token. Please try again.')
    ).toBeInTheDocument()

    expect(localStorage.getItem('token')).toBeNull()
    expect(sessionStorage.getItem('token')).toBeNull()
  })
})
