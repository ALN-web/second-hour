import { useState } from 'react'
import type { HospitalInfo, PMRahatInfo } from '../types'
import { inr, fmtTime, api } from '../../api'

interface HospitalTabProps {
  caseId: string
  hospitalPmrahat: {
    hospital: HospitalInfo
    pmrahat: PMRahatInfo
  }
  onRefresh: () => void
}

export function HospitalTab({
  caseId,
  hospitalPmrahat,
  onRefresh,
}: HospitalTabProps) {
  const { hospital: h, pmrahat: p } = hospitalPmrahat
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    hospital_name: h.name || '',
    hospital_address: h.address || '',
    hospital_contact: h.contact || '',
    treating_doctor: h.treating_doctor || '',
    hospital_treatment_status: h.treatment_status || '',
  })
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await api(`/api/cases/${caseId}/section`, {
        method: 'PATCH',
        body: {
          section: 'hospital',
          data: form,
        },
      })
      setEditing(false)
      onRefresh()
    } catch (e) {
      console.error('Failed to update hospital details:', e)
    } finally {
      setSaving(false)
    }
  }

  const remaining = Math.max(0, p.cover_limit_inr - p.confirmed_bills_inr)

  return (
    <div className="space-y-6">
      {/* PM-RAHAT Cashless Banner */}
      <div className="card p-6 bg-gradient-to-r from-navy-950 via-navy-900 to-navy-950 text-white rounded-2xl shadow-md border border-navy-800 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-orange-500/20 border border-orange-500/30 flex items-center justify-center text-2xl">
              🛡️
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-accent-500 tracking-wider uppercase">
                  Government Scheme Assistance
                </span>
                <span className="chip bg-emerald-500/20 text-emerald-300 text-[10px] font-semibold px-2 py-0.5 rounded border border-emerald-500/30">
                  Cashless Protocol Active
                </span>
              </div>
              <h3 className="text-lg sm:text-xl font-extrabold text-white">
                PM-RAHAT Scheme (Cashless Stabilization Cover)
              </h3>
              <p className="text-xs text-slate-300 mt-0.5">
                Statutory cashless treatment for road accident victims up to ₹1.5 Lakh for the first 7 days from crash.
              </p>
            </div>
          </div>

          <div className="bg-white/10 px-4 py-2.5 rounded-xl border border-white/10 text-right self-start md:self-auto">
            <span className="text-[11px] text-slate-300 block">Scheme Tracking Ref</span>
            <span className="text-sm font-mono font-bold text-white">{p.reference_number}</span>
          </div>
        </div>

        {/* Cover Tracker Progress Bar */}
        <div className="pt-4 border-t border-white/10 space-y-2">
          <div className="flex flex-wrap items-baseline justify-between text-xs">
            <span className="font-semibold text-slate-200">
              Confirmed Hospital Bill Spend: <span className="text-white text-base font-bold">₹{inr(p.confirmed_bills_inr)}</span>
            </span>
            <span className="text-slate-300">
              Cap: <span className="font-bold text-white">₹{inr(p.cover_limit_inr)}</span> ({p.percent_used}% utilized)
            </span>
          </div>

          <div className="w-full h-3 rounded-full bg-white/20 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                p.percent_used >= 80 ? 'bg-accent-500' : 'bg-emerald-400'
              }`}
              style={{ width: `${Math.min(100, p.percent_used)}%` }}
            />
          </div>

          <div className="flex justify-between text-[11px] text-slate-300 pt-1">
            <span>Remaining cashless cover: ₹{inr(remaining)}</span>
            <span>
              Window: Day {p.day_of_cover} of {p.cover_days} · Ends {fmtTime(p.window_ends_at)} IST
            </span>
          </div>
        </div>
      </div>

      {/* Main Grid: Hospital Details + PM-RAHAT Verification Checklist */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Hospital Facility & Treatment */}
        <div className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-base font-bold text-navy-950 flex items-center gap-2">
                <span>🏥</span>
                <span>Hospital Admission & Treatment Status</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Medical desk intimation and patient care facility
              </p>
            </div>

            {!editing ? (
              <button
                onClick={() => setEditing(true)}
                className="text-xs font-semibold text-accent-500 hover:underline cursor-pointer"
              >
                ✎ Edit Facility
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setEditing(false)}
                  className="text-xs text-slate-500 hover:text-slate-800"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="btn-accent text-xs px-3 py-1 rounded-lg"
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            )}
          </div>

          {editing ? (
            <div className="space-y-3 pt-1">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Hospital Name
                </label>
                <input
                  type="text"
                  value={form.hospital_name}
                  onChange={(e) => setForm({ ...form, hospital_name: e.target.value })}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Facility Address
                </label>
                <input
                  type="text"
                  value={form.hospital_address}
                  onChange={(e) => setForm({ ...form, hospital_address: e.target.value })}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Emergency Contact
                  </label>
                  <input
                    type="text"
                    value={form.hospital_contact}
                    onChange={(e) => setForm({ ...form, hospital_contact: e.target.value })}
                    className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-accent-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Treating Doctor
                  </label>
                  <input
                    type="text"
                    value={form.treating_doctor}
                    onChange={(e) => setForm({ ...form, treating_doctor: e.target.value })}
                    className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-accent-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Treatment Status
                </label>
                <select
                  value={form.hospital_treatment_status}
                  onChange={(e) => setForm({ ...form, hospital_treatment_status: e.target.value })}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-accent-500"
                >
                  <option value="Admitted - General Ward">Admitted - General Ward</option>
                  <option value="Admitted - ICU">Admitted - ICU / Critical Care</option>
                  <option value="Under Observation">Under Observation (48 Hours)</option>
                  <option value="Discharged">Discharged - Home Recovery</option>
                  <option value="Outpatient">Outpatient Consultation</option>
                </select>
              </div>
            </div>
          ) : (
            <div className="space-y-4 pt-1">
              <div>
                <span className="text-xs text-slate-400 block">Hospital Facility</span>
                <span className="text-base font-bold text-navy-950">{h.name || 'Emergency Facility'}</span>
                <p className="text-xs text-slate-600 mt-0.5">{h.address || 'Outer Ring Road Medical Corridor'}</p>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-100 text-xs">
                <div>
                  <span className="text-slate-400 block">Emergency Desk Contact</span>
                  <span className="font-semibold text-navy-900 font-mono">{h.contact || '+91 80 4920 1100'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Lead Physician / Surgeon</span>
                  <span className="font-semibold text-navy-900">{h.treating_doctor || 'Trauma Lead'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Admission Timestamp</span>
                  <span className="font-medium text-slate-700">{h.admission_at ? fmtTime(h.admission_at) : 'N/A'} IST</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Current Care Status</span>
                  <span className="chip bg-blue-50 text-blue-700 font-semibold border border-blue-200 px-2 py-0.5 rounded">
                    {h.treatment_status}
                  </span>
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between text-xs">
                <span className="text-slate-500">Estimated Stabilization Cost:</span>
                <span className="font-bold text-navy-950 font-mono">₹{inr(h.estimated_expenses_inr)}</span>
              </div>
            </div>
          )}
        </div>

        {/* PM-RAHAT Statutory Criteria & Required Documents */}
        <div className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-5">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-base font-bold text-navy-950 flex items-center gap-2">
              <span>📋</span>
              <span>PM-RAHAT Statutory Requirements</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Criteria under Ministry of Road Transport & Highways guidelines
            </p>
          </div>

          {/* Eligibility Criteria */}
          <div className="space-y-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
              Scheme Eligibility Checklist
            </span>
            <div className="space-y-2">
              {p.eligibility_checklist.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-50/80 border border-slate-100 text-xs"
                >
                  <span className="text-emerald-600 font-bold text-sm">✓</span>
                  <div>
                    <span className="font-bold text-navy-950 block">{item.title}</span>
                    <span className="text-slate-500 text-[11px]">{item.description}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Required Documents Checklist */}
          <div className="space-y-2 pt-2 border-t border-slate-100">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
              Required Documents for Settlement
            </span>
            <div className="space-y-1.5">
              {p.required_documents.map((doc, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded-lg bg-slate-50 text-xs"
                >
                  <span className="text-slate-700 font-medium">{doc.name}</span>
                  <span className={`chip text-[10px] font-bold px-2 py-0.5 rounded ${
                    doc.present
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-amber-50 text-amber-800 border border-amber-200'
                  }`}>
                    {doc.present ? 'Available' : 'Pending Upload'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
