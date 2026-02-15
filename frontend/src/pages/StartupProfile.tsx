import { useEffect, useState } from 'react'
import styles from './StartupProfile.module.css'

type StartupMe = {
  company_name?: string
  slug?: string
  short_pitch?: string
  website?: string
  contact_email?: string
  contact_phone?: string
  logo_url?: string | null
  pitch_deck_url?: string | null
}

const LOGO_MAX_BYTES = 10 * 1024 * 1024
const PITCH_DECK_MAX_BYTES = 10 * 1024 * 1024

const LOGO_ALLOWED_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp', 'image/svg+xml'])
const PITCH_DECK_ALLOWED_TYPES = new Set([
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
])

function validateOptionalFile(
  file: File | null,
  opts: { label: string; allowedTypes: Set<string>; maxBytes: number },
): string | undefined {
  if (!file) return undefined
  if (!opts.allowedTypes.has(file.type)) return `${opts.label} has an unsupported file type.`
  if (file.size > opts.maxBytes) return `${opts.label} is too large.`
  return undefined
}

function uploadWithProgress(params: {
  url: string
  token: string
  file: File
  purpose: string
  onProgress: (percent: number) => void
}): Promise<{ id: number }> {
  const { url, token, file, purpose, onProgress } = params

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', url)
    xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    xhr.upload.onprogress = (evt) => {
      if (!evt.lengthComputable) return
      const percent = Math.round((evt.loaded / evt.total) * 100)
      onProgress(percent)
    }

    xhr.onload = () => {
      let data: any = null
      try {
        data = xhr.responseText ? JSON.parse(xhr.responseText) : null
      } catch {
        data = null
      }

      if (xhr.status >= 200 && xhr.status < 300 && data?.id) {
        resolve({ id: Number(data.id) })
        return
      }
      reject(data || { detail: 'Upload failed.' })
    }

    xhr.onerror = () => reject({ detail: 'Network error' })

    const fd = new FormData()
    fd.append('file', file)
    fd.append('purpose', purpose)
    xhr.send(fd)
  })
}

