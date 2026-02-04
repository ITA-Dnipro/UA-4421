import { cleanup, render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import RegisterStartup from './RegisterStartup'

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

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('Email'), 'test@example.com')
  await user.type(screen.getByLabelText('Password'), 'password123')
  await user.type(screen.getByLabelText('Confirm password'), 'password123')
  await user.type(screen.getByLabelText('Company name'), 'Acme Inc')
  await user.type(screen.getByLabelText('Short pitch'), 'We build something useful.')
  await user.type(screen.getByLabelText('Website'), 'https://example.com')
  await user.type(screen.getByLabelText('Contact'), '+380000000000')
  await user.click(screen.getByLabelText('I accept the Terms & Privacy Policy'))
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('RegisterStartup', () => {
  it('blocks submit and shows inline errors when invalid', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<RegisterStartup />)

    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(fetchMock).not.toHaveBeenCalled()

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
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<RegisterStartup />)

    await fillValidForm(user)

    const emailInput = screen.getByLabelText('Email')
    await user.clear(emailInput)
    await user.type(emailInput, 'not-an-email')

    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(fetchMock).not.toHaveBeenCalled()
    expect(await screen.findByText('Enter a valid email.')).toBeInTheDocument()
  })

  it('validates password min length and blocks submit', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<RegisterStartup />)

    await fillValidForm(user)

    const passwordInput = screen.getByLabelText('Password')
    const confirmInput = screen.getByLabelText('Confirm password')

    await user.clear(passwordInput)
    await user.type(passwordInput, '1234567')

    await user.clear(confirmInput)
    await user.type(confirmInput, '1234567')

    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(fetchMock).not.toHaveBeenCalled()
    expect(
      await screen.findByText('Password must be at least 8 characters.'),
    ).toBeInTheDocument()
  })

  it('validates password confirmation match and blocks submit', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<RegisterStartup />)

    await fillValidForm(user)

    const confirmInput = screen.getByLabelText('Confirm password')
    await user.clear(confirmInput)
    await user.type(confirmInput, 'password124')

    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(fetchMock).not.toHaveBeenCalled()
    expect(await screen.findByText('Passwords do not match.')).toBeInTheDocument()
  })

  it('validates website URL format (http/https) and blocks submit', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<RegisterStartup />)

    await fillValidForm(user)

    const websiteInput = screen.getByLabelText('Website')
    await user.clear(websiteInput)
    await user.type(websiteInput, 'example.com')

    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(fetchMock).not.toHaveBeenCalled()
    expect(
      await screen.findByText('Enter a valid URL (http/https).'),
    ).toBeInTheDocument()
  })

  it('shows selected filenames when uploading files', async () => {
    const user = userEvent.setup()
    render(<RegisterStartup />)

    const logoInput = screen.getByLabelText('Logo (optional)') as HTMLInputElement
    const deckInput = screen.getByLabelText('Pitch deck (optional)') as HTMLInputElement

    const logo = new File(['logo'], 'logo.png', { type: 'image/png' })
    const deck = new File(['deck'], 'deck.pdf', { type: 'application/pdf' })

    await user.upload(logoInput, logo)
    expect(await screen.findByText('logo.png')).toBeInTheDocument()

    await user.upload(deckInput, deck)
    expect(await screen.findByText('deck.pdf')).toBeInTheDocument()
  })

  it('shows inline errors for invalid upload type and size', async () => {
    render(<RegisterStartup />)

    const logoInput = screen.getByLabelText('Logo (optional)') as HTMLInputElement
    const deckInput = screen.getByLabelText('Pitch deck (optional)') as HTMLInputElement

    // Use fireEvent to bypass any accept-filtering behavior from userEvent.upload
    const badLogo = new File(['nope'], 'logo.txt', { type: 'text/plain' })
    fireEvent.change(logoInput, { target: { files: [badLogo] } })
    expect(await screen.findByText('Logo has an unsupported file type.')).toBeInTheDocument()

    // Avoid allocating a 15+MB buffer; try to override the size first, fallback to real buffer if needed
    let tooLargeDeck = new File(['deck'], 'big.pdf', { type: 'application/pdf' })
    try {
      Object.defineProperty(tooLargeDeck, 'size', { value: 15 * 1024 * 1024 + 1 })
    } catch {
      // ignore
    }
    if (tooLargeDeck.size <= 15 * 1024 * 1024) {
      tooLargeDeck = new File([new Uint8Array(15 * 1024 * 1024 + 1)], 'big.pdf', {
        type: 'application/pdf',
      })
    }
    fireEvent.change(deckInput, { target: { files: [tooLargeDeck] } })
    expect(await screen.findByText('Pitch deck is too large.')).toBeInTheDocument()
  })


  it('submits valid form via FormData (no Content-Type header) and shows success', async () => {
    const user = userEvent.setup()

    const d = deferred<{
      ok: boolean
      status: number
      json: () => Promise<unknown>
    }>()

    const fetchMock = vi.fn().mockImplementation(() => d.promise)
    vi.stubGlobal('fetch', fetchMock)

    render(<RegisterStartup />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(await screen.findByRole('button', { name: 'Registering...' })).toBeInTheDocument()

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/auth/register/')
    expect((options as any).method).toBe('POST')

    expect((options as any).headers).toBeUndefined()

    const body = (options as any).body
    expect(body).toBeInstanceOf(FormData)

    const fd = body as FormData
    expect(fd.get('role')).toBe('startup')
    expect(fd.get('email')).toBe('test@example.com')
    expect(fd.get('password')).toBe('password123')
    expect(fd.get('company_name')).toBe('Acme Inc')
    expect(fd.get('short_pitch')).toBe('We build something useful.')
    expect(fd.get('website')).toBe('https://example.com')
    expect(fd.get('contact_phone')).toBe('+380000000000')

    expect(fd.get('logo')).toBeNull()
    expect(fd.get('pitch_deck')).toBeNull()

    d.resolve({
      ok: true,
      status: 201,
      json: async () => ({}),
    })

    expect(await screen.findByText('Check your email to verify your account.')).toBeInTheDocument()
  })

  it('includes selected files in FormData when uploading and submitting', async () => {
    const user = userEvent.setup()

    const d = deferred<{
      ok: boolean
      status: number
      json: () => Promise<unknown>
    }>()

    const fetchMock = vi.fn().mockImplementation(() => d.promise)
    vi.stubGlobal('fetch', fetchMock)

    render(<RegisterStartup />)

    const logoInput = screen.getByLabelText('Logo (optional)') as HTMLInputElement
    const deckInput = screen.getByLabelText('Pitch deck (optional)') as HTMLInputElement

    const logo = new File(['logo'], 'logo.png', { type: 'image/png' })
    const deck = new File(['deck'], 'deck.pdf', { type: 'application/pdf' })

    await user.upload(logoInput, logo)
    await user.upload(deckInput, deck)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: 'Register' }))

    const [, options] = fetchMock.mock.calls[0]
    const fd = (options as any).body as FormData

    const sentLogo = fd.get('logo')
    const sentDeck = fd.get('pitch_deck')

    expect(sentLogo).toBeInstanceOf(File)
    expect((sentLogo as File).name).toBe('logo.png')

    expect(sentDeck).toBeInstanceOf(File)
    expect((sentDeck as File).name).toBe('deck.pdf')

    d.resolve({
      ok: true,
      status: 201,
      json: async () => ({}),
    })

    expect(await screen.findByText('Check your email to verify your account.')).toBeInTheDocument()
  })

  it('shows backend field errors inline', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({
        email: ['Email already exists.'],
        company_name: ['Company name is invalid.'],
      }),
    })

    vi.stubGlobal('fetch', fetchMock)

    render(<RegisterStartup />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(await screen.findByText('Email already exists.')).toBeInTheDocument()
    expect(await screen.findByText('Company name is invalid.')).toBeInTheDocument()
    expect(
      await screen.findByText('Please fix the highlighted fields and try again.'),
    ).toBeInTheDocument()
  })
})
