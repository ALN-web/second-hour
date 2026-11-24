import { useCallback, useEffect, useRef, useState } from 'react'
import { api, fmtTime, getUser, inr } from './api'

/* ------------------------------------------------------------------ shared */

type Action = { action_id: string; tool: string; preview: string; status: string; result?: any }

export function ActionCard({ a, onDone }: { a: Action; onDone?: () => void }) {
  const [act, setAct] = useState(a)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  useEffect(() => setAct(a), [a])
  const go = async (verb: 'approve' | 'reject') => {
    setBusy(true); setErr('')
    try { setAct(await api(`/api/actions/${act.action_id}/${verb}`, { method: 'POST' })); onDone?.() }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  const color = act.status === 'approved' ? 'border-green-300 bg-green-50' : act.status === 'rejected' ? 'border-slate-200 bg-slate-50 opacity-70' : act.status === 'failed' ? 'border-red-300 bg-red-50' : 'border-accent-500 bg-orange-50'
  return (
    <div className={`rounded-lg border-2 p-3 ${color}`}>
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
        <span>Proposed action</span><code className="chip bg-white border border-slate-200 normal-case">{act.tool}</code>
        <span className="flex-1" /><span className="font-semibold">{act.status}</span>
      </div>
      <div className="mt-1 text-sm font-medium text-slate-800">{act.preview}</div>
      {act.status === 'proposed' && (
        <div className="mt-2 flex gap-2">
          <button className="btn-accent" disabled={busy} onClick={() => go('approve')}>Approve</button>
          <button className="btn-ghost" disabled={busy} onClick={() => go('reject')}>Reject</button>
        </div>
      )}
      {act.status === 'approved' && act.result?.download_url && (
        <a className="text-sm underline text-navy-800 mt-1 inline-block" href={`${act.result.download_url}?uid=${getUser()}`} target="_blank">Download PDF</a>
      )}
      {act.status === 'approved' && act.result?.task_id && <div className="text-xs text-green-700 mt-1">Task created via MCP ({act.result.task_id})</div>}
      {act.status === 'failed' && <div className="text-xs text-red-700 mt-1">{act.result?.text}</div>}
      {err && <div className="text-xs text-red-700 mt-1">{err}</div>}
    </div>
  )
}

function Bar({ pct, warn }: { pct: number; warn: boolean }) {
  return (
    <div className="h-3 rounded-full bg-slate-200 overflow-hidden">
      <div className={`h-full ${warn ? 'bg-accent-500' : 'bg-navy-700'}`} style={{ width: `${Math.min(100, pct)}%` }} />
    </div>
  )
}

function Md({ text }: { text: string }) {
  // tiny, safe markdown: **bold**, _italic_, line breaks, bullets
  const html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|\s)_(.+?)_(?=\s|$)/g, '$1<em>$2</em>')
    .replace(/\[(\d+)\]/g, '<sup class="text-navy-700 font-semibold">[$1]</sup>')
  return <div className="whitespace-pre-wrap text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: html }} />
}

/* ------------------------------------------------------------------ dashboard */

