import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SavedPage from './SavedPage'

// 🔹 helper для мокання localStorage
function mockLocalStorage(token: string | null) {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation((key: string) => {
    if (key === 'token') return token
    return null
  })
}

// 🔹 helper для створення валідного JWT
function createFakeJwt(userId: number) {
  const payload = {
    user_id: userId,
  }

  const base64 = btoa(JSON.stringify(payload))
  return `header.${base64}.signature`
}

describe('SavedPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows login message when no token', () => {
    mockLocalStorage(null)

    render(
      <MemoryRouter>
        <SavedPage />
      </MemoryRouter>
    )

    expect(
      screen.getByText(/Please log in to view saved items/i)
    ).toBeInTheDocument()
  })

  it('shows skeleton while loading', async () => {
    const token = createFakeJwt(1)
    mockLocalStorage(token)

    // фейковий fetch, який ніколи не резолвиться одразу
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      () =>
        new Promise(() => {
          /* never resolves immediately */
        }) as any
    )

    render(
      <MemoryRouter>
        <SavedPage />
      </MemoryRouter>
    )

    // Скелетон — це card + skeletonCard
    const skeletons = await screen.findAllByRole('generic')

    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('renders saved items after fetch', async () => {
    const token = createFakeJwt(1)
    mockLocalStorage(token)

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [
          {
            id: '1',
            saved_id: 1,
            type: 'startup',
            title: 'Test Startup',
            short_description: 'Test description',
            location: 'NY',
            tags: ['AI'],
          },
        ],
        next: null,
      }),
    } as Response)

    render(
      <MemoryRouter>
        <SavedPage />
      </MemoryRouter>
    )

    await waitFor(() =>
      expect(screen.getByText('Test Startup')).toBeInTheDocument()
    )
  })

  it('shows empty state if no items', async () => {
    const token = createFakeJwt(1)
    mockLocalStorage(token)

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [],
        next: null,
      }),
    } as Response)

    render(
      <MemoryRouter>
        <SavedPage />
      </MemoryRouter>
    )

    await waitFor(() =>
      expect(
        screen.getByText(/No saved items yet./i)
      ).toBeInTheDocument()
    )
  })
})