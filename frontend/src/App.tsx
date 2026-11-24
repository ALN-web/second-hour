import { useCallback, useEffect, useState } from 'react'
import { api, getUser, setUser, fmtTime } from './api'
import { Dashboard, Chat, Documents, Tasks, ReportView, McpPanel } from './Views'

type User = { user_id: string; name: string; role_label: string }
type CaseRow = { case_id: string; case_number: string; victim_display_name?: string; hospital_name?: string; incident_at: string }

const TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'chat', label: 'Agent' },
  { id: 'documents', label: 'Documents' },
  { id: 'tasks', label: 'Tasks & timeline' },
  { id: 'report', label: 'Report' },
  { id: 'mcp', label: 'MCP' },
] as const
type Tab = (typeof TABS)[number]['id']

function Banner() {
  return (
    <div className="bg-accent-500 text-white text-xs sm:text-sm text-center px-3 py-1.5 font-medium" role="alert">
      Second Hour is not an emergency service. In an emergency, call <a className="underline font-bold" href="tel:112">112</a>.
    </div>
  )
}

function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [users, setUsers] = useState<User[]>([])
  useEffect(() => { api<User[]>('/api/users').then(setUsers).catch(() => {}) }, [])
  return (
    <div className="max-w-md mx-auto px-4 py-12">
      <div className="text-center mb-8">
        <div className="text-4xl font-bold text-navy-800">Second Hour</div>
        <p className="text-slate-600 mt-2">One calm workspace for your family after a road accident.</p>
      </div>
      <div className="card space-y-3">
        <div className="text-sm font-semibold text-slate-700">Continue as (demo users)</div>
        {users.filter(u => u.user_id !== 'u_outsider').map(u => (
          <button key={u.user_id} onClick={() => { setUser(u.user_id); onLogin(u) }}
            className="w-full flex items-center gap-3 rounded-lg border border-slate-200 p-3 hover:border-navy-700 hover:bg-slate-50 text-left">
            <div className="h-10 w-10 rounded-full bg-navy-800 text-white grid place-items-center font-bold">{u.name[0]}</div>
            <div><div className="font-medium">{u.name}</div><div className="text-xs text-slate-500">{u.role_label}</div></div>
          </button>
        ))}
        {users.length === 0 && <div className="text-sm text-red-600">Cannot reach the agent host on :8000. Is it running?</div>}
      </div>
      <p className="text-xs text-slate-500 mt-4 text-center">Synthetic demo data only.</p>
    </div>
  )
}

function CaseList({ user, onOpen }: { user: User; onOpen: (c: CaseRow) => void }) {
  const [cases, setCases] = useState<CaseRow[]>([])
  const [show, setShow] = useState(false)
  const [form, setForm] = useState({ incident_at: '', approximate_location: '', victim_display_name: '', hospital_name: '', life_threatening: false })
  const [err, setErr] = useState('')
  const load = useCallback(() => { api<CaseRow[]>('/api/cases').then(setCases) }, [])
  useEffect(load, [load])
  const create = async () => {
    setErr('')
    try {
      await api('/api/cases', { body: { ...form, incident_at: new Date(form.incident_at).toISOString() } })
      setShow(false); load()
    } catch (e: any) { setErr(e.message) }
  }
  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-navy-800">Your cases, {user.name}</h1>
        <button className="btn-ghost" onClick={() => setShow(s => !s)}>+ New case</button>
      </div>
      {show && (
        <div className="card space-y-2">
          <label className="text-xs text-slate-600">Incident date & time</label>
          <input className="input" type="datetime-local" value={form.incident_at} onChange={e => setForm({ ...form, incident_at: e.target.value })} />
          <input className="input" placeholder="Approximate location" value={form.approximate_location} onChange={e => setForm({ ...form, approximate_location: e.target.value })} />
          <input className="input" placeholder="Victim display name (optional)" value={form.victim_display_name} onChange={e => setForm({ ...form, victim_display_name: e.target.value })} />
          <input className="input" placeholder="Hospital (optional)" value={form.hospital_name} onChange={e => setForm({ ...form, hospital_name: e.target.value })} />
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.life_threatening} onChange={e => setForm({ ...form, life_threatening: e.target.checked })} /> Doctors said it is life-threatening</label>
          {err && <div className="text-sm text-red-600">{err}</div>}
          <button className="btn-primary" onClick={create} disabled={!form.incident_at || !form.approximate_location}>Create case (via MCP)</button>
        </div>
      )}
      {cases.map(c => (
        <button key={c.case_id} onClick={() => onOpen(c)} className="card w-full text-left hover:border-navy-700">
          <div className="flex justify-between"><span className="font-semibold text-navy-800">{c.case_number}</span><span className="text-xs text-slate-500">Incident {fmtTime(c.incident_at)}</span></div>
          <div className="text-sm text-slate-600 mt-1">{c.victim_display_name || 'Unnamed'} · {c.hospital_name || 'Hospital not set'}</div>
        </button>
      ))}
      {cases.length === 0 && <div className="text-sm text-slate-500">No cases yet.</div>}
    </div>
  )
}

