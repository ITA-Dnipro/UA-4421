import { type ChangeEvent, type CSSProperties, type FormEvent, useMemo, useState } from 'react'

type FieldKey =
  | 'email'
  | 'password'
  | 'passwordConfirm'
  | 'companyName'
  | 'shortPitch'
  | 'website'
  | 'contact'
  | 'logo'
  | 'pitchDeck'
  | 'termsAccepted'

type FieldErrors = Partial<Record<FieldKey, string>>
type FieldTouched = Partial<Record<FieldKey, boolean>>

type Values = {
  email: string
  password: string
  passwordConfirm: string
  companyName: string
  shortPitch: string
  website: string
  contact: string
  termsAccepted: boolean
}

type UiState = 'idle' | 'submitting' | 'success'

const baseControlStyle: CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid #cbd5e1',
}

const errorControlStyle: CSSProperties = {
  ...baseControlStyle,
  borderColor: '#dc2626',
}

const errorTextStyle: CSSProperties = {
  color: '#dc2626',
  fontSize: 13,
  lineHeight: 1.3,
}

const MAX_LOGO_BYTES = 2 * 1024 * 1024
const MAX_PITCH_DECK_BYTES = 10 * 1024 * 1024

const LOGO_MIME_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp'])
const PITCH_DECK_MIME_TYPES = new Set(['application/pdf'])

function validateLogoFile(file: File) {
  if (!LOGO_MIME_TYPES.has(file.type)) return 'Logo must be PNG, JPG, or WEBP.'
  if (file.size > MAX_LOGO_BYTES) return 'Logo must be 2MB or smaller.'
  return undefined
}

function validatePitchDeckFile(file: File) {
  if (!PITCH_DECK_MIME_TYPES.has(file.type)) return 'Pitch deck must be a PDF.'
  if (file.size > MAX_PITCH_DECK_BYTES) return 'Pitch deck must be 10MB or smaller.'
  return undefined
}

function isBlank(value: string) {
  return value.trim().length === 0
}

function isEmail(value: string) {
  return /^\S+@\S+\.\S+$/.test(value.trim())
}

