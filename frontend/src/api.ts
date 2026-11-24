let currentUser = localStorage.getItem('sh_user') || ''

export function setUser(id: string) {
  currentUser = id
  if (id) localStorage.setItem('sh_user', id)
  else localStorage.removeItem('sh_user')
}
export function getUser() {
  return currentUser
}

export async function api<T = any>(path: string, opts: { method?: string; body?: any; form?: FormData } = {}): Promise<T> {
  const headers: Record<string, string> = { 'X-User-Id': currentUser }
  let body: BodyInit | undefined
  if (opts.form) body = opts.form
  else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }
  const res = await fetch(path, { method: opts.method || (body ? 'POST' : 'GET'), headers, body })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error((data as any).detail || `Request failed (${res.status})`)
  return data as T
}

export const inr = (n: number) => '₹' + Math.round(n).toLocaleString('en-IN')

export const fmtTime = (iso?: string | null) => {
  if (!iso) return '-'
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
  return d.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
}
