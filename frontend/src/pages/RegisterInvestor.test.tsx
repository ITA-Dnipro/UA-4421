import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RegisterInvestor from './RegisterInvestor'

function mockFetchOnce(ok: boolean, data: any, status = ok ? 200 : 400) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => data,
  } as any)
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/Email/i), 'investor_test@example.com')
  await user.type(screen.getByLabelText(/^Password$/i), 'TestPass123!')
  await user.type(screen.getByLabelText(/Confirm password/i), 'TestPass123!')

  await user.type(screen.getByLabelText(/Investor name/i), 'Test Investor')

  await user.click(screen.getByLabelText('FinTech'))

  await user.clear(screen.getByLabelText(/Minimum investment/i))
  await user.type(screen.getByLabelText(/Minimum investment/i), '1000')

  await user.type(screen.getByLabelText(/Contact name/i), 'John Doe')
  await user.type(screen.getByLabelText(/Contact phone/i), '123456789')

  await user.click(screen.getByLabelText(/I accept Terms/i))
}

describe('RegisterInvestor', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('prevents submit when invalid and shows inline errors on submit', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock as any)

    render(<RegisterInvestor />)

    await user.click(screen.getByRole('button', { name: /Register/i }))

    expect(fetchMock).not.toHaveBeenCalled()

    expect(screen.getByText(/Email is required\./i)).toBeInTheDocument()
    expect(screen.getByText(/Password is required\./i)).toBeInTheDocument()
    expect(screen.getByText(/Confirm your password\./i)).toBeInTheDocument()
    expect(screen.getByText(/Investor name is required\./i)).toBeInTheDocument()
    expect(screen.getByText(/Select at least one sector/i)).toBeInTheDocument()
    expect(screen.getByText(/Minimum investment must be a number/i)).toBeInTheDocument()
    expect(screen.getByText(/Contact name is required\./i)).toBeInTheDocument()
    expect(screen.getByText(/Contact phone is required\./i)).toBeInTheDocument()
    expect(screen.getByText(/You must accept Terms/i)).toBeInTheDocument()
  })

  it('shows password mismatch error', async () => {
    const user = userEvent.setup()
    render(<RegisterInvestor />)

    await user.type(screen.getByLabelText(/Email/i), 'investor_test@example.com')
    await user.type(screen.getByLabelText(/^Password$/i), 'TestPass123!')
    await user.type(screen.getByLabelText(/Confirm password/i), 'Different123!')

    await user.click(screen.getByRole('button', { name: /Register/i }))

    expect(screen.getByText(/Passwords do not match\./i)).toBeInTheDocument()
  })

  it('submits valid form and shows success message', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchOnce(true, { detail: 'Check your email to verify your account.' }, 201)
    vi.stubGlobal('fetch', fetchMock as any)

    render(<RegisterInvestor />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /Register/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/auth/register/')
    expect(options.method).toBe('POST')
    expect(options.headers).toEqual({ 'Content-Type': 'application/json' })

    const body = JSON.parse(options.body)
    expect(body.role).toBe('investor')
    expect(body.email).toBe('investor_test@example.com')
    expect(body.company_name).toBe('Test Investor')
    expect(body.contact_phone).toBe('123456789')

    expect(screen.getByText(/Check your email to verify your account\./i)).toBeInTheDocument()
  })

  it('maps server field error to email field', async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetchOnce(false, { email: ['User with this email already exists.'] }, 400)
    vi.stubGlobal('fetch', fetchMock as any)

    render(<RegisterInvestor />)

    await fillValidForm(user)
    await user.click(screen.getByRole('button', { name: /Register/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    expect(screen.getByText(/User with this email already exists\./i)).toBeInTheDocument()
  })
})
