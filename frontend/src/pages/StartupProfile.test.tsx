import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import StartupProfile from './StartupProfile'

const PITCH_DECK_MAX_BYTES = 10 * 1024 * 1024

function makeOversizedPdf(): File {
  return new File([new Uint8Array(PITCH_DECK_MAX_BYTES + 1)], 'big.pdf', {
    type: 'application/pdf',
  })
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

  static reset() {
    MockXHR.instances = []
  }
}

beforeEach(() => {
  MockXHR.reset()
  vi.stubGlobal('XMLHttpRequest', MockXHR as any)

  localStorage.setItem('token', 'test-token')

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
  localStorage.removeItem('token')
})

describe('StartupProfile', () => {
  it('uploads logo to /api/uploads/ with progress and then PATCHes /api/startups/me/', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn()

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ company_name: 'Acme', logo_url: null, pitch_deck_url: null }),
    })

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true }),
    })

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ company_name: 'Acme', logo_url: 'x', pitch_deck_url: null }),
    })

    vi.stubGlobal('fetch', fetchMock as any)

    render(<StartupProfile />)

    const input = await screen.findByLabelText('', { selector: 'input[type="file"]' })
    await user.upload(
      input,
      new File([new Uint8Array([1, 2, 3])], 'logo.png', { type: 'image/png' }),
    )

    const uploadBtn = screen.getAllByRole('button', { name: 'Upload' })[0]
    await user.click(uploadBtn)

    const xhr = MockXHR.instances[0]
    expect(xhr).toBeTruthy()
    expect(xhr.url).toBe('/api/uploads/')
    expect(xhr.method).toBe('POST')
    expect(xhr.headers.Authorization).toBe('Bearer test-token')

    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 5, total: 10 })
    expect(await screen.findByText('50%')).toBeInTheDocument()

    xhr.respond(201, { id: 123 })

    const patchCall = fetchMock.mock.calls.find(
      (c) => String(c[0]).includes('/api/startups/me/') && c[1]?.method === 'PATCH',
    )
    expect(patchCall).toBeTruthy()
    expect(JSON.parse(patchCall![1].body as string)).toEqual({ logo_upload_id: 123 })
  })

  it('uploads pitch deck to /api/uploads/ with progress and then PATCHes /api/startups/me/', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn()

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ company_name: 'Acme', logo_url: null, pitch_deck_url: null }),
    })

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true }),
    })

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ company_name: 'Acme', logo_url: null, pitch_deck_url: 'x' }),
    })

    vi.stubGlobal('fetch', fetchMock as any)

    render(<StartupProfile />)

    const fileInputs = document.querySelectorAll('input[type="file"]')
    const deckInput = fileInputs[1] as HTMLInputElement

    await user.upload(
      deckInput,
      new File([new Uint8Array([1, 2, 3])], 'deck.pdf', { type: 'application/pdf' }),
    )

    const uploadBtn = screen.getAllByRole('button', { name: 'Upload' })[1]
    await user.click(uploadBtn)

    const xhr = MockXHR.instances[0]
    expect(xhr).toBeTruthy()
    expect(xhr.url).toBe('/api/uploads/')
    expect(xhr.method).toBe('POST')
    expect(xhr.headers.Authorization).toBe('Bearer test-token')

    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 5, total: 10 })
    expect(await screen.findByText('50%')).toBeInTheDocument()

    xhr.respond(201, { id: 456 })

    const patchCall = fetchMock.mock.calls.find(
      (c) => String(c[0]).includes('/api/startups/me/') && c[1]?.method === 'PATCH',
    )
    expect(patchCall).toBeTruthy()
    expect(JSON.parse(patchCall![1].body as string)).toEqual({ pitch_deck_upload_id: 456 })
  })

  it('shows pitch deck validation error for invalid file type and does not upload', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn()
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ company_name: 'Acme', logo_url: null, pitch_deck_url: null }),
    })

    vi.stubGlobal('fetch', fetchMock as any)
    render(<StartupProfile />)

    const fileInputs = document.querySelectorAll('input[type="file"]')
    const deckInput = fileInputs[1] as HTMLInputElement

    fireEvent.change(deckInput, {
      target: {
        files: [new File(['x'], 'deck.txt', { type: 'text/plain' })],
      },
    })

    const uploadBtn = screen.getAllByRole('button', { name: 'Upload' })[1]
    await user.click(uploadBtn)

    expect(await screen.findByText('Pitch deck: invalid file type.')).toBeInTheDocument()
    expect(MockXHR.instances.length).toBe(0)
    expect(fetchMock.mock.calls.some((c) => c[1]?.method === 'PATCH')).toBe(false)
  })

  it('shows pitch deck validation error for oversized file and does not upload', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn()
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ company_name: 'Acme', logo_url: null, pitch_deck_url: null }),
    })

    vi.stubGlobal('fetch', fetchMock as any)
    render(<StartupProfile />)

    const fileInputs = document.querySelectorAll('input[type="file"]')
    const deckInput = fileInputs[1] as HTMLInputElement

    fireEvent.change(deckInput, {
      target: {
        files: [makeOversizedPdf()],
      },
    })

    const uploadBtn = screen.getAllByRole('button', { name: 'Upload' })[1]
    await user.click(uploadBtn)

    expect(
      await screen.findByText('Pitch deck: file is too large (max 10 MB).'),
    ).toBeInTheDocument()
    expect(MockXHR.instances.length).toBe(0)
    expect(fetchMock.mock.calls.some((c) => c[1]?.method === 'PATCH')).toBe(false)
  })

  it('shows server file error when pitch deck upload fails and does not PATCH', async () => {
    const user = userEvent.setup()

    const fetchMock = vi.fn()
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ company_name: 'Acme', logo_url: null, pitch_deck_url: null }),
    })

    vi.stubGlobal('fetch', fetchMock as any)
    render(<StartupProfile />)

    const fileInputs = document.querySelectorAll('input[type="file"]')
    const deckInput = fileInputs[1] as HTMLInputElement

    await user.upload(
      deckInput,
      new File([new Uint8Array([1, 2, 3])], 'deck.pdf', { type: 'application/pdf' }),
    )

    const uploadBtn = screen.getAllByRole('button', { name: 'Upload' })[1]
    await user.click(uploadBtn)

    const xhr = MockXHR.instances[0]
    expect(xhr).toBeTruthy()

    xhr.respond(400, { file: ['Invalid file.'] })

    expect(await screen.findByText('Invalid file.')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some((c) => c[1]?.method === 'PATCH')).toBe(false)
  })
})
