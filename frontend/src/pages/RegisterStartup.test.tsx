import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import RegisterStartup from './RegisterStartup'

async function setTextField(user: ReturnType<typeof userEvent.setup>, label: string, value: string) {
  const el = screen.getByLabelText(label) as HTMLInputElement | HTMLTextAreaElement
  await user.clear(el)
  if (value) await user.type(el, value)
}

async function fillValidForm(
  user: ReturnType<typeof userEvent.setup>,
  overrides?: Partial<{
    email: string
    password: string
    passwordConfirm: string
    companyName: string
    shortPitch: string
    website: string
    contact: string
  }>,
) {
  const v = {
    email: 'test@example.com',
    password: 'password123',
    passwordConfirm: 'password123',
    companyName: 'Acme Inc',
    shortPitch: 'We build something useful.',
    website: 'https://example.com',
    contact: '+380000000000',
    ...overrides,
  }

  await setTextField(user, 'Email', v.email)
  await setTextField(user, 'Password', v.password)
  await setTextField(user, 'Confirm password', v.passwordConfirm)
  await setTextField(user, 'Company name', v.companyName)
  await setTextField(user, 'Short pitch', v.shortPitch)
  await setTextField(user, 'Website', v.website)
  await setTextField(user, 'Contact', v.contact)
  await user.click(screen.getByLabelText('I accept the Terms & Privacy Policy'))
}

function makeTooLargePdf(name = 'big.pdf') {
  const max = 10 * 1024 * 1024
  const file = new File([new Uint8Array(1)], name, { type: 'application/pdf' })
  try {
    Object.defineProperty(file, 'size', { value: max + 1 })
    return file
  } catch {
    // Fallback: real buffer (slower, but reliable)
    return new File([new Uint8Array(max + 1)], name, { type: 'application/pdf' })
  }
}

class MockXHR {
  static instances: MockXHR[] = []

  method = ''
  url = ''
  status = 0
  responseText = ''
  headers: Record<string, string> = {}
  body: any = null

  upload = { onprogress: null as null | ((e: any) => void) }

  onload: null | (() => void) = null
  onerror: null | (() => void) = null

  open(method: string, url: string) {
    this.method = method
    this.url = url
  }

  setRequestHeader(name: string, value: string) {
    this.headers[name] = value
  }

  send(body: any) {
    this.body = body
    MockXHR.instances.push(this)
  }

  respond(status: number, json: unknown) {
    this.status = status
    this.responseText = JSON.stringify(json)
    this.onload?.()
  }

  fail() {
    this.onerror?.()
  }

  static reset() {
    MockXHR.instances = []
  }
}