export function Dashboard({ caseId, tick, refresh, goChat }: { caseId: string; tick: number; refresh: () => void; goChat: () => void }) {
  const [s, setS] = useState<any>(null)
  const [cards, setCards] = useState<Action[]>([])
  const [err, setErr] = useState('')
  const load = useCallback(() => { api(`/api/cases/${caseId}/summary`).then(setS).catch(e => setErr(e.message)) }, [caseId])
  useEffect(load, [load, tick])
  if (err) return <div className="card text-red-700">{err}</div>
  if (!s) return <div className="text-slate-500">Loading…</div>
  const cw = s.milestones.cover_window, ca = s.milestones.cover_amount, pa = s.milestones.police_authentication

  const setPolice = async (status: string) => { await api(`/api/cases/${caseId}/police-status`, { body: { status } }); load(); refresh() }
  const clock = async (hours: number) => { await api(`/api/cases/${caseId}/clock`, { body: { hours } }); load(); refresh() }
  const proposeTask = async (al: any) => {
    const card = await api<Action>(`/api/cases/${caseId}/propose`, { body: { tool: 'create_followup_task', arguments: { title: al.suggested_task.title, priority: al.suggested_task.priority, description: al.message } } })
    setCards(c => [card, ...c])
  }

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 className="text-lg font-semibold text-navy-800">{s.victim_display_name || 'Case'} · {s.case_number}</h2>
          <span className="text-sm text-slate-500">{s.hospital_name} · {s.approximate_location}</span>
        </div>
        <div className="text-xs text-slate-500 mt-1">Incident {fmtTime(s.incident_at)} IST · Case clock {fmtTime(s.clock_now)} IST{s.demo_clock_offset_hours ? <span className="chip bg-orange-100 text-orange-800 ml-2">demo clock +{s.demo_clock_offset_hours}h</span> : null}</div>
      </div>

      {s.alerts.length > 0 && (
        <div className="space-y-2">
          {s.alerts.map((al: any) => (
            <div key={al.id} className="rounded-xl border-l-4 border-accent-500 bg-orange-50 p-4">
              <div className="flex items-center gap-2"><span className="chip bg-accent-500 text-white">Watcher alert</span><span className="font-semibold text-slate-800">{al.title}</span></div>
              <p className="text-sm text-slate-700 mt-1">{al.message}</p>
              <div className="text-xs text-slate-500 mt-1">Source: <a className="underline" href={al.source.url} target="_blank">{al.source.title}</a></div>
              <button className="btn-primary mt-2" onClick={() => proposeTask(al)}>Propose task: {al.suggested_task.title}</button>
            </div>
          ))}
        </div>
      )}
      {cards.map(c => <ActionCard key={c.action_id} a={c} onDone={() => { load(); refresh() }} />)}

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="card">
          <div className="text-xs uppercase text-slate-500 tracking-wide">PM-RAHAT 7-day window</div>
          <div className="text-3xl font-bold text-navy-800 mt-1">Day {cw.day} <span className="text-base font-normal text-slate-500">of {cw.of}</span></div>
          <div className="mt-2"><Bar pct={(cw.day / cw.of) * 100} warn={cw.day >= 6} /></div>
          <div className="text-xs text-slate-500 mt-2">Counted from the accident date. Window ends {fmtTime(cw.window_ends_at)} IST.</div>
        </div>
        <div className="card">
          <div className="text-xs uppercase text-slate-500 tracking-wide">Cover tracker (confirmed bills)</div>
          <div className="text-3xl font-bold text-navy-800 mt-1">{inr(ca.confirmed_bills_inr)} <span className="text-base font-normal text-slate-500">of {inr(ca.cover_limit_inr)}</span></div>
          <div className="mt-2"><Bar pct={ca.percent_used} warn={ca.percent_used >= 80} /></div>
          <div className="text-xs text-slate-500 mt-2">{ca.note}</div>
        </div>
        <div className="card">
          <div className="text-xs uppercase text-slate-500 tracking-wide">Police authentication status</div>
          <select className="input mt-2" value={pa.status} onChange={e => setPolice(e.target.value)}>
            <option value="not_started">Not started</option>
            <option value="requested_by_hospital">Requested by hospital</option>
            <option value="confirmed">Confirmed</option>
            <option value="not_confirmed">Not confirmed</option>
          </select>
          <div className="text-xs text-slate-500 mt-2"><span className="chip bg-slate-100 text-slate-600">user-provided, unverified</span> Updated {fmtTime(pa.updated_at)} IST. The hospital raises this with police; it is not a family deadline.</div>
        </div>
        <div className="card">
          <div className="text-xs uppercase text-slate-500 tracking-wide">At a glance</div>
          <div className="grid grid-cols-3 gap-2 mt-2 text-center">
            <div><div className="text-2xl font-bold text-navy-800">{s.document_counts.total}</div><div className="text-xs text-slate-500">documents</div></div>
            <div><div className="text-2xl font-bold text-accent-600">{s.document_counts.fields_needing_review}</div><div className="text-xs text-slate-500">fields to review</div></div>
            <div><div className="text-2xl font-bold text-navy-800">{s.open_tasks.length}</div><div className="text-xs text-slate-500">open tasks</div></div>
          </div>
          <div className="text-xs text-slate-500 mt-3">Members: {s.members.map((m: any) => m.name).join(', ')}</div>
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between"><div className="font-semibold text-navy-800">Next steps</div><button className="btn-ghost" onClick={goChat}>Ask the agent</button></div>
        <ul className="mt-2 space-y-1 text-sm list-disc pl-5">{s.next_steps.length ? s.next_steps.map((n: string) => <li key={n}>{n}</li>) : <li>Upload hospital documents to get started.</li>}</ul>
      </div>

      <div className="card border-dashed">
        <div className="text-xs uppercase text-slate-500 tracking-wide">Demo mode · advance clock</div>
        <div className="flex flex-wrap gap-2 mt-2">
          <button className="btn-ghost" onClick={() => clock(6)}>+6 h</button>
          <button className="btn-ghost" onClick={() => clock(25)}>+25 h</button>
          <button className="btn-ghost" onClick={() => clock(24 * 4)}>+4 days</button>
          <button className="btn-ghost" onClick={() => clock(0)}>Reset</button>
        </div>
        <div className="text-xs text-slate-500 mt-2">Moves this case's clock forward so the deterministic watchers can be shown live (same as the <code>now</code> parameter of the MCP tool).</div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ voice (ElevenLabs) */

let ttsEnabled: Promise<boolean> | null = null
function useTts() {
  const [on, setOn] = useState(false)
  useEffect(() => {
    ttsEnabled ??= api<{ tts: boolean }>('/api/config').then(c => c.tts).catch(() => false)
    ttsEnabled.then(setOn)
  }, [])
  return on
}

function ListenButton({ text }: { text: string }) {
  const [state, setState] = useState<'idle' | 'loading' | 'playing' | 'error'>('idle')
  const audio = useRef<HTMLAudioElement | null>(null)
  const play = async () => {
    if (state === 'playing') { audio.current?.pause(); setState('idle'); return }
    setState('loading')
    try {
      const res = await fetch('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-User-Id': getUser() }, body: JSON.stringify({ text }) })
      if (!res.ok) throw new Error()
      const url = URL.createObjectURL(await res.blob())
      audio.current = new Audio(url)
      audio.current.onended = () => setState('idle')
      await audio.current.play()
      setState('playing')
    } catch { setState('error') }
  }
  return (
    <button onClick={play} className="chip bg-white border border-slate-300 text-slate-700 hover:border-navy-700 py-1" aria-label="Read this reply aloud">
      {state === 'loading' ? 'Loading voice…' : state === 'playing' ? '■ Stop' : state === 'error' ? 'Voice unavailable' : '▶ Listen'}
      <span className="text-[10px] text-slate-400 ml-1">ElevenLabs</span>
    </button>
  )
}

