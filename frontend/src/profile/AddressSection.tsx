import { useState, useEffect } from 'react'
import type { AddressItem } from './types'

interface AddressSectionProps {
  addresses: { current: AddressItem | null; permanent: AddressItem | null }
  onSaveAddress: (type: 'current' | 'permanent', data: any) => Promise<void>
}

export function AddressSection({
  addresses,
  onSaveAddress,
}: AddressSectionProps) {
  const [currentForm, setCurrentForm] = useState({
    address_line_1: addresses.current?.address_line_1 || '',
    address_line_2: addresses.current?.address_line_2 || '',
    city: addresses.current?.city || '',
    state: addresses.current?.state || '',
    pin_code: addresses.current?.pin_code || '',
    country: addresses.current?.country || 'India',
  })

  const [sameAsCurrent, setSameAsCurrent] = useState(
    addresses.permanent?.is_same_as_current || false
  )

  const [permanentForm, setPermanentForm] = useState({
    address_line_1: addresses.permanent?.address_line_1 || '',
    address_line_2: addresses.permanent?.address_line_2 || '',
    city: addresses.permanent?.city || '',
    state: addresses.permanent?.state || '',
    pin_code: addresses.permanent?.pin_code || '',
    country: addresses.permanent?.country || 'India',
  })

  const [savingCurrent, setSavingCurrent] = useState(false)
  const [savingPermanent, setSavingPermanent] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    if (sameAsCurrent) {
      setPermanentForm({ ...currentForm })
    }
  }, [sameAsCurrent, currentForm])

  const handleSaveCurrent = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSavingCurrent(true)
      await onSaveAddress('current', currentForm)
      setNotice('Current residential address updated.')
      setTimeout(() => setNotice(null), 4000)
    } finally {
      setSavingCurrent(false)
    }
  }

  const handleSavePermanent = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSavingPermanent(true)
      await onSaveAddress('permanent', {
        ...permanentForm,
        is_same_as_current: sameAsCurrent,
      })
      setNotice('Permanent address updated.')
      setTimeout(() => setNotice(null), 4000)
    } finally {
      setSavingPermanent(false)
    }
  }

  return (
    <div className="space-y-6">
      {notice && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium">
          {notice}
        </div>
      )}

      {/* 1. Current Residential Address */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="p-5 sm:p-6 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">Current Residential Address</h2>
            <p className="text-xs text-slate-500 mt-0.5">Primary residence used for emergency jurisdiction and local contact.</p>
          </div>
          {addresses.current && (
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              Active
            </span>
          )}
        </div>

        <form onSubmit={handleSaveCurrent} className="p-5 sm:p-6 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Address Line 1 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={currentForm.address_line_1}
                onChange={(e) => setCurrentForm({ ...currentForm, address_line_1: e.target.value })}
                placeholder="House / Flat No., Building, Street Name"
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Address Line 2 (Optional)
              </label>
              <input
                type="text"
                value={currentForm.address_line_2}
                onChange={(e) => setCurrentForm({ ...currentForm, address_line_2: e.target.value })}
                placeholder="Area, Landmark, Road"
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                City <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={currentForm.city}
                onChange={(e) => setCurrentForm({ ...currentForm, city: e.target.value })}
                placeholder="e.g. Bengaluru"
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                State <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={currentForm.state}
                onChange={(e) => setCurrentForm({ ...currentForm, state: e.target.value })}
                placeholder="e.g. Karnataka"
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                PIN Code <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                maxLength={6}
                value={currentForm.pin_code}
                onChange={(e) => setCurrentForm({ ...currentForm, pin_code: e.target.value.replace(/\D/g, '') })}
                placeholder="560103"
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 font-mono focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Country
              </label>
              <input
                type="text"
                readOnly
                value={currentForm.country}
                className="w-full text-xs rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-slate-600 font-medium"
              />
            </div>
          </div>

          <div className="pt-3 flex items-center justify-end">
            <button
              type="submit"
              disabled={savingCurrent}
              className="px-5 py-2 text-xs font-semibold text-white bg-[#ff7518] hover:bg-[#ea6309] rounded-xl transition shadow-md shadow-[#ff7518]/20 disabled:opacity-50 cursor-pointer"
            >
              {savingCurrent ? 'Saving...' : 'Save Current Address'}
            </button>
          </div>
        </form>
      </div>

      {/* 2. Permanent Address */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="p-5 sm:p-6 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">Permanent Address</h2>
            <p className="text-xs text-slate-500 mt-0.5">Legal permanent residence record.</p>
          </div>
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={sameAsCurrent}
              onChange={(e) => setSameAsCurrent(e.target.checked)}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
            <span>Same as current address</span>
          </label>
        </div>

        {!sameAsCurrent && (
          <form onSubmit={handleSavePermanent} className="p-5 sm:p-6 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">Address Line 1 *</label>
                <input
                  type="text"
                  required
                  value={permanentForm.address_line_1}
                  onChange={(e) => setPermanentForm({ ...permanentForm, address_line_1: e.target.value })}
                  className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">City *</label>
                <input
                  type="text"
                  required
                  value={permanentForm.city}
                  onChange={(e) => setPermanentForm({ ...permanentForm, city: e.target.value })}
                  className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">State *</label>
                <input
                  type="text"
                  required
                  value={permanentForm.state}
                  onChange={(e) => setPermanentForm({ ...permanentForm, state: e.target.value })}
                  className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">PIN Code *</label>
                <input
                  type="text"
                  required
                  maxLength={6}
                  value={permanentForm.pin_code}
                  onChange={(e) => setPermanentForm({ ...permanentForm, pin_code: e.target.value.replace(/\D/g, '') })}
                  className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 font-mono focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
                />
              </div>
            </div>

            <div className="pt-3 flex items-center justify-end">
              <button
                type="submit"
                disabled={savingPermanent}
                className="px-5 py-2 text-xs font-semibold text-white bg-[#ff7518] hover:bg-[#ea6309] rounded-xl transition shadow-md shadow-[#ff7518]/20 disabled:opacity-50 cursor-pointer"
              >
                {savingPermanent ? 'Saving...' : 'Save Permanent Address'}
              </button>
            </div>
          </form>
        )}

        {sameAsCurrent && (
          <div className="p-5 sm:p-6 text-xs text-slate-500">
            Permanent address is linked to your current address:
            <p className="font-semibold text-slate-800 mt-1">
              {currentForm.address_line_1}, {currentForm.city}, {currentForm.state} - {currentForm.pin_code}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