async function fetchMe(token: string): Promise<StartupMe> {
  const res = await fetch('/api/startups/me/', {
    headers: { Authorization: `Bearer ${token}` },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw data
  return data as StartupMe
}

async function patchMe(
  token: string,
  payload: { logo_upload_id?: number; pitch_deck_upload_id?: number },
) {
  const res = await fetch('/api/startups/me/', {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw data
  return data as StartupMe
}

function toMessage(value: unknown): string | undefined {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    const parts = value.map((v) => (typeof v === 'string' ? v : '')).filter(Boolean)
    return parts.length ? parts.join(' ') : undefined
  }
  if (value && typeof value === 'object') {
    const obj = value as any
    if (typeof obj.detail === 'string') return obj.detail
  }
  return undefined
}

export default function StartupProfile() {
  const token = localStorage.getItem('token') || localStorage.getItem('accessToken') || ''

  const [profile, setProfile] = useState<StartupMe | null>(null)
  const [banner, setBanner] = useState('')

  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreviewUrl, setLogoPreviewUrl] = useState<string | null>(null)
  const [logoError, setLogoError] = useState<string>('')
  const [logoProgress, setLogoProgress] = useState(0)
  const [logoBusy, setLogoBusy] = useState(false)

  const [deckFile, setDeckFile] = useState<File | null>(null)
  const [deckError, setDeckError] = useState<string>('')
  const [deckProgress, setDeckProgress] = useState(0)
  const [deckBusy, setDeckBusy] = useState(false)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const data = await fetchMe(token)
        if (mounted) setProfile(data)
      } catch (e) {
        if (mounted) setBanner(toMessage(e) || 'Failed to load startup profile.')
      }
    })()
    return () => {
      mounted = false
    }
  }, [token])

  useEffect(() => {
    return () => {
      if (logoPreviewUrl) URL.revokeObjectURL(logoPreviewUrl)
    }
  }, [logoPreviewUrl])

  async function refresh() {
    const data = await fetchMe(token)
    setProfile(data)
  }

  async function handleUploadLogo() {
    setBanner('')
    const msg = validateOptionalFile(logoFile, {
      label: 'Logo',
      allowedTypes: LOGO_ALLOWED_TYPES,
      maxBytes: LOGO_MAX_BYTES,
    })
    if (msg) {
      setLogoError(msg)
      return
    }
    if (!logoFile) {
      setLogoError('Select a file first.')
      return
    }

    try {
      setLogoBusy(true)
      setLogoProgress(0)
      const up = await uploadWithProgress({
        url: '/api/uploads/',
        token,
        file: logoFile,
        purpose: 'logo',
        onProgress: setLogoProgress,
      })
      await patchMe(token, { logo_upload_id: up.id })
      await refresh()
      setBanner('Logo updated.')
    } catch (e) {
      setBanner(toMessage(e) || 'Logo upload failed.')
    } finally {
      setLogoBusy(false)
    }
  }

  async function handleUploadDeck() {
    setBanner('')
    const msg = validateOptionalFile(deckFile, {
      label: 'Pitch deck',
      allowedTypes: PITCH_DECK_ALLOWED_TYPES,
      maxBytes: PITCH_DECK_MAX_BYTES,
    })
    if (msg) {
      setDeckError(msg)
      return
    }
    if (!deckFile) {
      setDeckError('Select a file first.')
      return
    }

    try {
      setDeckBusy(true)
      setDeckProgress(0)
      const up = await uploadWithProgress({
        url: '/api/uploads/',
        token,
        file: deckFile,
        purpose: 'pitch_deck',
        onProgress: setDeckProgress,
      })
      await patchMe(token, { pitch_deck_upload_id: up.id })
      await refresh()
      setBanner('Pitch deck updated.')
    } catch (e) {
      setBanner(toMessage(e) || 'Pitch deck upload failed.')
    } finally {
      setDeckBusy(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.card}>
          <h1 className={styles.title}>Startup profile</h1>
          <div aria-live="polite" className={styles.banner}>
            {banner}
          </div>

          <div className={styles.grid}>
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>Current</h2>
              <div className={styles.row}>
                <span className={styles.label}>Company:</span>
                <span>{profile?.company_name || '—'}</span>
              </div>
              <div className={styles.row}>
                <span className={styles.label}>Logo URL:</span>
                {profile?.logo_url ? (
                  <a className={styles.link} href={profile.logo_url} target="_blank" rel="noreferrer">
                    open
                  </a>
                ) : (
                  <span>—</span>
                )}
              </div>
              <div className={styles.row}>
                <span className={styles.label}>Pitch deck URL:</span>
                {profile?.pitch_deck_url ? (
                  <a
                    className={styles.link}
                    href={profile.pitch_deck_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    open
                  </a>
                ) : (
                  <span>—</span>
                )}
              </div>
            </div>

            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>Update logo</h2>
              <div className={styles.row}>
                <input
                  className={logoError ? `${styles.input} ${styles.inputError}` : styles.input}
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/svg+xml"
                  disabled={logoBusy || deckBusy}
                  onChange={(e) => {
                    const file = e.target.files?.[0] ?? null
                    setLogoFile(file)
                    setLogoError('')

                    if (logoPreviewUrl) URL.revokeObjectURL(logoPreviewUrl)
                    setLogoPreviewUrl(file ? URL.createObjectURL(file) : null)
                  }}
                />

                <button
                  className={styles.button}
                  type="button"
                  disabled={logoBusy || deckBusy || !logoFile}
                  onClick={handleUploadLogo}
                >
                  {logoBusy ? 'Uploading...' : 'Upload'}
                </button>
              </div>

              {logoFile && <div className={styles.fileName}>{logoFile.name}</div>}

              {logoPreviewUrl && (
                <img className={styles.logoPreview} src={logoPreviewUrl} alt="Logo preview" />
              )}

              {logoBusy && logoProgress > 0 && (
                <div className={styles.progressRow}>
                  <progress className={styles.progress} value={logoProgress} max={100} />
                  <span className={styles.progressText}>{logoProgress}%</span>
                </div>
              )}

              {logoError && <div className={styles.errorText}>{logoError}</div>}
            </div>

            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>Update pitch deck</h2>
              <div className={styles.row}>
                <input
                  className={deckError ? `${styles.input} ${styles.inputError}` : styles.input}
                  type="file"
                  accept="application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.pdf,.docx"
                  disabled={logoBusy || deckBusy}
                  onChange={(e) => {
                    const file = e.target.files?.[0] ?? null
                    setDeckFile(file)
                    setDeckError('')
                  }}
                />

                <button
                  className={styles.button}
                  type="button"
                  disabled={logoBusy || deckBusy || !deckFile}
                  onClick={handleUploadDeck}
                >
                  {deckBusy ? 'Uploading...' : 'Upload'}
                </button>
              </div>

              {deckFile && <div className={styles.fileName}>{deckFile.name}</div>}

              {deckBusy && deckProgress > 0 && (
                <div className={styles.progressRow}>
                  <progress className={styles.progress} value={deckProgress} max={100} />
                  <span className={styles.progressText}>{deckProgress}%</span>
                </div>
              )}

              {deckError && <div className={styles.errorText}>{deckError}</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
