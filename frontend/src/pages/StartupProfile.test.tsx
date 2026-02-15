import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import StartupProfile from './StartupProfile'

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
})
