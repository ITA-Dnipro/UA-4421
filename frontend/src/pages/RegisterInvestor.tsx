import { useMemo, useState, type FormEventHandler } from 'react'

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

type Field =
  | 'email'
  | 'password'
  | 'confirmPassword'
  | 'investorName'
  | 'sectors'
  | 'minimumInvestment'
  | 'contactName'
  | 'contactPhone'
  | 'acceptTerms'

type Errors = Partial<Record<Field, string>>
type Touched = Partial<Record<Field, boolean>>

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

function validate(values: {
  email: string
  password: string
  confirmPassword: string
  investorName: string
  sectors: string[]
  minimumInvestment: string
  contactName: string
  contactPhone: string
  acceptTerms: boolean
}): Errors {
  const errors: Errors = {}

  if (isBlank(values.email)) errors.email = 'Email is required.'
  else if (!isEmail(values.email)) errors.email = 'Enter a valid email.'

  if (isBlank(values.password)) errors.password = 'Password is required.'
  else if (values.password.length < 8) errors.password = 'Password must be at least 8 characters.'

  if (isBlank(values.confirmPassword)) errors.confirmPassword = 'Confirm your password.'
  else if (values.password !== values.confirmPassword) errors.confirmPassword = 'Passwords do not match.'

  if (isBlank(values.investorName)) errors.investorName = 'Investor name is required.'

  if (values.sectors.length === 0) errors.sectors = 'Select at least one sector of interest.'

  if (!isNonNegativeNumber(values.minimumInvestment)) {
    errors.minimumInvestment = 'Minimum investment must be a number (0 or greater).'
  }

  if (isBlank(values.contactName)) errors.contactName = 'Contact name is required.'
  if (isBlank(values.contactPhone)) errors.contactPhone = 'Contact phone is required.'

  if (!values.acceptTerms) errors.acceptTerms = 'You must accept Terms & Conditions.'

  return errors
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

  const [touched, setTouched] = useState<Touched>({})

  const values = useMemo(
    () => ({
      email,
      password,
      confirmPassword,
      investorName,
      sectors,
      minimumInvestment,
      contactName,
      contactPhone,
      acceptTerms,
    }),
    [email, password, confirmPassword, investorName, sectors, minimumInvestment, contactName, contactPhone, acceptTerms]
  )

  const errors = useMemo(() => validate(values), [values])
  const isFormValid = Object.keys(errors).length === 0

  const disabled = uiState === 'submitting' || uiState === 'success'

  const markTouched = (field: Field) => {
    setTouched((prev) => (prev[field] ? prev : { ...prev, [field]: true }))
  }

  const markAllTouched = () => {
    setTouched({
      email: true,
      password: true,
      confirmPassword: true,
      investorName: true,
      sectors: true,
      minimumInvestment: true,
      contactName: true,
      contactPhone: true,
      acceptTerms: true,
    })
  }

  const showError = (field: Field) => Boolean(touched[field] && errors[field])
  const fieldError = (field: Field) => (showError(field) ? errors[field] : '')

  const inputStyle = (field: Field): React.CSSProperties => ({
    display: 'block',
    width: '100%',
    padding: '10px 12px',
    marginTop: 6,
    borderRadius: 8,
    border: showError(field) ? '1px solid #d33' : '1px solid #ccc',
    outline: 'none',
  })

  const errorTextStyle: React.CSSProperties = {
    marginTop: 6,
    color: '#d33',
    fontSize: 13,
  }

  const toggleSector = (s: string) => {
    markTouched('sectors')
    setSectors((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]))
  }

  const onSubmit: FormEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    setMessage('')

    markAllTouched()

    if (!isFormValid) {
      setUiState('error')
      setMessage('Please fix the highlighted fields.')
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

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 24 }}>
      <h1>Investor Registration</h1>

      {message && (
        <p style={{ marginTop: 12, padding: 10, background: uiState === 'success' ? '#e7ffe7' : '#fff3cd' }}>
          {message}
        </p>
      )}

      <form onSubmit={onSubmit} style={{ marginTop: 18 }}>
        <h3>Account</h3>

        <label style={{ display: 'block', marginTop: 12 }}>
          Email
          <input
            type="email"
            value={email}
            disabled={disabled}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={() => markTouched('email')}
            aria-invalid={showError('email')}
            style={inputStyle('email')}
            required
          />
          {fieldError('email') && <div style={errorTextStyle}>{fieldError('email')}</div>}
        </label>

        <label style={{ display: 'block', marginTop: 12 }}>
          Password
          <input
            type="password"
            value={password}
            disabled={disabled}
            onChange={(e) => setPassword(e.target.value)}
            onBlur={() => markTouched('password')}
            aria-invalid={showError('password')}
            style={inputStyle('password')}
            required
          />
          {fieldError('password') && <div style={errorTextStyle}>{fieldError('password')}</div>}
        </label>

        <label style={{ display: 'block', marginTop: 12 }}>
          Confirm password
          <input
            type="password"
            value={confirmPassword}
            disabled={disabled}
            onChange={(e) => setConfirmPassword(e.target.value)}
            onBlur={() => markTouched('confirmPassword')}
            aria-invalid={showError('confirmPassword')}
            style={inputStyle('confirmPassword')}
            required
          />
          {fieldError('confirmPassword') && <div style={errorTextStyle}>{fieldError('confirmPassword')}</div>}
        </label>

        <h3 style={{ marginTop: 22 }}>Investor</h3>

        <label style={{ display: 'block', marginTop: 12 }}>
          Investor name
          <input
            type="text"
            value={investorName}
            disabled={disabled}
            onChange={(e) => setInvestorName(e.target.value)}
            onBlur={() => markTouched('investorName')}
            aria-invalid={showError('investorName')}
            style={inputStyle('investorName')}
            required
          />
          {fieldError('investorName') && <div style={errorTextStyle}>{fieldError('investorName')}</div>}
        </label>

        <label style={{ display: 'block', marginTop: 12 }}>
          Investor type
          <select
            value={investorType}
            disabled={disabled}
            onChange={(e) => setInvestorType(e.target.value as InvestorType)}
            style={{ ...inputStyle('investorName'), marginTop: 6 }}
          >
            <option value="individual">Individual</option>
            <option value="fund">Fund</option>
          </select>
        </label>

        <div style={{ marginTop: 14 }}>
          <div style={{ marginBottom: 8 }}>Sectors of interest</div>
          <div
            style={{
              padding: 12,
              borderRadius: 8,
              border: showError('sectors') ? '1px solid #d33' : '1px solid #ccc',
            }}
          >
            {SECTORS.map((s) => (
              <label key={s} style={{ display: 'inline-flex', gap: 6, marginRight: 14, marginBottom: 8 }}>
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
          {fieldError('sectors') && <div style={errorTextStyle}>{fieldError('sectors')}</div>}
        </div>

        <label style={{ display: 'block', marginTop: 12 }}>
          Minimum investment
          <input
            type="number"
            min={0}
            value={minimumInvestment}
            disabled={disabled}
            onChange={(e) => setMinimumInvestment(e.target.value)}
            onBlur={() => markTouched('minimumInvestment')}
            aria-invalid={showError('minimumInvestment')}
            style={inputStyle('minimumInvestment')}
            required
          />
          {fieldError('minimumInvestment') && <div style={errorTextStyle}>{fieldError('minimumInvestment')}</div>}
        </label>

        <h3 style={{ marginTop: 22 }}>Contacts</h3>

        <label style={{ display: 'block', marginTop: 12 }}>
          Contact name
          <input
            type="text"
            value={contactName}
            disabled={disabled}
            onChange={(e) => setContactName(e.target.value)}
            onBlur={() => markTouched('contactName')}
            aria-invalid={showError('contactName')}
            style={inputStyle('contactName')}
            required
          />
          {fieldError('contactName') && <div style={errorTextStyle}>{fieldError('contactName')}</div>}
        </label>

        <label style={{ display: 'block', marginTop: 12 }}>
          Contact phone
          <input
            type="tel"
            value={contactPhone}
            disabled={disabled}
            onChange={(e) => setContactPhone(e.target.value)}
            onBlur={() => markTouched('contactPhone')}
            aria-invalid={showError('contactPhone')}
            style={inputStyle('contactPhone')}
            required
          />
          {fieldError('contactPhone') && <div style={errorTextStyle}>{fieldError('contactPhone')}</div>}
        </label>

        <label style={{ display: 'block', marginTop: 16 }}>
          <input
            type="checkbox"
            checked={acceptTerms}
            disabled={disabled}
            onChange={(e) => {
              setAcceptTerms(e.target.checked)
              markTouched('acceptTerms')
            }}
          />{' '}
          I accept Terms & Conditions
        </label>
        {fieldError('acceptTerms') && <div style={errorTextStyle}>{fieldError('acceptTerms')}</div>}

        <button
          type="submit"
          disabled={disabled || !isFormValid}
          style={{
            marginTop: 18,
            padding: '10px 14px',
            borderRadius: 10,
            border: '1px solid #000',
            opacity: disabled || !isFormValid ? 0.6 : 1,
            cursor: disabled || !isFormValid ? 'not-allowed' : 'pointer',
          }}
        >
          {uiState === 'submitting' ? 'Submitting…' : 'Register'}
        </button>
      </form>
    </div>
  )
}
