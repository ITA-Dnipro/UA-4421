import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import styles from './SavedPage.module.css'

type SavedItem = {
  id: string
  saved_id: number
  type: 'company' | 'startup' | 'project'
  title: string
  short_description: string
  location: string
  tags: string[]
}

const TABS = [
  { label: 'All', value: '' },
  { label: 'Companies', value: 'company' },
  { label: 'Startups', value: 'startup' },
  { label: 'Projects', value: 'project' },
]

const parseJwt = (token: string) => {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      window
        .atob(base64)
        .split('')
        .map(function (c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
        })
        .join('')
    )

    return JSON.parse(jsonPayload)
  } catch (e) {
    return null
  }
}

export default function SavedPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [items, setItems] = useState<SavedItem[]>([])
  const [next, setNext] = useState<string | null>(null)
  const [loading, setLoading] = useState(!!localStorage.getItem('token'))

  const type = searchParams.get('type') || ''
  const token = localStorage.getItem('token')

  let userId: number | null = null
  if (token) {
    const decoded = parseJwt(token)
    if (decoded?.user_id) {
      userId = decoded.user_id
    }
  }

  useEffect(() => {
    if (userId) {
      fetchSaved(1, true)
    }
  }, [type, userId])

  const fetchSaved = async (page = 1, replace = false) => {
    if (!userId || !token) return

    setLoading(true)

    let url = `/api/users/${userId}/saved/?page=${page}&page_size=12`
    if (type) url += `&type=${type}`

    try {
      const res = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (res.ok) {
        const data = await res.json()
        setItems(prev => (replace ? data.results : [...prev, ...data.results]))
        setNext(data.next)
      } else {
        console.error('Failed to fetch saved items:', res.status)
      }
    } catch (error) {
      console.error('Error fetching saved items', error)
    }

    setLoading(false)
  }

  const handleTabChange = (value: string) => {
    if (value) {
      setSearchParams({ type: value })
    } else {
      setSearchParams({})
    }
  }

  if (!token || !userId) {
    return (
      <div className={styles.page}>
        <div className={styles.container}>
          <div className={styles.emptyCard}>
             <h3>Authentication required</h3>
             <p>Please log in to view saved items.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <h1 className={styles.title}>Saved</h1>

        <div className={styles.toolbar}>
          {TABS.map(tab => {
            const isActive = type === tab.value
            return (
              <button
                key={tab.value}
                onClick={() => handleTabChange(tab.value)}
                className={`${styles.tab} ${isActive ? styles.tabActive : ''}`}
              >
                {tab.label}
              </button>
            )
          })}
        </div>

        {loading && items.length === 0 && (
          <div className={styles.grid}>
            {[...Array(8)].map((_, i) => (
              <div key={i} className={styles.card}>
                <div className={`${styles.skeleton} ${styles.skeletonTitle}`} />
                <div className={`${styles.skeleton} ${styles.skeletonText}`} />
                <div className={`${styles.skeleton} ${styles.skeletonText}`} style={{ width: '70%' }} />
                <div className={styles.tags}>
                  <div className={`${styles.skeleton} ${styles.skeletonTag}`} />
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && items.length === 0 && (
          <div className={styles.emptyCard}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📂</div>
            <h3>No saved items yet.</h3>
            <p>Items you save will appear here.</p>
          </div>
        )}

        {items.length > 0 && (
          <div className={styles.grid}>
            {items.map(item => (
              <div key={item.saved_id} className={styles.card}>
                <div className={styles.cardTitle}>{item.title}</div>

                <div className={styles.cardDescription}>
                  {item.short_description}
                </div>

                <div className={styles.tags}>
                  {item.tags.map(tag => (
                    <span key={tag} className={styles.tag}>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {next && !loading && (
          <button
            className={styles.loadMore}
            onClick={() => {
              const url = new URL(next, window.location.origin)
              const nextPage = url.searchParams.get('page')
              if (nextPage) {fetchSaved(Number(nextPage))
              }
            }}
          >
            Load more
          </button>
        )}
      </div>
    </div>
  )
}