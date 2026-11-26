import { useState } from 'react'
import type { SecurityOverview } from './types'

interface AccountSecuritySectionProps {
  security: SecurityOverview
  onChangePassword: (curr: string, next: string) => Promise<void>
  onDeleteAccount: (confirmation: string) => Promise<{ status: string; message: string }>
}

export function AccountSecuritySection({
  security,
  onChangePassword,
  onDeleteAccount,
}: AccountSecuritySectionProps) {
  // Password change state
  const [currPassword, setCurrPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwdLoading, setPwdLoading] = useState(false)
  const [pwdNotice, setPwdNotice] = useState<string | null>(null)
  const [pwdError, setPwdError] = useState<string | null>(null)

  // Account deletion state
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteNotice, setDeleteNotice] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      setPwdError('New passwords do not match.')
      return
    }
    try {
      setPwdLoading(true)
      setPwdError(null)
      await onChangePassword(currPassword, newPassword)
      setPwdNotice('Password updated successfully.')
      setCurrPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setTimeout(() => setPwdNotice(null), 4000)
    } catch (err: any) {
      setPwdError(err?.message || 'Failed to update password.')
    } finally {
      setPwdLoading(false)
    }
  }

  const handleDeleteSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setDeleteLoading(true)
      setDeleteError(null)
      const res = await onDeleteAccount(deleteConfirmation)
      setDeleteNotice(res.message)
    } catch (err: any) {
      setDeleteError(err?.message || 'Failed to request account deletion.')
    } finally {
      setDeleteLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* 1. Password & Credentials */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="p-5 sm:p-6 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-900">Login & Password Security</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage your credentials and login protection.
          </p>
        </div>

        <form onSubmit={handlePasswordSubmit} className="p-5 sm:p-6 space-y-4 max-w-xl">
          {pwdNotice && (
            <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium">
              {pwdNotice}
            </div>
          )}
          {pwdError && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 font-medium">
              {pwdError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Current Password</label>
            <input
              type="password"
              required
              value={currPassword}
              onChange={(e) => setCurrPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">New Password</label>
              <input
                type="password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Min 8 chars, 1 letter & 1 digit"
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Confirm New Password</label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repeat new password"
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={pwdLoading}
            className="px-5 py-2 text-xs font-semibold text-white bg-[#091528] hover:bg-[#122847] rounded-xl transition shadow-sm disabled:opacity-50 cursor-pointer"
          >
            {pwdLoading ? 'Updating...' : 'Change Password'}
          </button>
        </form>
      </div>

      {/* 2. Active Sessions */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="p-5 sm:p-6 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-900">Active Web Sessions</h2>
          <p className="text-xs text-slate-500 mt-0.5">Devices currently authenticated to your Second Hour profile.</p>
        </div>

        <div className="p-5 sm:p-6 space-y-3">
          {security.active_sessions.map((sess) => (
            <div
              key={sess.id}
              className="p-3.5 rounded-xl border border-slate-200 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-xs font-bold text-slate-900">{sess.device}</p>
                    {sess.is_current && (
                      <span className="text-[10px] font-semibold px-2 py-0.2 rounded-full bg-emerald-100 text-emerald-800">
                        Current Session
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 font-mono mt-0.5">{sess.ip_masked}</p>
                </div>
              </div>
              <span className="text-xs text-slate-400">Active now</span>
            </div>
          ))}
        </div>
      </div>

      {/* 3. Account Deletion & Statutory Retention Notice */}
      <div className="bg-white rounded-2xl border border-red-200 shadow-sm overflow-hidden">
        <div className="p-5 sm:p-6 border-b border-red-100 bg-red-50/30">
          <h2 className="text-base font-bold text-red-900">Close Account</h2>
          <p className="text-xs text-red-700 mt-0.5">
            Permanently close your profile and deactivate active services.
          </p>
        </div>

        <form onSubmit={handleDeleteSubmit} className="p-5 sm:p-6 space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            Please note: In compliance with <strong>Ministry of Road Transport & Highways (MoRTH)</strong> and PM-RAHAT statutory guidelines, official road accident case files, police verifications, and hospital claims cannot be immediately erased during active legal retention windows.
          </p>

          {deleteNotice && (
            <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 leading-relaxed">
              {deleteNotice}
            </div>
          )}

          {deleteError && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800 font-medium">
              {deleteError}
            </div>
          )}

          <div className="max-w-md">
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Type <code className="font-mono text-red-600 bg-red-50 px-1 py-0.5 rounded">DELETE</code> to confirm
            </label>
            <input
              type="text"
              value={deleteConfirmation}
              onChange={(e) => setDeleteConfirmation(e.target.value)}
              placeholder="DELETE"
              className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-red-500"
            />
          </div>

          <button
            type="submit"
            disabled={deleteLoading || deleteConfirmation !== 'DELETE'}
            className="px-5 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-xl transition shadow-sm disabled:opacity-40 cursor-pointer"
          >
            {deleteLoading ? 'Processing...' : 'Request Account Closure'}
          </button>
        </form>
      </div>
    </div>
  )
}
