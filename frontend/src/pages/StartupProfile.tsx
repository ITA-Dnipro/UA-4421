import { useEffect, useState } from 'react'
import styles from './StartupProfile.module.css'

type StartupMe = {
  company_name: string
  slug?: string
  short_pitch?: string
  about_html?: string
  website?: string
  contact_email?: string
  contact_phone?: string
  hero_image_url?: string
  logo_url?: string | null
  pitch_deck_url?: string | null
}

const LOGO_ALLOWED_TYPES = [
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/svg+xml',
] as const

const PITCH_DECK_ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
] as const

const LOGO_MAX_BYTES = 10 * 1024 * 1024
const PITCH_DECK_MAX_BYTES = 10 * 1024 * 1024

function validateOptionalFile(
  file: File | null,
  rules: { label: string; allowedTypes: readonly string[]; maxBytes: number },
) {
  if (!file) return ''

  if (!rules.allowedTypes.includes(file.type)) {
    return `${rules.label}: invalid file type.`
  }

  if (file.size > rules.maxBytes) {
    const mb = Math.round((rules.maxBytes / (1024 * 1024)) * 10) / 10
    return `${rules.label}: file is too large (max ${mb} MB).`
  }

  return ''
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

function toMessage(value: unknown, preferKeys?: string[]): string | undefined {
  if (typeof value === 'string') return value

  if (Array.isArray(value)) {
    const parts = value
      .map((v) => toMessage(v))
      .filter(Boolean) as string[]
    return parts.length ? parts.join(' ') : undefined
  }

  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>

    if (preferKeys?.length) {
      for (const k of preferKeys) {
        if (Object.prototype.hasOwnProperty.call(obj, k) && obj[k] != null) {
          const msg = toMessage(obj[k])
          if (msg) return msg
        }
      }
    }

    const detail = (obj as any).detail
    if (typeof detail === 'string') return detail

    const fallbackKeys = [
      'file',
      'non_field_errors',
      'logo_upload_id',
      'pitch_deck_upload_id',
      'logo',
      'pitch_deck',
    ]

    for (const k of fallbackKeys) {
      if (Object.prototype.hasOwnProperty.call(obj, k) && obj[k] != null) {
        const msg = toMessage(obj[k])
        if (msg) return msg
      }
    }

    for (const k of Object.keys(obj)) {
      const msg = toMessage(obj[k])
      if (msg) return msg
    }
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
    setLogoError('')
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
      const msg = toMessage(e, ['file', 'logo_upload_id', 'logo'])
      setLogoError(msg || 'Logo upload failed.')
      setBanner(msg ? '' : 'Logo upload failed.')
    } finally {
      setLogoBusy(false)
    }
  }

  async function handleUploadDeck() {
    setBanner('')
    setDeckError('')
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
      const msg = toMessage(e, ['file', 'pitch_deck_upload_id', 'pitch_deck'])
      setDeckError(msg || 'Pitch deck upload failed.')
      setBanner(msg ? '' : 'Pitch deck upload failed.')
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
                <span className={styles.label}>Logo:</span>
                {profile?.logo_url ? (
                  <a
                    className={styles.link}
                    href={profile.logo_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    open
                  </a>
                ) : (
                  <span>—</span>
                )}
              </div>

              <div className={styles.row}>
                <span className={styles.label}>Pitch deck:</span>
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

              {logoPreviewUrl && (
                <div className={styles.row}>
                  <img className={styles.logoPreview} src={logoPreviewUrl} alt="logo preview" />
                </div>
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
