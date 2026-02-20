import { type FormEvent, useState } from 'react'
import styles from './RegisterInvestor.module.css'
import { isEmail } from '../utils/validation'


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

type FieldKey =
  | 'email'
  | 'password'
  | 'confirmPassword'
  | 'investorName'
  | 'sectors'
  | 'minimumInvestment'
  | 'contactName'
  | 'contactPhone'
  | 'termsAccepted'

type FieldErrors = Partial<Record<FieldKey, string>>
type FieldTouched = Partial<Record<FieldKey, boolean>>

type Values = {
  email: string
  password: string
  confirmPassword: string
  investorName: string
  investorType: InvestorType
  sectors: string[]
  minimumInvestment: string
  contactName: string
  contactPhone: string
  termsAccepted: boolean
}

type UiState = 'idle' | 'submitting' | 'success'

function isBlank(value: string) {
  return value.trim().length === 0
}

function isNonNegativeNumber(value: string) {
  if (isBlank(value)) return false
  const n = Number(value)
  return Number.isFinite(n) && n >= 0
}

function validateAll(values: Values): FieldErrors {
  const next: FieldErrors = {}

  if (isBlank(values.email)) next.email = 'Email is required.'
  else if (!isEmail(values.email)) next.email = 'Enter a valid email.'

  if (isBlank(values.password)) next.password = 'Password is required.'
  else if (values.password.length < 8) next.password = 'Password must be at least 8 characters.'

  if (isBlank(values.confirmPassword)) next.confirmPassword = 'Confirm your password.'
  else if (values.confirmPassword !== values.password) next.confirmPassword = 'Passwords do not match.'

  if (isBlank(values.investorName)) next.investorName = 'Investor name is required.'

  if (values.sectors.length === 0) next.sectors = 'Select at least one sector of interest.'

  if (!isNonNegativeNumber(values.minimumInvestment)) {
    next.minimumInvestment = 'Minimum investment must be a number (0 or greater).'
  }

  if (isBlank(values.contactName)) next.contactName = 'Contact name is required.'
  if (isBlank(values.contactPhone)) next.contactPhone = 'Contact phone is required.'

  if (!values.termsAccepted) next.termsAccepted = 'You must accept Terms & Conditions.'

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

function mapServerErrorsToFields(payload: unknown): { fieldErrors: FieldErrors; general?: string } {
  const fieldErrors: FieldErrors = {}
  let general: string | undefined

  if (!payload || typeof payload !== 'object') return { fieldErrors }

  const obj = payload as Record<string, unknown>

  if (typeof obj.detail === 'string') general = obj.detail
  if (typeof obj.non_field_errors === 'string') general = obj.non_field_errors
  if (Array.isArray(obj.non_field_errors)) general = toMessage(obj.non_field_errors)

  const emailMsg = toMessage(obj.email)
  if (emailMsg) fieldErrors.email = emailMsg

  const passwordMsg = toMessage(obj.password)
  if (passwordMsg) fieldErrors.password = passwordMsg

  const companyNameMsg = toMessage(obj.company_name)
  if (companyNameMsg) fieldErrors.investorName = companyNameMsg

  const contactPhoneMsg = toMessage(obj.contact_phone)
  if (contactPhoneMsg) fieldErrors.contactPhone = contactPhoneMsg

  return { fieldErrors, general }
}

export default function RegisterInvestor() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const [investorName, setInvestorName] = useState('')
  const [investorType, setInvestorType] = useState<InvestorType>('individual')

  const [sectors, setSectors] = useState<string[]>([])
  const [minimumInvestment, setMinimumInvestment] = useState('')

  const [contactName, setContactName] = useState('')
  const [contactPhone, setContactPhone] = useState('')

  const [termsAccepted, setTermsAccepted] = useState(false)

  const [errors, setErrors] = useState<FieldErrors>({})
  const [touched, setTouched] = useState<FieldTouched>({})
  const [submitAttempted, setSubmitAttempted] = useState(false)

  const [uiState, setUiState] = useState<UiState>('idle')
  const [banner, setBanner] = useState<string>('')

  function getValues(): Values {
    return {
      email,
      password,
      confirmPassword,
      investorName,
      investorType,
      sectors,
      minimumInvestment,
      contactName,
      contactPhone,
      termsAccepted,
    }
  }

  function markTouched(key: FieldKey) {
    setTouched((prev) => ({ ...prev, [key]: true }))
  }

  function getVisibleError(key: FieldKey) {
    const message = errors[key]
    if (!message) return undefined
    if (submitAttempted || touched[key]) return message
    return undefined
  }

  function controlClass(key: FieldKey) {
    return getVisibleError(key) ? `${styles.input} ${styles.inputError}` : styles.input
  }

  function revalidate() {
    setErrors(validateAll(getValues()))
  }

  function toggleSector(s: string) {
    markTouched('sectors')
    setSectors((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitAttempted(true)
    setBanner('')

    const combined = validateAll(getValues())
    setErrors(combined)
    if (Object.keys(combined).length > 0) return

    setUiState('submitting')

    try {
      const payload = {
        email: email.trim(),
        password,
        role: 'investor',
        company_name: investorName.trim(),
        contact_phone: contactPhone.trim(),
      }

      const res = await fetch('/api/auth/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await res.json().catch(() => undefined)

      if (res.ok) {
        setUiState('success')
        setBanner(data && typeof data === 'object' && (data as any).detail ? String((data as any).detail) : 'Check your email to verify your account.')
        return
      }

      const parsed = mapServerErrorsToFields(data)
      const nextErrors: FieldErrors = { ...combined, ...parsed.fieldErrors }
      setErrors(nextErrors)

      if (parsed.general) setBanner(parsed.general)
      else if (Object.keys(parsed.fieldErrors).length > 0) setBanner('Please fix the highlighted fields and try again.')
      else setBanner('Registration failed. Please try again.')

      setUiState('idle')
    } catch {
      setBanner('Network error. Please try again.')
      setUiState('idle')
    }
  }

  const isSubmitting = uiState === 'submitting'

  if (uiState === 'success') {
    return (
      <div className={styles.page}>
        <div className={styles.container}>
          <div className={styles.card}>
            <h1 className={styles.title}>Investor registration</h1>

            <div aria-live="polite" className={styles.bannerSuccess}>
              {banner}
            </div>

            <div className={styles.successHint}>
              If you don&apos;t see the email, check your spam folder or try again later.
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.card}>
          <h1 className={styles.title}>Investor registration</h1>

          {banner && (
            <div aria-live="polite" className={styles.banner}>
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
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => {
                  markTouched('email')
                  revalidate()
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
                onChange={(e) => setPassword(e.target.value)}
                onBlur={() => {
                  markTouched('password')
                  revalidate()
                }}
                placeholder="At least 8 characters"
                required
              />
              {getVisibleError('password') && <div className={styles.errorText}>{getVisibleError('password')}</div>}
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="confirmPassword">
                Confirm password
              </label>
              <input
                id="confirmPassword"
                className={controlClass('confirmPassword')}
                type="password"
                value={confirmPassword}
                disabled={isSubmitting}
                onChange={(e) => setConfirmPassword(e.target.value)}
                onBlur={() => {
                  markTouched('confirmPassword')
                  revalidate()
                }}
                required
              />
              {getVisibleError('confirmPassword') && (
                <div className={styles.errorText}>{getVisibleError('confirmPassword')}</div>
              )}
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="investorName">
                Investor name
              </label>
              <input
                id="investorName"
                className={controlClass('investorName')}
                type="text"
                value={investorName}
                disabled={isSubmitting}
                onChange={(e) => setInvestorName(e.target.value)}
                onBlur={() => {
                  markTouched('investorName')
                  revalidate()
                }}
                placeholder="Example Investor"
                required
              />
              {getVisibleError('investorName') && (
                <div className={styles.errorText}>{getVisibleError('investorName')}</div>
              )}
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="investorType">
                Investor type
              </label>
              <select
                id="investorType"
                className={styles.input}
                value={investorType}
                disabled={isSubmitting}
                onChange={(e) => setInvestorType(e.target.value as InvestorType)}
              >
                <option value="individual">Individual</option>
                <option value="fund">Fund</option>
              </select>
            </div>

            <div className={styles.field}>
              <div className={styles.label}>Sectors of interest</div>

              <div className={getVisibleError('sectors') ? `${styles.box} ${styles.inputError}` : styles.box}>
                <div className={styles.sectorsGrid}>
                  {SECTORS.map((s) => (
                    <label key={s} className={styles.sectorItem}>
                      <input
                        type="checkbox"
                        checked={sectors.includes(s)}
                        disabled={isSubmitting}
                        onChange={() => {
                          toggleSector(s)
                          revalidate()
                        }}
                      />
                      <span>{s}</span>
                    </label>
                  ))}
                </div>
              </div>

              {getVisibleError('sectors') && <div className={styles.errorText}>{getVisibleError('sectors')}</div>}
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="minimumInvestment">
                Minimum investment
              </label>
              <input
                id="minimumInvestment"
                className={controlClass('minimumInvestment')}
                type="number"
                min={0}
                value={minimumInvestment}
                disabled={isSubmitting}
                onChange={(e) => setMinimumInvestment(e.target.value)}
                onBlur={() => {
                  markTouched('minimumInvestment')
                  revalidate()
                }}
                required
              />
              {getVisibleError('minimumInvestment') && (
                <div className={styles.errorText}>{getVisibleError('minimumInvestment')}</div>
              )}
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="contactName">
                Contact name
              </label>
              <input
                id="contactName"
                className={controlClass('contactName')}
                type="text"
                value={contactName}
                disabled={isSubmitting}
                onChange={(e) => setContactName(e.target.value)}
                onBlur={() => {
                  markTouched('contactName')
                  revalidate()
                }}
                required
              />
              {getVisibleError('contactName') && <div className={styles.errorText}>{getVisibleError('contactName')}</div>}
            </div>

            <div className={styles.field}>
              <label className={styles.label} htmlFor="contactPhone">
                Contact phone
              </label>
              <input
                id="contactPhone"
                className={controlClass('contactPhone')}
                type="tel"
                value={contactPhone}
                disabled={isSubmitting}
                onChange={(e) => setContactPhone(e.target.value)}
                onBlur={() => {
                  markTouched('contactPhone')
                  revalidate()
                }}
                placeholder="+380123456789"
                required
              />
              {getVisibleError('contactPhone') && (
                <div className={styles.errorText}>{getVisibleError('contactPhone')}</div>
              )}
            </div>

            <div className={styles.field}>
              <label className={styles.checkboxRow}>
                <input
                  type="checkbox"
                  checked={termsAccepted}
                  disabled={isSubmitting}
                  onChange={(e) => {
                    setTermsAccepted(e.target.checked)
                    markTouched('termsAccepted')
                    revalidate()
                  }}
                />
                I accept Terms & Conditions
              </label>
              {getVisibleError('termsAccepted') && (
                <div className={styles.errorText}>{getVisibleError('termsAccepted')}</div>
              )}
            </div>

            <button type="submit" className={styles.button} disabled={isSubmitting}>
              {isSubmitting ? 'Registering...' : 'Register'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}