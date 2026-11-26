import { useState } from 'react'
import type { UserProfileData } from './types'

interface PersonalInfoSectionProps {
  profile: UserProfileData
  onSave: (data: Partial<UserProfileData>) => Promise<void>
  onOpenVerifyModal: (channel: 'email' | 'phone') => void
}

export function PersonalInfoSection({
  profile,
  onSave,
  onOpenVerifyModal,
}: PersonalInfoSectionProps) {
  const [editing, setEditing] = useState(false)
  const [formData, setFormData] = useState({
    name: profile.name,
    gender: profile.gender || '',
    date_of_birth: profile.date_of_birth || '',
    phone: profile.phone || '',
    email: profile.email || '',
    preferred_language: profile.preferred_language || 'English',
  })
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSaving(true)
      await onSave(formData)
      setEditing(false)
      setNotice('Personal information updated successfully.')
      setTimeout(() => setNotice(null), 4000)
    } catch (err: any) {
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setFormData({
      name: profile.name,
      gender: profile.gender || '',
      date_of_birth: profile.date_of_birth || '',
      phone: profile.phone || '',
      email: profile.email || '',
      preferred_language: profile.preferred_language || 'English',
    })
    setEditing(false)
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* Section Header */}
      <div className="p-5 sm:p-6 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-900">Personal Information</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Your identity details used across preparedness, verification, and emergency contacts.
          </p>
        </div>
        {!editing ? (
          <button
            onClick={() => setEditing(true)}
            className="px-4 py-1.5 text-xs font-semibold text-[#ff7518] hover:text-[#ea6309] border border-[#ff7518]/30 hover:border-[#ff7518] rounded-xl transition flex items-center gap-1.5 cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            <span>Edit Information</span>
          </button>
        ) : (
          <button
            onClick={handleCancel}
            className="text-xs font-semibold text-slate-500 hover:text-slate-800 transition cursor-pointer"
          >
            Cancel
          </button>
        )}
      </div>

      {notice && (
        <div className="m-5 sm:m-6 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium flex items-center gap-2">
          <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
          </svg>
          <span>{notice}</span>
        </div>
      )}

      {/* Body */}
      <form onSubmit={handleSubmit} className="p-5 sm:p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {/* Full Name */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Full Name <span className="text-red-500">*</span>
            </label>
            {editing ? (
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            ) : (
              <p className="text-sm font-semibold text-slate-900">{profile.name}</p>
            )}
          </div>

          {/* Preferred Language */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Preferred Language
            </label>
            {editing ? (
              <select
                value={formData.preferred_language}
                onChange={(e) => setFormData({ ...formData, preferred_language: e.target.value })}
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              >
                <option value="English">English</option>
                <option value="Hindi">Hindi (हिंदी)</option>
                <option value="Kannada">Kannada (ಕನ್ನಡ)</option>
                <option value="Tamil">Tamil (தமிழ்)</option>
                <option value="Telugu">Telugu (తెలుగు)</option>
                <option value="Malayalam">Malayalam (മലയാളം)</option>
              </select>
            ) : (
              <p className="text-sm text-slate-700">{profile.preferred_language || 'English'}</p>
            )}
          </div>

          {/* Date of Birth */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Date of Birth
            </label>
            {editing ? (
              <input
                type="date"
                value={formData.date_of_birth}
                onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            ) : (
              <p className="text-sm text-slate-700">
                {profile.date_of_birth ? profile.date_of_birth : <span className="text-slate-400 italic">Not set</span>}
              </p>
            )}
          </div>

          {/* Gender */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Gender
            </label>
            {editing ? (
              <select
                value={formData.gender}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              >
                <option value="">Prefer not to say</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            ) : (
              <p className="text-sm text-slate-700 capitalize">
                {profile.gender ? profile.gender : <span className="text-slate-400 italic">Prefer not to say</span>}
              </p>
            )}
          </div>

          {/* Mobile Number */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-700">
                Registered Mobile Number
              </label>
              {profile.phone_verified ? (
                <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                  ✓ Verified
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => onOpenVerifyModal('phone')}
                  className="text-[10px] font-bold text-[#ff7518] hover:underline cursor-pointer"
                >
                  Verify via OTP
                </button>
              )}
            </div>
            {editing ? (
              <div>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="+91 98450 00000"
                  className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
                />
                <p className="text-[10px] text-amber-600 mt-1">
                  Note: Updating mobile number will require fresh OTP verification.
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-900 font-mono">{profile.phone || 'Not provided'}</p>
            )}
          </div>

          {/* Email Address */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-700">
                Registered Email Address
              </label>
              {profile.email_verified ? (
                <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                  ✓ Verified
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => onOpenVerifyModal('email')}
                  className="text-[10px] font-bold text-[#ff7518] hover:underline cursor-pointer"
                >
                  Verify via OTP
                </button>
              )}
            </div>
            {editing ? (
              <div>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="name@example.com"
                  className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
                />
                <p className="text-[10px] text-amber-600 mt-1">
                  Note: Updating email will require fresh verification.
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-900">{profile.email || 'Not provided'}</p>
            )}
          </div>
        </div>

        {editing && (
          <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={handleCancel}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 text-xs font-semibold text-white bg-[#ff7518] hover:bg-[#ea6309] rounded-xl transition shadow-md shadow-[#ff7518]/20 disabled:opacity-50 cursor-pointer"
            >
              {saving ? 'Saving changes...' : 'Save Personal Info'}
            </button>
          </div>
        )}
      </form>
    </div>
  )
}
