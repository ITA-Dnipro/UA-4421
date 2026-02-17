import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import styles from './Login.module.css'

type Role = 'startup' | 'investor'
type FieldKey = 'email' | 'password'
type FieldErrors = Partial<Record<FieldKey, string>>
type FieldTouched = Partial<Record<FieldKey, boolean>>
type UiState = 'idle' | 'loading' | 'validation_errors' | 'credential_error' | 'locked'

function isBlank(value: string) {
  return value.trim().length === 0
}

function isEmail(value: string) {
  return /^\S+@\S+\.\S+$/.test(value.trim())
}

function validateAll(email: string, password: string): FieldErrors {
  const next: FieldErrors = {}

  if (isBlank(email)) next.email = 'Email is required.'
  else if (!isEmail(email)) next.email = 'Enter a valid email.'

  if (isBlank(password)) next.password = 'Password is required.'
  else if (password.length < 8) next.password = 'Password must be at least 8 characters.'

  return next
}

function toMessage(value: unknown): string | undefined {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    const parts = value.map((v) => (typeof v === 'string' ? v : '')).filter(Boolean)
    return parts.length ? parts.join(' ') : undefined
  }
  return undefined
}

export default function LoginPage() {
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Role>('startup')
  const [remember, setRemember] = useState(false)

  const [errors, setErrors] = useState<FieldErrors>({})
  const [touched, setTouched] = useState<FieldTouched>({})
  const [submitAttempted, setSubmitAttempted] = useState(false)

  const [uiState, setUiState] = useState<UiState>('idle')
  const [banner, setBanner] = useState<string>('')

  const isSubmitting = uiState === 'loading'

  function markTouched(key: FieldKey) {
    setTouched((prev) => ({ ...prev, [key]: true }))
  }

  function getVisibleError(key: FieldKey) {
    const message = errors[key]
    if (!message) return undefined
    if (submitAttempted || touched[key]) return message
    return undefined
  }

  function showSuccess(key: FieldKey) {
    const value = key === 'email' ? email : password
    const visibleError = getVisibleError(key)
    return (submitAttempted || touched[key]) && !visibleError && !isBlank(value)
  }

  function controlClass(key: FieldKey) {
    if (getVisibleError(key)) return `${styles.input} ${styles.inputError}`
    if (showSuccess(key)) return `${styles.input} ${styles.inputSuccess}`
    return styles.input
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitAttempted(true)
    setBanner('')

    const nextErrors = validateAll(email, password)
    setErrors(nextErrors)

    if (Object.keys(nextErrors).length > 0) {
      setUiState('validation_errors')
      return
    }

    setUiState('loading')

    try {
      const payload = {
        email: email.trim(),
        password,
        remember,
      }

      const res = await fetch('/api/auth/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await res.json().catch(() => undefined)

      if (res.ok) {
        const obj = (data && typeof data === 'object' ? (data as any) : undefined) as
          | { access?: string; refresh?: string; user?: { role?: string } }
          | undefined

        const access = obj?.access
        const refresh = obj?.refresh

        if (remember) {
          if (access) localStorage.setItem('token', access)
          if (refresh) localStorage.setItem('refreshToken', refresh)
          sessionStorage.removeItem('token')
          sessionStorage.removeItem('refreshToken')
        } else {
          if (access) sessionStorage.setItem('token', access)
          if (refresh) sessionStorage.setItem('refreshToken', refresh)
          localStorage.removeItem('token')
          localStorage.removeItem('refreshToken')
        }

        const returnedRole = obj?.user?.role
        if (returnedRole === 'investor') navigate('/dashboard', { replace: true })
        else navigate('/', { replace: true })

        return
      }

      if (res.status === 401) {
        const detail = toMessage(data && typeof data === 'object' ? (data as any).detail : undefined)
        setBanner(detail || 'Incorrect email or password.')
        setUiState('credential_error')
        return
      }

      if (res.status === 429) {
        const detail = toMessage(data && typeof data === 'object' ? (data as any).detail : undefined)
        setBanner(detail || 'Too many login attempts. Please try again later.')
        setUiState('locked')
        return
      }

      setBanner('Login failed. Please try again.')
      setUiState('idle')
    } catch {
      setBanner('Network error. Please try again.')
      setUiState('idle')
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.card}>
          <h1 className={styles.title}>Login</h1>

          {banner && (
            <div
              aria-live="polite"
              className={uiState === 'credential_error' || uiState === 'locked' ? styles.bannerError : styles.banner}
            >
              {banner}
            </div>
          )}

          <form className={styles.form} onSubmit={onSubmit} noValidate aria-busy={isSubmitting}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="email">
                Email
              </label>
              <input
                id="email"
                className={controlClass('email')}
                type="email"
                value={email}
                disabled={isSubmitting}
                onChange={(e) => {
                  setEmail(e.target.value)
                  if (submitAttempted) setErrors(validateAll(e.target.value, password))
                }}
                onBlur={() => {
                  markTouched('email')
                  setErrors(validateAll(email, password))
                }}
                placeholder="you@example.com"
                required
              />
              {getVisibleError('email') && <div className={styles.errorText}>{getVisibleError('email')}</div>}
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="password">
                Password
              </label>

              <input
                id="password"
                className={controlClass('password')}
                type="password"
                value={password}
                disabled={isSubmitting}
                onChange={(e) => {
                  setPassword(e.target.value)
                  if (submitAttempted) setErrors(validateAll(email, e.target.value))
                }}
                onBlur={() => {
                  markTouched('password')
                  setErrors(validateAll(email, password))
                }}
                placeholder="At least 8 characters"
                required
              />

              <div className={styles.passwordMetaRow}>
                <div>
                  {getVisibleError('password') && (
                    <div className={styles.errorText}>{getVisibleError('password')}</div>
                  )}
                </div>

                <Link className={styles.link} to="/reset-password">
                  Forgot password?
                </Link>
              </div>
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="role">
                Role
              </label>
              <select
                id="role"
                className={styles.input}
                value={role}
                disabled={isSubmitting}
                onChange={(e) => setRole(e.target.value as Role)}
              >
                <option value="startup">Startup</option>
                <option value="investor">Investor</option>
              </select>
            </div>

            <div className={styles.helpRow}>
              <label className={styles.checkboxRow}>
                <input
                  type="checkbox"
                  checked={remember}
                  disabled={isSubmitting}
                  onChange={(e) => setRemember(e.target.checked)}
                />
                Remember me
              </label>

              <Link className={styles.link} to="/register">
                Create account
              </Link>
            </div>

            <button type="submit" className={styles.button} disabled={isSubmitting}>
              {isSubmitting && <span className={styles.spinner} aria-hidden="true" />}
              {isSubmitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          {(uiState === 'credential_error' || uiState === 'locked') && (
            <div className={styles.metaNote}>
              {uiState === 'locked'
                ? 'If you keep seeing this message, wait a bit and try again, or reset your password.'
                : 'Double-check your email/password and try again.'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