export default function App() {
  const [user, setU] = useState<User | null>(null)
  const [kase, setKase] = useState<CaseRow | null>(null)
  const [tab, setTab] = useState<Tab>('dashboard')
  const [tick, setTick] = useState(0)
  const refresh = () => setTick(t => t + 1)

  useEffect(() => {
    // Deep link for demos: ?as=u_priya&case=case_demo&tab=chat
    const q = new URLSearchParams(location.search)
    if (q.get('as')) setUser(q.get('as')!)
    const id = getUser()
    if (!id) return
    api<User[]>('/api/users').then(us => {
      const u = us.find(x => x.user_id === id)
      if (!u) return
      setU(u)
      const want = q.get('case')
      if (want) api<CaseRow[]>('/api/cases').then(cs => {
        const c = cs.find(x => x.case_id === want)
        if (c) { setKase(c); const t = q.get('tab'); if (t && TABS.some(x => x.id === t)) setTab(t as Tab) }
      })
    }).catch(() => {})
  }, [])

  const logout = () => { setUser(''); setU(null); setKase(null) }

  return (
    <div className="min-h-screen flex flex-col">
      <Banner />
      <header className="bg-navy-900 text-white">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
          <button className="font-bold text-lg tracking-tight" onClick={() => setKase(null)}>Second Hour</button>
          {kase && <span className="chip bg-navy-700 text-white">{kase.case_number}</span>}
          <div className="flex-1" />
          {user && <span className="text-sm text-slate-300">{user.name}</span>}
          {user && <button className="text-xs underline text-slate-300" onClick={logout}>Switch user</button>}
        </div>
        {kase && (
          <nav className="max-w-5xl mx-auto px-2 flex gap-1 overflow-x-auto">
            {TABS.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`px-3 py-2 text-sm whitespace-nowrap border-b-2 ${tab === t.id ? 'border-accent-500 text-white' : 'border-transparent text-slate-300 hover:text-white'}`}>
                {t.label}
              </button>
            ))}
          </nav>
        )}
      </header>
      <main className="flex-1">
        {!user && <Login onLogin={setU} />}
        {user && !kase && <CaseList user={user} onOpen={c => { setKase(c); setTab('dashboard') }} />}
        {user && kase && (
          <div className="max-w-5xl mx-auto px-4 py-5">
            {tab === 'dashboard' && <Dashboard caseId={kase.case_id} tick={tick} refresh={refresh} goChat={() => setTab('chat')} />}
            {tab === 'chat' && <Chat caseId={kase.case_id} refresh={refresh} />}
            {tab === 'documents' && <Documents caseId={kase.case_id} refresh={refresh} />}
            {tab === 'tasks' && <Tasks caseId={kase.case_id} tick={tick} refresh={refresh} />}
            {tab === 'report' && <ReportView caseId={kase.case_id} />}
            {tab === 'mcp' && <McpPanel caseId={kase.case_id} />}
          </div>
        )}
      </main>
      <footer className="text-center text-xs text-slate-500 py-4">Prepared by Second Hour · not legal advice · synthetic demo data</footer>
    </div>
  )
}