/* ------------------------------------------------------------------ chat */

const SUGGESTIONS = [
  'What does PM-RAHAT cover and for how long?',
  'Who starts police authentication, and is there anything I need to do?',
  'Which documents are we still missing?',
  'Create a task for the alert you found',
  'Prepare the case report PDF',
]

export function Chat({ caseId, refresh }: { caseId: string; refresh: () => void }) {
  const [msgs, setMsgs] = useState<any[]>([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const end = useRef<HTMLDivElement>(null)
  const box = useRef<HTMLDivElement>(null)
  const tts = useTts()
  const load = useCallback(() => { api<any[]>(`/api/cases/${caseId}/chat`).then(setMsgs) }, [caseId])
  useEffect(load, [load])
  useEffect(() => { const b = box.current; if (b) b.scrollTo({ top: b.scrollHeight, behavior: 'smooth' }) }, [msgs, busy])

  const send = async (m: string) => {
    if (!m.trim()) return
    setBusy(true); setErr(''); setText('')
    setMsgs(x => [...x, { id: 'tmp', role: 'user', content: m }])
    try { await api(`/api/cases/${caseId}/chat`, { body: { message: m } }); load(); refresh() }
    catch (e: any) { setErr(e.message); load() } finally { setBusy(false) }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-190px)] min-h-[420px]">
      <div className="flex items-center gap-2 mb-2 text-xs"><span className="chip bg-navy-800 text-white">Case context loaded</span><span className="text-slate-500">Tools discovered live from the MCP server · write actions need your approval</span></div>
      <div ref={box} className="flex-1 overflow-y-auto space-y-3 pr-1">
        {msgs.length === 0 && <div className="card text-sm text-slate-600">Ask about PM-RAHAT, your documents or next steps. Answers about the scheme come only from official sources, with citations.</div>}
        {msgs.map((m, i) => (
          <div key={m.id + '-' + i} className={m.role === 'user' ? 'flex justify-end' : ''}>
            <div className={m.role === 'user' ? 'max-w-[85%] rounded-2xl rounded-br-sm bg-navy-800 text-white px-4 py-2' : 'max-w-[95%] card space-y-2'}>
              {m.role === 'user' && m.user && <div className="text-[10px] text-slate-300">{m.user}</div>}
              {m.role === 'assistant' && m.mode === 'offline' && <span className="chip bg-slate-100 text-slate-500 mr-1" title="No ANTHROPIC_API_KEY set: deterministic agent, still via MCP">offline agent</span>}
              {m.new_alerts?.length > 0 && <div className="text-xs chip bg-orange-100 text-orange-800">{m.new_alerts.length} new watcher alert(s)</div>}
              <Md text={m.content} />
              {tts && m.role === 'assistant' && <ListenButton text={m.content} />}
              {m.citations?.length > 0 && (
                <div className="border-t border-slate-100 pt-2 space-y-1">
                  <div className="text-xs font-semibold text-slate-500">Sources</div>
                  {m.citations.map((c: any) => (
                    <div key={c.n} className="text-xs text-slate-600"><span className="font-semibold text-navy-700">[{c.n}]</span> <a href={c.url} target="_blank" className="underline">{c.title}</a> · {c.date}{c.section ? ` · ${c.section}` : ''}{c.verification && c.verification !== 'verified' ? <span className="chip bg-yellow-100 text-yellow-800 ml-1">{c.verification}</span> : null}</div>
                  ))}
                </div>
              )}
              {m.actions?.map((a: Action) => <ActionCard key={a.action_id} a={a} onDone={refresh} />)}
              {m.tool_trace?.length > 0 && (
                <div className="flex flex-wrap gap-1 pt-1">
                  {m.tool_trace.map((t: any, j: number) => <span key={j} className={`chip ${t.state === 'proposed' ? 'bg-orange-100 text-orange-800' : t.state === 'error' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'}`}>MCP · {t.tool}</span>)}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="card text-sm text-slate-500 animate-pulse">Second Hour is checking the case via MCP…</div>}
        <div ref={end} />
      </div>
      {err && <div className="text-sm text-red-700 mt-2">{err}</div>}
      <div className="flex gap-2 overflow-x-auto py-2">
        {SUGGESTIONS.map(s => <button key={s} className="chip bg-white border border-slate-300 text-slate-700 whitespace-nowrap py-1 hover:border-navy-700" onClick={() => send(s)} disabled={busy}>{s}</button>)}
      </div>
      <form className="flex gap-2" onSubmit={e => { e.preventDefault(); send(text) }}>
        <input className="input" placeholder="Ask Second Hour…" value={text} onChange={e => setText(e.target.value)} disabled={busy} />
        <button className="btn-accent" disabled={busy || !text.trim()}>Send</button>
      </form>
    </div>
  )
}

/* ------------------------------------------------------------------ documents */

const CATS = ['medical_report', 'hospital_bill', 'police_document', 'vehicle_document', 'insurance_policy', 'accident_photo', 'other']

function FieldRow({ caseId, f, onChange }: { caseId: string; f: any; onChange: () => void }) {
  const [edit, setEdit] = useState(false)
  const [val, setVal] = useState(f.value)
  const save = async (confirm: boolean) => {
    await api(`/api/cases/${caseId}/fields/${f.field_id}`, { body: { value: edit ? val : null, confirm } })
    setEdit(false); onChange()
  }
  return (
    <div className="flex flex-wrap items-center gap-2 py-1.5 border-b border-slate-100 last:border-0 text-sm">
      <div className="w-36 text-slate-500">{f.name.replace(/_/g, ' ')}</div>
      <div className="flex-1 min-w-[140px]">{edit ? <input className="input py-1" value={val} onChange={e => setVal(e.target.value)} /> : <span className="font-medium">{f.name === 'total_amount' && /^\d+$/.test(f.value) ? inr(Number(f.value)) : f.value}</span>}</div>
      <span className="text-xs text-slate-500 w-16">{Math.round(f.confidence * 100)}% conf.</span>
      {f.status === 'confirmed' ? <span className="chip bg-green-100 text-green-800">Confirmed</span> : <span className="chip bg-yellow-100 text-yellow-800">Needs review</span>}
      {edit ? <button className="btn-primary py-1" onClick={() => save(true)}>Save & confirm</button> : <>
        {f.status !== 'confirmed' && <button className="btn-primary py-1" onClick={() => save(false || true)}>Confirm</button>}
        <button className="btn-ghost py-1" onClick={() => setEdit(true)}>Edit</button></>}
    </div>
  )
}

export function Documents({ caseId, refresh }: { caseId: string; refresh: () => void }) {
  const [docs, setDocs] = useState<any[]>([])
  const [check, setCheck] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const load = useCallback(() => {
    api<any[]>(`/api/cases/${caseId}/documents`).then(setDocs)
    api(`/api/cases/${caseId}/checklist`).then(setCheck)
  }, [caseId])
  useEffect(load, [load])
  const upload = async (files: FileList | null) => {
    if (!files) return
    setBusy(true); setErr('')
    try {
      for (const file of Array.from(files)) { const fd = new FormData(); fd.append('file', file); await api(`/api/cases/${caseId}/documents`, { form: fd }) }
    } catch (e: any) { setErr(e.message) } finally { setBusy(false); load(); refresh() }
  }
  const changed = () => { load(); refresh() }
  return (
    <div className="grid lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 space-y-4">
        <label className="card border-dashed border-2 flex flex-col items-center justify-center py-8 cursor-pointer hover:border-navy-700">
          <input type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.webp" className="hidden" onChange={e => upload(e.target.files)} disabled={busy} />
          <div className="font-semibold text-navy-800">{busy ? 'Uploading & analysing via MCP…' : 'Upload bills, reports, police papers'}</div>
          <div className="text-xs text-slate-500 mt-1">PDF or photo · stored privately with a SHA-256 hash · try <code>demo_assets/</code></div>
        </label>
        {err && <div className="text-sm text-red-700">{err}</div>}
        {docs.map(d => (
          <div key={d.document_id} className="card">
            <div className="flex flex-wrap items-center gap-2">
              <div className="font-semibold text-slate-800 flex-1">{d.filename}</div>
              <select className="input w-auto py-1" value={d.category || ''} onChange={async e => { await api(`/api/cases/${caseId}/documents/${d.document_id}/category`, { body: { category: e.target.value } }); changed() }}>
                <option value="" disabled>unclassified</option>
                {CATS.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
              </select>
              {d.category_confidence != null && <span className="text-xs text-slate-500">{Math.round(d.category_confidence * 100)}%</span>}
            </div>
            <div className="text-[11px] text-slate-400 mt-1 font-mono">sha256 {d.sha256.slice(0, 20)}… · {d.analysis_status}</div>
            <div className="mt-2">{d.fields.length ? d.fields.map((f: any) => <FieldRow key={f.field_id} caseId={caseId} f={f} onChange={changed} />) : <div className="text-sm text-slate-500">No fields extracted.</div>}</div>
          </div>
        ))}
      </div>
      <div className="card h-fit">
        <div className="font-semibold text-navy-800">Document checklist</div>
        <div className="text-xs text-slate-500 mb-2">{check?.label}</div>
        {check && [...check.missing, ...check.needs_review, ...check.present].map((i: any) => (
          <div key={i.key} className="py-2 border-b border-slate-100 last:border-0">
            <div className="flex items-center gap-2 text-sm"><span className={`chip ${i.status === 'present' ? 'bg-green-100 text-green-800' : i.status === 'missing' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-800'}`}>{i.status.replace('_', ' ')}</span>{i.label}</div>
            <div className="text-xs text-slate-500 mt-0.5">{i.reason}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ tasks + timeline */

export function Tasks({ caseId, tick, refresh }: { caseId: string; tick: number; refresh: () => void }) {
  const [tasks, setTasks] = useState<any[]>([])
  const [tl, setTl] = useState<any[]>([])
  const [members, setMembers] = useState<any[]>([])
  const [err, setErr] = useState('')
  const load = useCallback(() => {
    api<any[]>(`/api/cases/${caseId}/tasks`).then(setTasks)
    api<any[]>(`/api/cases/${caseId}/timeline`).then(setTl)
    api<any>(`/api/cases/${caseId}/summary`).then(s => setMembers(s.members))
  }, [caseId])
  useEffect(load, [load, tick])
  const name = (id: string) => members.find(m => m.user_id === id)?.name
  const assign = async (t: any, member_id: string) => {
    setErr('')
    try { await api(`/api/cases/${caseId}/tasks/${t.task_id}/assign`, { body: { member_id } }); load(); refresh() } catch (e: any) { setErr(e.message) }
  }
  const toggle = async (t: any) => { await api(`/api/cases/${caseId}/tasks/${t.task_id}/status`, { body: { status: t.status === 'open' ? 'done' : 'open' } }); load(); refresh() }
  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div className="space-y-2">
        <div className="font-semibold text-navy-800">Tasks</div>
        {err && <div className="text-sm text-red-700">{err}</div>}
        {tasks.length === 0 && <div className="card text-sm text-slate-500">No tasks yet. Approve a proposed task from the dashboard or the agent.</div>}
        {tasks.map(t => (
          <div key={t.task_id} className={`card ${t.status === 'done' ? 'opacity-60' : ''}`}>
            <div className="flex items-start gap-2">
              <input type="checkbox" className="mt-1" checked={t.status === 'done'} onChange={() => toggle(t)} />
              <div className="flex-1">
                <div className={`font-medium ${t.status === 'done' ? 'line-through' : ''}`}>{t.title}</div>
                {t.description && <div className="text-xs text-slate-500 mt-0.5 line-clamp-2">{t.description}</div>}
                <div className="flex flex-wrap gap-2 items-center mt-2 text-xs">
                  <span className={`chip ${t.priority === 'high' ? 'bg-orange-100 text-orange-800' : 'bg-slate-100 text-slate-600'}`}>{t.priority}</span>
                  {t.due_at && <span className="chip bg-slate-100">due {fmtTime(t.due_at)} · {t.due_source}</span>}
                  <span className="text-slate-500">Assignee:</span>
                  <select className="input w-auto py-0.5 text-xs" value={t.assignee_id || ''} onChange={e => assign(t, e.target.value)}>
                    <option value="" disabled>unassigned</option>
                    {members.map(m => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}
                  </select>
                  {t.assignee_id && <span className="text-slate-500">({name(t.assignee_id)}, via MCP assign_family_task)</span>}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div>
        <div className="font-semibold text-navy-800 mb-2">Timeline</div>
        <ol className="card space-y-3 relative">
          {tl.map((e, i) => (
            <li key={i} className="flex gap-3 text-sm">
              <div className="w-2 h-2 rounded-full bg-navy-700 mt-1.5 shrink-0" />
              <div><div className="text-slate-800">{e.summary}</div><div className="text-xs text-slate-500">{fmtTime(e.at)} IST · {name(e.actor_id) || e.actor_id || 'system'}</div></div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ report */

export function ReportView({ caseId }: { caseId: string }) {
  const [reports, setReports] = useState<any[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const load = useCallback(() => { api<any[]>(`/api/cases/${caseId}/reports`).then(setReports) }, [caseId])
  useEffect(load, [load])
  const gen = async () => {
    setBusy(true); setErr('')
    try { await api(`/api/cases/${caseId}/reports`, { method: 'POST' }); load() } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="max-w-2xl space-y-4">
      <div className="card">
        <div className="font-semibold text-navy-800">Case package (PDF)</div>
        <p className="text-sm text-slate-600 mt-1">Summary, timeline, document index with hashes, extracted fields (confirmed vs needs review), missing items, alerts and a "Prepared by Second Hour, not legal advice" notice. Useful to share with the hospital desk, insurer or a lawyer.</p>
        <button className="btn-accent mt-3" onClick={gen} disabled={busy}>{busy ? 'Generating via MCP…' : 'Generate case package'}</button>
        {err && <div className="text-sm text-red-700 mt-2">{err}</div>}
      </div>
      {reports.map(r => (
        <div key={r.report_id} className="card flex items-center justify-between">
          <div><div className="font-medium text-sm">{r.filename}</div><div className="text-xs text-slate-500">{fmtTime(r.created_at)} IST</div></div>
          <a className="btn-primary" href={`${r.download_url}?uid=${getUser()}`} target="_blank">Download</a>
        </div>
      ))}
    </div>
  )
}

/* ------------------------------------------------------------------ MCP panel */

export function McpPanel({ caseId }: { caseId: string }) {
  const [info, setInfo] = useState<any>(null)
  const [log, setLog] = useState<any[]>([])
  useEffect(() => { api('/api/mcp/info').then(setInfo) }, [])
  useEffect(() => {
    const f = () => api<any[]>(`/api/cases/${caseId}/activity`).then(setLog).catch(() => {})
    f(); const t = setInterval(f, 2500); return () => clearInterval(t)
  }, [caseId])
  const stateColor: Record<string, string> = { auto_read_only: 'bg-slate-100 text-slate-700', proposed: 'bg-orange-100 text-orange-800', approved: 'bg-green-100 text-green-800', rejected: 'bg-slate-200 text-slate-600', error: 'bg-red-100 text-red-700', auto_on_upload: 'bg-blue-100 text-blue-800', user_requested: 'bg-blue-100 text-blue-800' }
  return (
    <div className="grid lg:grid-cols-5 gap-4">
      <div className="lg:col-span-2 space-y-4">
        <div className="card">
          <div className="flex items-center gap-2"><span className={`h-2.5 w-2.5 rounded-full ${info?.connected ? 'bg-green-500' : 'bg-red-500'}`} /><span className="font-semibold text-navy-800">MCP server {info?.connected ? 'connected' : 'not connected'}</span></div>
          <div className="text-xs text-slate-500 mt-1 font-mono">{info?.url} · Streamable HTTP</div>
          {info?.server && <div className="text-xs text-slate-500">{info.server.name} {info.server.version} · protocol {info.protocol_version}</div>}
          {info?.error && <div className="text-xs text-red-700 mt-1">{info.error}</div>}
          <div className="text-xs text-slate-600 mt-2">Connect a second host: <code>npx @modelcontextprotocol/inspector</code> → Streamable HTTP → <code>http://localhost:8001/mcp</code></div>
        </div>
        <div className="card">
          <div className="font-semibold text-navy-800 mb-2">Tools ({info?.tools?.length ?? 0})</div>
          {info?.tools?.map((t: any) => (
            <div key={t.name} className="py-1.5 border-b border-slate-100 last:border-0">
              <div className="flex items-center gap-2"><code className="text-sm text-navy-800">{t.name}</code>{t.requires_approval ? <span className="chip bg-orange-100 text-orange-800">needs approval</span> : t.read_only ? <span className="chip bg-slate-100 text-slate-600">read-only</span> : <span className="chip bg-blue-100 text-blue-800">auto write</span>}</div>
              <div className="text-xs text-slate-500">{t.description}</div>
            </div>
          ))}
        </div>
        <div className="card text-sm">
          <div className="font-semibold text-navy-800 mb-1">Resources</div>
          {info?.resources?.map((r: string) => <div key={r} className="font-mono text-xs text-slate-600">{r}</div>)}
          <div className="font-semibold text-navy-800 mt-3 mb-1">Prompts</div>
          {info?.prompts?.map((p: string) => <div key={p} className="font-mono text-xs text-slate-600">{p}</div>)}
        </div>
      </div>
      <div className="lg:col-span-3 card">
        <div className="flex items-center gap-2 mb-2"><span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" /><span className="font-semibold text-navy-800">Live MCP activity</span><span className="text-xs text-slate-500">(audit log, refreshes every 2.5 s)</span></div>
        <div className="space-y-2 max-h-[70vh] overflow-y-auto">
          {log.map(l => (
            <div key={l.id} className="text-xs border-b border-slate-100 pb-2">
              <div className="flex items-center gap-2"><code className="font-semibold text-navy-800">{l.tool}</code><span className={`chip ${stateColor[l.approval_state] || 'bg-slate-100'}`}>{l.approval_state}</span><span className="flex-1" /><span className="text-slate-400">{fmtTime(l.at)} · {l.actor_id}</span></div>
              <div className="text-slate-600 mt-0.5">→ {l.result_summary}</div>
              <div className="font-mono text-[10px] text-slate-400 truncate">{JSON.stringify(l.arguments)}</div>
            </div>
          ))}
          {log.length === 0 && <div className="text-sm text-slate-500">No MCP calls yet.</div>}
        </div>
      </div>
    </div>
  )
}
