import { useState, type FormEventHandler } from 'react'

type InvestorType = 'individual' | 'fund'

const SECTORS = [
  'FinTech',
  'HealthTech',
  'EdTech',
  'AI/ML',
  'E-commerce',
  'Cybersecurity',
  'SaaS',
  'Marketplace',
]

type UiState = 'idle' | 'submitting' | 'success' | 'error'

function isBlank(value: string) {
  return value.trim().length === 0
}

function isEmail(value: string) {
  return /^\S+@\S+\.\S+$/.test(value.trim())
}

function isNonNegativeNumber(value: string) {
  if (isBlank(value)) return false
  const n = Number(value)
  return Number.isFinite(n) && n >= 0
}

export default function RegisterInvestor() {
  const [uiState, setUiState] = useState<UiState>('idle')
  const [message, setMessage] = useState('')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [investorName, setInvestorName] = useState('')
  const [investorType, setInvestorType] = useState<InvestorType>('individual')

  const [sectors, setSectors] = useState<string[]>([])
  const [minimumInvestment, setMinimumInvestment] = useState('')

  const [contactName, setContactName] = useState('')
  const [contactPhone, setContactPhone] = useState('')

  const [acceptTerms, setAcceptTerms] = useState(false)

  const toggleSector = (s: string) => {
    setSectors((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]))
  }

  const onSubmit: FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    setMessage('')

    // required + format checks
    if (isBlank(email)) {
      setUiState('error')
      setMessage('Email is required.')
      return
    }
    if (!isEmail(email)) {
      setUiState('error')
      setMessage('Enter a valid email.')
      return
    }

    if (isBlank(password)) {
      setUiState('error')
      setMessage('Password is required.')
      return
    }
    if (password.length < 8) {
      setUiState('error')
      setMessage('Password must be at least 8 characters.')
      return
    }

    if (isBlank(confirmPassword)) {
      setUiState('error')
      setMessage('Confirm your password.')
      return
    }
    if (password !== confirmPassword) {
      setUiState('error')
      setMessage('Passwords do not match.')
      return
    }

    if (isBlank(investorName)) {
      setUiState('error')
      setMessage('Investor name is required.')
      return
    }

    if (sectors.length === 0) {
      setUiState('error')
      setMessage('Select at least one sector of interest.')
      return
    }

    if (!isNonNegativeNumber(minimumInvestment)) {
      setUiState('error')
      setMessage('Minimum investment must be a number (0 or greater).')
      return
    }

    if (isBlank(contactName)) {
      setUiState('error')
      setMessage('Contact name is required.')
      return
    }

    if (isBlank(contactPhone)) {
      setUiState('error')
      setMessage('Contact phone is required.')
      return
    }

    if (!acceptTerms) {
      setUiState('error')
      setMessage('You must accept Terms & Conditions.')
      return
    }

    setUiState('submitting')

    try {
      const payload = {
        email: email.trim(),
        password,
        role: 'investor',
        company_name: investorName.trim(),
        contact_phone: contactPhone.trim(),
      }

      const resp = await fetch('/api/auth/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await resp.json().catch(() => null)

      if (!resp.ok) {
        const key = data && typeof data === 'object' ? Object.keys(data)[0] : ''
        const val = key ? (data as any)[key] : null
        const text = Array.isArray(val) ? val.join(', ') : val ? String(val) : 'Request failed.'
        setUiState('error')
        setMessage(text)
        return
      }

      setUiState('success')
      setMessage(data?.detail || 'Check your email to verify your account.')
    } catch {
      setUiState('error')
      setMessage('Network error. Please try again.')
    }
  }

  const disabled = uiState === 'submitting'

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 24 }}>
      <h1>Investor Registration</h1>

      {message && <p>{message}</p>}

      <form onSubmit={onSubmit}>
        <h3>Account</h3>

        <label>
          Email
          <input
            type="email"
            value={email}
            disabled={disabled}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            disabled={disabled}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        <label>
          Confirm password
          <input
            type="password"
            value={confirmPassword}
            disabled={disabled}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
        </label>

        <h3>Investor</h3>

        <label>
          Investor name
          <input
            type="text"
            value={investorName}
            disabled={disabled}
            onChange={(e) => setInvestorName(e.target.value)}
            required
          />
        </label>

        <label>
          Investor type
          <select
            value={investorType}
            disabled={disabled}
            onChange={(e) => setInvestorType(e.target.value as InvestorType)}
          >
            <option value="individual">Individual</option>
            <option value="fund">Fund</option>
          </select>
        </label>

        <div>
          <div>Sectors of interest</div>
          {SECTORS.map((s) => (
            <label key={s} style={{ display: 'inline-flex', gap: 6, marginRight: 12 }}>
              <input
                type="checkbox"
                checked={sectors.includes(s)}
                disabled={disabled}
                onChange={() => toggleSector(s)}
              />
              {s}
            </label>
          ))}
        </div>

        <label>
          Minimum investment
          <input
            type="number"
            min={0}
            value={minimumInvestment}
            disabled={disabled}
            onChange={(e) => setMinimumInvestment(e.target.value)}
            required
          />
        </label>

        <h3>Contacts</h3>

        <label>
          Contact name
          <input
            type="text"
            value={contactName}
            disabled={disabled}
            onChange={(e) => setContactName(e.target.value)}
            required
          />
        </label>

        <label>
          Contact phone
          <input
            type="tel"
            value={contactPhone}
            disabled={disabled}
            onChange={(e) => setContactPhone(e.target.value)}
            required
          />
        </label>

        <label style={{ display: 'block', marginTop: 12 }}>
          <input
            type="checkbox"
            checked={acceptTerms}
            disabled={disabled}
            onChange={(e) => setAcceptTerms(e.target.checked)}
          />{' '}
          I accept Terms & Conditions
        </label>

        <button type="submit" disabled={disabled} style={{ marginTop: 16 }}>
          {disabled ? 'Submitting…' : 'Register'}
        </button>
      </form>
    </div>
  )
}
