import { cleanup, render, screen } from '@testing-library/react'
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
    expect(screen.getByText('You must accept the Terms & Privacy Policy.')).toBeInTheDocument()
  })

  it('submits valid form, shows loading state, then success confirmation', async () => {
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

    const [, options] = fetchMock.mock.calls[0]

    expect((options as any).method).toBe('POST')
    expect((options as any).headers).toEqual(
      expect.objectContaining({ 'Content-Type': 'application/json' }),
    )

    const body = JSON.parse((options as { body: string }).body)

    expect(body.role).toBe('startup')
    expect(body.email).toBe('test@example.com')
    expect(body.password).toBe('password123')
    expect(body.company_name).toBe('Acme Inc')
    expect(body.short_pitch).toBe('We build something useful.')
    expect(body.website).toBe('https://example.com')
    expect(body.contact_phone).toBe('+380000000000')

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