function isValidHttpUrl(value: string) {
  try {
    const url = new URL(value.trim())
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

function validateAll(values: Values): FieldErrors {
  const next: FieldErrors = {}

  if (isBlank(values.email)) next.email = 'Email is required.'
  else if (!isEmail(values.email)) next.email = 'Enter a valid email.'

  if (isBlank(values.password)) next.password = 'Password is required.'
  else if (values.password.length < 8) next.password = 'Password must be at least 8 characters.'

  if (isBlank(values.passwordConfirm)) next.passwordConfirm = 'Confirm your password.'
  else if (values.passwordConfirm !== values.password)
    next.passwordConfirm = 'Passwords do not match.'

  if (isBlank(values.companyName)) next.companyName = 'Company name is required.'
  if (isBlank(values.shortPitch)) next.shortPitch = 'Short pitch is required.'

  if (isBlank(values.website)) next.website = 'Website is required.'
  else if (!isValidHttpUrl(values.website)) next.website = 'Enter a valid URL (http/https).'

  if (isBlank(values.contact)) next.contact = 'Contact is required.'

  if (!values.termsAccepted) next.termsAccepted = 'You must accept the Terms & Privacy Policy.'

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
  if (companyNameMsg) fieldErrors.companyName = companyNameMsg

  const shortPitchMsg = toMessage(obj.short_pitch)
  if (shortPitchMsg) fieldErrors.shortPitch = shortPitchMsg

  const websiteMsg = toMessage(obj.website)
  if (websiteMsg) fieldErrors.website = websiteMsg

  const contactMsg = toMessage(obj.contact_phone)
  if (contactMsg) fieldErrors.contact = contactMsg

  return { fieldErrors, general }
}

export default function RegisterStartup() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [shortPitch, setShortPitch] = useState('')
  const [website, setWebsite] = useState('')
  const [contact, setContact] = useState('')
  const [termsAccepted, setTermsAccepted] = useState(false)

  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [pitchDeckFile, setPitchDeckFile] = useState<File | null>(null)

  const [errors, setErrors] = useState<FieldErrors>({})
  const [touched, setTouched] = useState<FieldTouched>({})
  const [submitAttempted, setSubmitAttempted] = useState(false)

  const [uiState, setUiState] = useState<UiState>('idle')
  const [banner, setBanner] = useState<string>('')

  const chosenLogoName = useMemo(() => logoFile?.name ?? 'No file chosen', [logoFile])
  const chosenPitchDeckName = useMemo(
    () => pitchDeckFile?.name ?? 'No file chosen',
    [pitchDeckFile],
  )

  function getValues(): Values {
    return {
      email,
      password,
      passwordConfirm,
      companyName,
      shortPitch,
      website,
      contact,
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

  function controlStyle(key: FieldKey) {
    return getVisibleError(key) ? errorControlStyle : baseControlStyle
  }

  function revalidate() {
    setErrors((prev) => ({
      ...validateAll(getValues()),
      logo: prev.logo,
      pitchDeck: prev.pitchDeck,
    }))
  }

  function onLogoChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null
    markTouched('logo')

    if (!file) {
      setLogoFile(null)
      setErrors((prev) => ({ ...prev, logo: undefined }))
      return
    }

    const message = validateLogoFile(file)
    if (message) {
      setLogoFile(null)
      e.currentTarget.value = ''
      setErrors((prev) => ({ ...prev, logo: message }))
      return
    }

    setLogoFile(file)
    setErrors((prev) => ({ ...prev, logo: undefined }))
  }

  function onPitchDeckChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null
    markTouched('pitchDeck')

    if (!file) {
      setPitchDeckFile(null)
      setErrors((prev) => ({ ...prev, pitchDeck: undefined }))
      return
    }

    const message = validatePitchDeckFile(file)
    if (message) {
      setPitchDeckFile(null)
      e.currentTarget.value = ''
      setErrors((prev) => ({ ...prev, pitchDeck: message }))
      return
    }

    setPitchDeckFile(file)
    setErrors((prev) => ({ ...prev, pitchDeck: undefined }))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitAttempted(true)
    setBanner('')

    const base = validateAll(getValues())
    const combined: FieldErrors = { ...base }
    if (errors.logo) combined.logo = errors.logo
    if (errors.pitchDeck) combined.pitchDeck = errors.pitchDeck

    setErrors(combined)
    if (Object.keys(combined).length > 0) return

    setUiState('submitting')

    try {
      const payload = {
        email: email.trim(),
        password,
        role: 'startup',
        company_name: companyName.trim(),
        short_pitch: shortPitch.trim(),
        website: website.trim(),
        contact_phone: contact.trim(),
      }

      const res = await fetch('/api/auth/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await res.json().catch(() => undefined)

      if (res.ok) {
        setUiState('success')
        setBanner('Check your email to verify your account.')
        return
      }

      const parsed = mapServerErrorsToFields(data)
      const nextErrors: FieldErrors = { ...combined, ...parsed.fieldErrors }

      setErrors(nextErrors)

      if (parsed.general) setBanner(parsed.general)
      else if (Object.keys(parsed.fieldErrors).length > 0)
        setBanner('Please fix the highlighted fields and try again.')
      else setBanner('Registration failed. Please try again.')

      setUiState('idle')
    } catch {
      setBanner('Network error. Please try again.')
      setUiState('idle')
    }
  }

  const emailError = getVisibleError('email')
  const passwordError = getVisibleError('password')
  const passwordConfirmError = getVisibleError('passwordConfirm')
  const companyNameError = getVisibleError('companyName')
  const shortPitchError = getVisibleError('shortPitch')
  const websiteError = getVisibleError('website')
  const contactError = getVisibleError('contact')
  const logoError = getVisibleError('logo')
  const pitchDeckError = getVisibleError('pitchDeck')
  const termsError = getVisibleError('termsAccepted')

  if (uiState === 'success') {
    return (
      <div style={{ maxWidth: 560, width: '100%', margin: '0 auto', textAlign: 'left' }}>
        <h1 style={{ fontSize: 28, marginBottom: 12 }}>Startup registration</h1>
        <div aria-live="polite" style={{ marginBottom: 12 }}>
          {banner}
        </div>
        <div style={{ opacity: 0.85 }}>
          If you don&apos;t see the email, check your spam folder or try again later.
        </div>
      </div>
    )
  }

  const isSubmitting = uiState === 'submitting'

  return (
    <div style={{ maxWidth: 560, width: '100%', margin: '0 auto', textAlign: 'left' }}>
      <h1 style={{ fontSize: 28, marginBottom: 16 }}>Startup registration</h1>

      <div aria-live="polite" style={{ minHeight: 24, marginBottom: 12 }}>
        {banner}
      </div>

      <form onSubmit={onSubmit} noValidate aria-busy={isSubmitting}>
        <div style={{ display: 'grid', gap: 12 }}>
          <label style={{ display: 'grid', gap: 6 }}>
            Email
            <input
              type="email"
              name="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => {
                markTouched('email')
                revalidate()
              }}
              autoComplete="email"
              required
              disabled={isSubmitting}
              style={controlStyle('email')}
              aria-invalid={Boolean(emailError)}
              aria-describedby={emailError ? 'email-error' : undefined}
            />
            {emailError && (
              <div id="email-error" role="alert" style={errorTextStyle}>
                {emailError}
              </div>
            )}
          </label>

          <label style={{ display: 'grid', gap: 6 }}>
            Password
            <input
              type="password"
              name="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={() => {
                markTouched('password')
                revalidate()
              }}
              autoComplete="new-password"
              required
              disabled={isSubmitting}
              style={controlStyle('password')}
              aria-invalid={Boolean(passwordError)}
              aria-describedby={passwordError ? 'password-error' : undefined}
            />
            {passwordError && (
              <div id="password-error" role="alert" style={errorTextStyle}>
                {passwordError}
              </div>
            )}
          </label>

          <label style={{ display: 'grid', gap: 6 }}>
            Confirm password
            <input
              type="password"
              name="passwordConfirm"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              onBlur={() => {
                markTouched('passwordConfirm')
                revalidate()
              }}
              autoComplete="new-password"
              required
              disabled={isSubmitting}
              style={controlStyle('passwordConfirm')}
              aria-invalid={Boolean(passwordConfirmError)}
              aria-describedby={passwordConfirmError ? 'passwordConfirm-error' : undefined}
            />
            {passwordConfirmError && (
              <div id="passwordConfirm-error" role="alert" style={errorTextStyle}>
                {passwordConfirmError}
              </div>
            )}
          </label>

          <label style={{ display: 'grid', gap: 6 }}>
            Company name
            <input
              type="text"
              name="companyName"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              onBlur={() => {
                markTouched('companyName')
                revalidate()
              }}
              autoComplete="organization"
              required
              disabled={isSubmitting}
              style={controlStyle('companyName')}
              aria-invalid={Boolean(companyNameError)}
              aria-describedby={companyNameError ? 'companyName-error' : undefined}
            />
            {companyNameError && (
              <div id="companyName-error" role="alert" style={errorTextStyle}>
                {companyNameError}
              </div>
            )}
          </label>

          <label style={{ display: 'grid', gap: 6 }}>
            Short pitch
            <textarea
              name="shortPitch"
              value={shortPitch}
              onChange={(e) => setShortPitch(e.target.value)}
              onBlur={() => {
                markTouched('shortPitch')
                revalidate()
              }}
              rows={3}
              required
              disabled={isSubmitting}
              style={controlStyle('shortPitch')}
              aria-invalid={Boolean(shortPitchError)}
              aria-describedby={shortPitchError ? 'shortPitch-error' : undefined}
            />
            {shortPitchError && (
              <div id="shortPitch-error" role="alert" style={errorTextStyle}>
                {shortPitchError}
              </div>
            )}
          </label>

          <label style={{ display: 'grid', gap: 6 }}>
            Website
            <input
              type="url"
              name="website"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              onBlur={() => {
                markTouched('website')
                revalidate()
              }}
              placeholder="https://example.com"
              required
              disabled={isSubmitting}
              style={controlStyle('website')}
              aria-invalid={Boolean(websiteError)}
              aria-describedby={websiteError ? 'website-error' : undefined}
            />
            {websiteError && (
              <div id="website-error" role="alert" style={errorTextStyle}>
                {websiteError}
              </div>
            )}
          </label>

          <label style={{ display: 'grid', gap: 6 }}>
            Contact
            <input
              type="text"
              name="contact"
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              onBlur={() => {
                markTouched('contact')
                revalidate()
              }}
              placeholder="+380..."
              required
              disabled={isSubmitting}
              style={controlStyle('contact')}
              aria-invalid={Boolean(contactError)}
              aria-describedby={contactError ? 'contact-error' : undefined}
            />
            {contactError && (
              <div id="contact-error" role="alert" style={errorTextStyle}>
                {contactError}
              </div>
            )}
          </label>

          <label style={{ display: 'grid', gap: 6 }}>
            <span>Logo (optional)</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <input
                aria-label="Logo (optional)"
                type="file"
                name="logo"
                accept="image/png,image/jpeg,image/webp"
                onChange={onLogoChange}
                disabled={isSubmitting}
                aria-invalid={Boolean(logoError)}
                aria-describedby={logoError ? 'logo-error' : undefined}
              />
              <span style={{ fontSize: 14, opacity: 0.8 }}>{chosenLogoName}</span>
            </div>
            {logoError && (
              <div id="logo-error" role="alert" style={errorTextStyle}>
                {logoError}
              </div>
            )}
          </label>

          <label style={{ display: 'grid', gap: 6 }}>
            <span>Pitch deck (optional)</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <input
                aria-label="Pitch deck (optional)"
                type="file"
                name="pitchDeck"
                accept="application/pdf"
                onChange={onPitchDeckChange}
                disabled={isSubmitting}
                aria-invalid={Boolean(pitchDeckError)}
                aria-describedby={pitchDeckError ? 'pitchDeck-error' : undefined}
              />
              <span style={{ fontSize: 14, opacity: 0.8 }}>{chosenPitchDeckName}</span>
            </div>
            {pitchDeckError && (
              <div id="pitchDeck-error" role="alert" style={errorTextStyle}>
                {pitchDeckError}
              </div>
            )}
          </label>

          <label style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <input
              type="checkbox"
              name="termsAccepted"
              checked={termsAccepted}
              onChange={(e) => setTermsAccepted(e.target.checked)}
              onBlur={() => {
                markTouched('termsAccepted')
                revalidate()
              }}
              required
              disabled={isSubmitting}
              aria-invalid={Boolean(termsError)}
              aria-describedby={termsError ? 'termsAccepted-error' : undefined}
            />
            <span>I accept the Terms &amp; Privacy Policy</span>
          </label>
          {termsError && (
            <div id="termsAccepted-error" role="alert" style={errorTextStyle}>
              {termsError}
            </div>
          )}

          <button type="submit" style={{ width: '100%' }} disabled={isSubmitting}>
            {isSubmitting ? 'Registering...' : 'Register'}
          </button>
        </div>
      </form>
    </div>
  )
}
