import { useState, type FormEvent } from 'react'
import { api } from '../api'
import { CloseIcon, CarIcon, CheckCircleIcon, UserIcon } from './Icons'

// ---------------------------------------------------------------- Report Accident Modal
interface ReportAccidentModalProps {
  isOpen: boolean
  onClose: () => void
  onCaseCreated: (caseData: any) => void
}

export function ReportAccidentModal({ isOpen, onClose, onCaseCreated }: ReportAccidentModalProps) {
  const [form, setForm] = useState(() => ({
    incident_at: new Date().toISOString().slice(0, 16),
    approximate_location: 'Hosur Road, Bengaluru',
    victim_display_name: 'Ravi Kumar',
    hospital_name: 'Sample City Hospital',
    life_threatening: false,
  }))
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  if (!isOpen) return null

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      const res = await api('/api/cases', {
        body: {
          ...form,
          incident_at: new Date(form.incident_at).toISOString(),
        },
      })
      onCaseCreated(res)
      onClose()
    } catch (e: any) {
      setErr(e.message || 'Failed to create case')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-navy-950 text-white p-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-accent-500 text-white flex items-center justify-center">
              <span className="text-lg">🚨</span>
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Report an Accident</h3>
              <p className="text-xs text-slate-300">PM-RAHAT cashless case intake & coordinator setup</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition">
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Warning Callout */}
        <div className="bg-red-50 border-b border-red-100 p-3.5 flex items-center gap-3 text-xs text-red-700">
          <span className="font-bold uppercase tracking-wider bg-red-600 text-white text-[10px] px-1.5 py-0.5 rounded">Emergency</span>
          <span>For medical or police assistance, call <a href="tel:112" className="underline font-bold">112</a> immediately.</span>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Incident Date & Time <span className="text-red-500">*</span>
            </label>
            <input
              type="datetime-local"
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
              value={form.incident_at}
              onChange={(e) => setForm({ ...form, incident_at: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Approximate Incident Location <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Near Silk Board Junction, Bengaluru"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
              value={form.approximate_location}
              onChange={(e) => setForm({ ...form, approximate_location: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Victim Display Name
              </label>
              <input
                type="text"
                placeholder="e.g. Ravi Kumar"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
                value={form.victim_display_name}
                onChange={(e) => setForm({ ...form, victim_display_name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Hospital Admitted To
              </label>
              <input
                type="text"
                placeholder="e.g. Sample City Hospital"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
                value={form.hospital_name}
                onChange={(e) => setForm({ ...form, hospital_name: e.target.value })}
              />
            </div>
          </div>

          <label className="flex items-start gap-2.5 p-3 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer">
            <input
              type="checkbox"
              className="mt-0.5 rounded text-accent-500 focus:ring-accent-500"
              checked={form.life_threatening}
              onChange={(e) => setForm({ ...form, life_threatening: e.target.checked })}
            />
            <div className="text-xs">
              <span className="font-semibold text-slate-800">Doctors stated injuries are life-threatening</span>
              <p className="text-slate-500 mt-0.5">PM-RAHAT grants 48 hours (instead of 24 hours) for police authentication.</p>
            </div>
          </label>

          {err && (
            <div className="text-xs text-red-600 bg-red-50 p-2.5 rounded-lg border border-red-200">
              {err}
            </div>
          )}

          <div className="pt-2 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={busy}
              className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={busy || !form.incident_at || !form.approximate_location}
              className="px-5 py-2 text-sm font-semibold text-white bg-accent-500 hover:bg-accent-600 rounded-lg shadow transition disabled:opacity-50"
            >
              {busy ? 'Creating via MCP…' : 'Create Case & Open Dashboard'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- Vehicles Modal
export function VehiclesModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden">
        <div className="bg-navy-950 text-white p-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-blue-500/20 text-blue-400 border border-blue-400/30 flex items-center justify-center">
              <CarIcon className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Registered Vehicles</h3>
              <p className="text-xs text-slate-300">Vehicle profiles & insurance preparedness</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition">
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-blue-700 bg-blue-100 px-2 py-0.5 rounded">Primary Car</span>
                <h4 className="text-base font-bold text-navy-900 mt-1">Honda City ZX (2024)</h4>
                <div className="text-sm font-mono text-slate-700 mt-0.5">KA-01-MJ-2024</div>
              </div>
              <div className="text-right">
                <span className="chip bg-green-100 text-green-800 font-semibold text-xs">Active Policy</span>
                <div className="text-xs text-slate-500 mt-1">Tata AIG General</div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-blue-100 grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-slate-500">Policy Number:</span>
                <div className="font-medium text-slate-800">#POL-99283401-2026</div>
              </div>
              <div>
                <span className="text-slate-500">Policy Validity:</span>
                <div className="font-medium text-slate-800">15 Dec 2026 (28 days left)</div>
              </div>
              <div>
                <span className="text-slate-500">PM-RAHAT Status:</span>
                <div className="font-semibold text-emerald-700 flex items-center gap-1">
                  <CheckCircleIcon className="h-3.5 w-3.5" /> Cashless Eligible
                </div>
              </div>
              <div>
                <span className="text-slate-500">Emergency Roadside:</span>
                <div className="font-medium text-slate-800">1800-266-7780</div>
              </div>
            </div>
          </div>

          <div className="p-3 rounded-xl border border-dashed border-slate-300 text-center text-xs text-slate-500">
            Demo vehicle linked to Priya Sharma's account.
          </div>

          <div className="flex justify-end">
            <button onClick={onClose} className="btn-primary">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- Profile Modal
export function ProfileModal({ isOpen, onClose, userName = "Priya Sharma", roleLabel = "Family Coordinator" }: { isOpen: boolean; onClose: () => void; userName?: string; roleLabel?: string }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden">
        <div className="bg-navy-950 text-white p-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-accent-500/20 text-accent-400 border border-accent-500/30 flex items-center justify-center">
              <UserIcon className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">My Profile</h3>
              <p className="text-xs text-slate-300">Family coordinator profile</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition">
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="flex items-center gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
            <div className="h-14 w-14 rounded-full bg-navy-800 text-white font-bold text-xl flex items-center justify-center">
              {userName[0]}
            </div>
            <div>
              <h4 className="text-base font-bold text-navy-900">{userName}</h4>
              <p className="text-xs text-slate-500">{roleLabel}</p>
              <div className="mt-1 flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                <span className="text-xs font-medium text-emerald-700">Verified Member</span>
              </div>
            </div>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Case Permissions:</span>
              <span className="font-semibold text-slate-800">Coordinator (Approve & Assign)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Linked Co-Coordinator:</span>
              <span className="font-semibold text-slate-800">Arjun Sharma (Brother)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500">Emergency Contact:</span>
              <span className="font-semibold text-slate-800">+91 98450 12345</span>
            </div>
          </div>

          <div className="flex justify-end">
            <button onClick={onClose} className="btn-primary">
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- Notifications Modal
export function NotificationsModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  if (!isOpen) return null

  const notifications = [
    {
      title: "Watcher Alert: 7-Day Cover Window",
      msg: "PM-RAHAT cashless cover applies for a maximum of 7 days from the accident date.",
      time: "10 mins ago",
      type: "alert",
    },
    {
      title: "Document Extracted: Hospital Bill",
      msg: "Bill #HOSP-9921 analysed through MCP with ₹1,24,000 total. Marked as Needs Review.",
      time: "25 mins ago",
      type: "info",
    },
    {
      title: "Reminder: Insurance Renewal",
      msg: "Tata AIG Comprehensive Policy for KA-01-MJ-2024 is due in 28 days.",
      time: "Yesterday",
      type: "reminder",
    },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden">
        <div className="bg-navy-950 text-white p-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-base">🔔</span>
            <h3 className="text-sm font-bold text-white">Notifications & Alerts</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition">
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="p-4 space-y-2.5 max-h-[70vh] overflow-y-auto">
          {notifications.map((n, i) => (
            <div key={i} className="p-3 rounded-xl border border-slate-200 hover:border-navy-700 bg-slate-50/60 transition">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-navy-900">{n.title}</span>
                <span className="text-[10px] text-slate-400">{n.time}</span>
              </div>
              <p className="text-xs text-slate-600 mt-1">{n.msg}</p>
            </div>
          ))}
        </div>

        <div className="p-3 bg-slate-50 border-t border-slate-200 text-right">
          <button onClick={onClose} className="btn-ghost text-xs">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
