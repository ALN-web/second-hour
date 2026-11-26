import { useState } from 'react'
import type { PrivacyPreferences } from './types'

interface PrivacyPermissionsSectionProps {
  preferences: PrivacyPreferences
  onSave: (data: Partial<PrivacyPreferences>) => Promise<void>
}

export function PrivacyPermissionsSection({
  preferences,
  onSave,
}: PrivacyPermissionsSectionProps) {
  const [formData, setFormData] = useState({
    ai_data_access_enabled: preferences.ai_data_access_enabled,
    ai_include_medical: preferences.ai_include_medical,
    ai_include_documents: preferences.ai_include_documents,
    ai_include_vehicles: preferences.ai_include_vehicles,
    ai_include_cases: preferences.ai_include_cases,
    allow_emergency_broadcast: preferences.allow_emergency_broadcast,
  })
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const handleToggle = async (key: keyof typeof formData) => {
    const updated = { ...formData, [key]: !formData[key] }
    setFormData(updated)
    try {
      setSaving(true)
      await onSave(updated)
      setNotice('Privacy settings updated.')
      setTimeout(() => setNotice(null), 3000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-5 sm:p-6 border-b border-slate-100">
        <h2 className="text-base font-bold text-slate-900">Privacy & Second Hour AI Data Boundaries</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Explicit controls determining what categories of personal records Ask Second Hour AI can access.
        </p>
      </div>

      {notice && (
        <div className="m-5 sm:m-6 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium">
          {notice}
        </div>
      )}

      {/* Toggles */}
      <div className="p-5 sm:p-6 space-y-4">
        {/* Global AI toggle */}
        <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-xs font-bold text-slate-900">Enable Context-Aware AI Assistance</h3>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Allow Ask Second Hour AI to answer questions using your authorized account records.
            </p>
          </div>
          <button
            type="button"
            disabled={saving}
            onClick={() => handleToggle('ai_data_access_enabled')}
            className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors ${
              formData.ai_data_access_enabled ? 'bg-[#ff7518]' : 'bg-slate-300'
            }`}
          >
            <div
              className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                formData.ai_data_access_enabled ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Sub-boundaries */}
        <div className="space-y-3 pt-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Granular Data Categories Accessible to Second Hour AI
          </h4>

          {/* Vehicles */}
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition">
            <div>
              <p className="text-xs font-bold text-slate-900">Registered Vehicles & Insurance</p>
              <p className="text-[11px] text-slate-500">Allow AI to look up vehicle specs, policy numbers, and expiry countdowns.</p>
            </div>
            <input
              type="checkbox"
              checked={formData.ai_include_vehicles}
              onChange={() => handleToggle('ai_include_vehicles')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>

          {/* Cases */}
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition">
            <div>
              <p className="text-xs font-bold text-slate-900">Accident Cases & Tasks</p>
              <p className="text-[11px] text-slate-500">Allow AI to summarize case milestones, hospital progress, and police drafting.</p>
            </div>
            <input
              type="checkbox"
              checked={formData.ai_include_cases}
              onChange={() => handleToggle('ai_include_cases')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>

          {/* Documents */}
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition">
            <div>
              <p className="text-xs font-bold text-slate-900">Document Wallet Metadata</p>
              <p className="text-[11px] text-slate-500">Allow AI to search document titles and verification states in your wallet.</p>
            </div>
            <input
              type="checkbox"
              checked={formData.ai_include_documents}
              onChange={() => handleToggle('ai_include_documents')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>

          {/* Medical */}
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition">
            <div>
              <div className="flex items-center gap-1.5">
                <p className="text-xs font-bold text-slate-900">Optional Medical Information</p>
                <span className="text-[10px] font-semibold px-2 py-0.2 rounded bg-amber-50 text-amber-700 border border-amber-200">
                  Strict Privacy
                </span>
              </div>
              <p className="text-[11px] text-slate-500">Allow AI to inspect allergies & emergency notes for emergency assistance.</p>
            </div>
            <input
              type="checkbox"
              checked={formData.ai_include_medical}
              onChange={() => handleToggle('ai_include_medical')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>

          {/* Emergency broadcast */}
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50 transition">
            <div>
              <p className="text-xs font-bold text-slate-900">Automated Emergency Broadcast</p>
              <p className="text-[11px] text-slate-500">Authorize automated SOS broadcast to designated contacts during verified crashes.</p>
            </div>
            <input
              type="checkbox"
              checked={formData.allow_emergency_broadcast}
              onChange={() => handleToggle('allow_emergency_broadcast')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
