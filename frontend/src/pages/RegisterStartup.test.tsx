import { cleanup, render, screen, within } from '@testing-library/react'
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
    expect(screen.getByText('Company name is required.')).toBeInTheDocument()
    expect(screen.getByText('Short pitch is required.')).toBeInTheDocument()
    expect(screen.getByText('Website is required.')).toBeInTheDocument()
    expect(screen.getByText('Contact is required.')).toBeInTheDocument()
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
    expect(screen.getByRole('button')).toHaveTextContent('Registering...')

    const [, options] = fetchMock.mock.calls[0]
    const body = JSON.parse((options as { body: string }).body)

    expect(body.role).toBe('startup')
    expect(body.email).toBe('test@example.com')
    expect(body.company_name).toBe('Acme Inc')

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
    expect(screen.getByText('Please fix the highlighted fields and try again.')).toBeInTheDocument()
})

it('validates logo file type and shows filename when valid', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    render(<RegisterStartup />)

    const logoInput = screen.getByLabelText('Logo (optional)') as HTMLInputElement
    const logoLabel = logoInput.closest('label')
    if (!logoLabel) throw new Error('Logo label not found')

    await user.upload(logoInput, new File(['x'], 'logo.txt', { type: 'text/plain' }))

    expect(await screen.findByText('Logo must be PNG, JPG, or WEBP.')).toBeInTheDocument()
    expect(within(logoLabel).getByText('No file chosen')).toBeInTheDocument()

    await user.upload(logoInput, new File(['x'], 'logo.png', { type: 'image/png' }))

    expect(screen.queryByText('Logo must be PNG, JPG, or WEBP.')).not.toBeInTheDocument()
    expect(within(logoLabel).getByText('logo.png')).toBeInTheDocument()
})

it('validates pitch deck file type and shows filename when valid', async () => {
        const user = userEvent.setup()
        const fetchMock = vi.fn()
        vi.stubGlobal('fetch', fetchMock)

        render(<RegisterStartup />)

        const deckInput = screen.getByLabelText('Pitch deck (optional)') as HTMLInputElement
        const deckLabel = deckInput.closest('label')
        if (!deckLabel) throw new Error('Pitch deck label not found')

        await user.upload(deckInput, new File(['x'], 'deck.txt', { type: 'text/plain' }))

        expect(await screen.findByText('Pitch deck must be a PDF.')).toBeInTheDocument()
        expect(within(deckLabel).getByText('No file chosen')).toBeInTheDocument()

        await user.upload(deckInput, new File(['x'], 'deck.pdf', { type: 'application/pdf' }))

        expect(screen.queryByText('Pitch deck must be a PDF.')).not.toBeInTheDocument()
        expect(within(deckLabel).getByText('deck.pdf')).toBeInTheDocument()
    })
})
