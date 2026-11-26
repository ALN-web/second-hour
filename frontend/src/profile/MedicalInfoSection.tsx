import { useState } from 'react'
import type { MedicalInfoData } from './types'

interface MedicalInfoSectionProps {
  medicalInfo: MedicalInfoData
  onSave: (data: Partial<MedicalInfoData>) => Promise<void>
  onClear: () => Promise<void>
}

export function MedicalInfoSection({
  medicalInfo,
  onSave,
  onClear,
}: MedicalInfoSectionProps) {
  const [formData, setFormData] = useState({
    blood_group: medicalInfo.blood_group || '',
    allergies: medicalInfo.allergies || '',
    medical_conditions: medicalInfo.medical_conditions || '',
    medications: medicalInfo.medications || '',
    emergency_notes: medicalInfo.emergency_notes || '',
    share_with_ems: medicalInfo.share_with_ems || false,
    share_with_ai: medicalInfo.share_with_ai || false,
  })
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [confirmClear, setConfirmClear] = useState(false)

  const bloodGroups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'Unknown']

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSaving(true)
      await onSave(formData)
      setNotice('Medical preparedness information saved.')
      setTimeout(() => setNotice(null), 4000)
    } finally {
      setSaving(false)
    }
  }

  const handleClear = async () => {
    try {
      setSaving(true)
      await onClear()
      setFormData({
        blood_group: '',
        allergies: '',
        medical_conditions: '',
        medications: '',
        emergency_notes: '',
        share_with_ems: false,
        share_with_ai: false,
      })
      setConfirmClear(false)
      setNotice('Medical information cleared.')
      setTimeout(() => setNotice(null), 4000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-5 sm:p-6 border-b border-slate-100 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900">Medical Information</h2>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
              Optional & Privacy-Restricted
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Vital health details accessible only during authorized emergency aftermath coordination.
          </p>
        </div>

        {confirmClear ? (
          <div className="flex items-center gap-1.5 bg-red-50 p-1 rounded-xl border border-red-200 text-xs">
            <span className="text-[11px] text-red-700 font-semibold px-1">Clear all?</span>
            <button
              onClick={handleClear}
              className="px-2 py-0.5 bg-red-600 hover:bg-red-700 text-white rounded text-[11px] font-bold cursor-pointer"
            >
              Yes
            </button>
            <button
              onClick={() => setConfirmClear(false)}
              className="px-2 py-0.5 text-slate-600 hover:text-slate-900 text-[11px] cursor-pointer"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirmClear(true)}
            className="text-xs font-semibold text-slate-400 hover:text-red-600 transition cursor-pointer"
          >
            Clear Information
          </button>
        )}
      </div>

      {/* Explanatory Disclaimer Alert */}
      <div className="m-5 sm:m-6 p-4 rounded-xl bg-amber-50/70 border border-amber-200/80 flex items-start gap-3">
        <svg className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div className="text-xs text-amber-900 leading-relaxed">
          <strong className="block font-bold mb-0.5 text-amber-950">Important Medical Disclaimer</strong>
          {medicalInfo.disclaimer}
        </div>
      </div>

      {notice && (
        <div className="mx-5 sm:mx-6 mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium">
          {notice}
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="px-5 sm:px-6 pb-6 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Blood Group
            </label>
            <select
              value={formData.blood_group}
              onChange={(e) => setFormData({ ...formData, blood_group: e.target.value })}
              className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
            >
              <option value="">Select blood group (optional)</option>
              {bloodGroups.map((bg) => (
                <option key={bg} value={bg}>{bg}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Known Allergies
            </label>
            <input
              type="text"
              value={formData.allergies}
              onChange={(e) => setFormData({ ...formData, allergies: e.target.value })}
              placeholder="e.g. Penicillin, Peanuts, Sulfa drugs"
              className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Existing Medical Conditions
            </label>
            <input
              type="text"
              value={formData.medical_conditions}
              onChange={(e) => setFormData({ ...formData, medical_conditions: e.target.value })}
              placeholder="e.g. Hypertension, Diabetes, Asthma"
              className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Current Medications
            </label>
            <input
              type="text"
              value={formData.medications}
              onChange={(e) => setFormData({ ...formData, medications: e.target.value })}
              placeholder="e.g. Metformin 500mg, Inhaler"
              className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Emergency Medical Notes
          </label>
          <textarea
            rows={2}
            value={formData.emergency_notes}
            onChange={(e) => setFormData({ ...formData, emergency_notes: e.target.value })}
            placeholder="e.g. Carries EpiPen in backpack, Pacemaker implant, preferred trauma center..."
            className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
          />
        </div>

        {/* Privacy & Sharing Toggles */}
        <div className="pt-2 space-y-2.5 border-t border-slate-100">
          <label className="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.share_with_ems}
              onChange={(e) => setFormData({ ...formData, share_with_ems: e.target.checked })}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
            <span className="text-xs text-slate-700 font-medium">
              Share critical blood group & allergy notes with treating hospital trauma desk during an active accident case.
            </span>
          </label>

          <label className="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.share_with_ai}
              onChange={(e) => setFormData({ ...formData, share_with_ai: e.target.checked })}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
            <span className="text-xs text-slate-700 font-medium">
              Allow Ask Second Hour AI to review medical notes when assisting me during case reviews.
            </span>
          </label>
        </div>

        <div className="pt-4 flex items-center justify-end">
          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2.5 text-xs font-semibold text-white bg-[#ff7518] hover:bg-[#ea6309] rounded-xl transition shadow-md shadow-[#ff7518]/20 disabled:opacity-50 cursor-pointer"
          >
            {saving ? 'Saving...' : 'Save Medical Info'}
          </button>
        </div>
      </form>
    </div>
  )
}