beforeEach(() => {
  MockXHR.reset()
  vi.stubGlobal('XMLHttpRequest', MockXHR as any)

  Object.defineProperty(URL, 'createObjectURL', {
    value: vi.fn(() => 'blob:logo'),
    writable: true,
    configurable: true,
  })
  Object.defineProperty(URL, 'revokeObjectURL', {
    value: vi.fn(),
    writable: true,
    configurable: true,
  })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('RegisterStartup', () => {
  it('blocks submit and shows inline errors when invalid', async () => {
    const user = userEvent.setup()

    render(<RegisterStartup />)

    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(MockXHR.instances.length).toBe(0)

    expect(await screen.findByText('Email is required.')).toBeInTheDocument()
    expect(screen.getByText('Password is required.')).toBeInTheDocument()
    expect(screen.getByText('Confirm your password.')).toBeInTheDocument()
    expect(screen.getByText('Company name is required.')).toBeInTheDocument()
    expect(screen.getByText('Short pitch is required.')).toBeInTheDocument()
    expect(screen.getByText('Website is required.')).toBeInTheDocument()
    expect(screen.getByText('Contact is required.')).toBeInTheDocument()
    expect(screen.getByText('You must accept the Terms & Privacy Policy.')).toBeInTheDocument()
  })

  it('validates email format and blocks submit', async () => {
    const user = userEvent.setup()

    render(<RegisterStartup />)

    await fillValidForm(user, { email: 'not-an-email' })
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(MockXHR.instances.length).toBe(0)
    expect(await screen.findByText('Enter a valid email.')).toBeInTheDocument()
  })

  it('validates password min length and blocks submit', async () => {
    const user = userEvent.setup()

    render(<RegisterStartup />)

    await fillValidForm(user, { password: '1234567', passwordConfirm: '1234567' })
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(MockXHR.instances.length).toBe(0)
    expect(await screen.findByText('Password must be at least 8 characters.')).toBeInTheDocument()
  })

  it('validates password confirmation match and blocks submit', async () => {
    const user = userEvent.setup()

    render(<RegisterStartup />)

    await fillValidForm(user, { passwordConfirm: 'password124' })
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(MockXHR.instances.length).toBe(0)
    expect(await screen.findByText('Passwords do not match.')).toBeInTheDocument()
  })

  it('shows Website required error when empty (and not URL format error)', async () => {
    const user = userEvent.setup()

    render(<RegisterStartup />)

    await fillValidForm(user, { website: '' })
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(MockXHR.instances.length).toBe(0)
    expect(await screen.findByText('Website is required.')).toBeInTheDocument()
    expect(screen.queryByText('Enter a valid URL (http/https).')).not.toBeInTheDocument()
  })

  it('shows URL format error when Website is non-empty but invalid (and not required error)', async () => {
    const user = userEvent.setup()

    render(<RegisterStartup />)

    await fillValidForm(user, { website: 'not-a-url' })
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(MockXHR.instances.length).toBe(0)
    expect(await screen.findByText('Enter a valid URL (http/https).')).toBeInTheDocument()
    expect(screen.queryByText('Website is required.')).not.toBeInTheDocument()
  })

  it('shows selected filenames when uploading files', async () => {
    const user = userEvent.setup()

    render(<RegisterStartup />)

    const logoInput = screen.getByLabelText('Logo (optional)') as HTMLInputElement
    const deckInput = screen.getByLabelText('Pitch deck (optional)') as HTMLInputElement

    const logo = new File(['logo'], 'logo.png', { type: 'image/png' })
    const deck = new File(['deck'], 'deck.pdf', { type: 'application/pdf' })

    await user.upload(logoInput, logo)
    await user.upload(deckInput, deck)

    expect(await screen.findByText('logo.png')).toBeInTheDocument()
    expect(await screen.findByText('deck.pdf')).toBeInTheDocument()

    // ✅ preview
    expect(await screen.findByAltText('Logo preview')).toBeInTheDocument()
  })

  it('shows inline errors for invalid upload type and size', async () => {
    render(<RegisterStartup />)

    const logoInput = screen.getByLabelText('Logo (optional)') as HTMLInputElement
    const deckInput = screen.getByLabelText('Pitch deck (optional)') as HTMLInputElement

    // IMPORTANT: userEvent.upload may not trigger change when file doesn't match input.accept.
    // fireEvent.change triggers the component's onChange reliably so we can test validation logic.
    const badLogo = new File(['nope'], 'logo.txt', { type: 'text/plain' })
    fireEvent.change(logoInput, { target: { files: [badLogo] } })
    expect(await screen.findByText('Logo has an unsupported file type.')).toBeInTheDocument()

    const tooLargeDeck = makeTooLargePdf()
    fireEvent.change(deckInput, { target: { files: [tooLargeDeck] } })
    expect(await screen.findByText('Pitch deck is too large.')).toBeInTheDocument()
  })

  it('submits valid form via FormData (no Content-Type header) and shows success', async () => {
    const user = userEvent.setup()

    render(<RegisterStartup />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(MockXHR.instances.length).toBe(1)
    expect(await screen.findByRole('button', { name: 'Registering...' })).toBeInTheDocument()

    const xhr = MockXHR.instances[0]
    expect(xhr.url).toBe('/api/auth/register/')
    expect(xhr.method).toBe('POST')

    // Must not set Content-Type manually for FormData
    expect(Object.keys(xhr.headers).length).toBe(0)

    expect(xhr.body).toBeInstanceOf(FormData)
    const fd = xhr.body as FormData

    expect(fd.get('role')).toBe('startup')
    expect(fd.get('email')).toBe('test@example.com')
    expect(fd.get('password')).toBe('password123')
    expect(fd.get('company_name')).toBe('Acme Inc')
    expect(fd.get('short_pitch')).toBe('We build something useful.')
    expect(fd.get('website')).toBe('https://example.com')
    expect(fd.get('contact_phone')).toBe('+380000000000')

    expect(fd.get('logo')).toBeNull()
    expect(fd.get('pitch_deck')).toBeNull()

    // ✅ progress
    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 5, total: 10 })
    expect(await screen.findByText('50%')).toBeInTheDocument()

    xhr.respond(201, {})
    expect(await screen.findByText('Check your email to verify your account.')).toBeInTheDocument()
  })

  it('includes selected files in FormData when uploading and submitting', async () => {
    const user = userEvent.setup()

    render(<RegisterStartup />)

    const logoInput = screen.getByLabelText('Logo (optional)') as HTMLInputElement
    const deckInput = screen.getByLabelText('Pitch deck (optional)') as HTMLInputElement

    const logo = new File(['logo'], 'logo.png', { type: 'image/png' })
    const deck = new File(['deck'], 'deck.pdf', { type: 'application/pdf' })

    await user.upload(logoInput, logo)
    await user.upload(deckInput, deck)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(MockXHR.instances.length).toBe(1)
    const xhr = MockXHR.instances[0]
    const fd = xhr.body as FormData

    const sentLogo = fd.get('logo')
    const sentDeck = fd.get('pitch_deck')

    expect(sentLogo).toBeInstanceOf(File)
    expect((sentLogo as File).name).toBe('logo.png')

    expect(sentDeck).toBeInstanceOf(File)
    expect((sentDeck as File).name).toBe('deck.pdf')

    xhr.respond(201, {})
    expect(await screen.findByText('Check your email to verify your account.')).toBeInTheDocument()
  })

  it('shows backend field errors inline', async () => {
    const user = userEvent.setup()

    render(<RegisterStartup />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(MockXHR.instances.length).toBe(1)
    const xhr = MockXHR.instances[0]

    xhr.respond(400, {
      email: ['Email already exists.'],
      company_name: ['Company name is invalid.'],
    })

    expect(await screen.findByText('Email already exists.')).toBeInTheDocument()
    expect(await screen.findByText('Company name is invalid.')).toBeInTheDocument()
    expect(await screen.findByText('Please fix the highlighted fields and try again.')).toBeInTheDocument()
  })
})
