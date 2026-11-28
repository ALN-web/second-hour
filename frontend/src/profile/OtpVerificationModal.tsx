import { useEffect, useState } from 'react'
import { api } from '../api'

interface OtpVerificationModalProps {
  isOpen: boolean
  channel: 'email' | 'phone' | null
  target: string
  onClose: () => void
  onSuccess: () => void
}

export function OtpVerificationModal({
  isOpen,
  channel,
  target,
  onClose,
  onSuccess,
}: OtpVerificationModalProps) {
  const [otp, setOtp] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resending, setResending] = useState(false)
  const [requestingInitial, setRequestingInitial] = useState(false)
  const [resendNotice, setResendNotice] = useState<string | null>(null)
  const [devDemoCode, setDevDemoCode] = useState<string | null>(null)

  // Automatically request OTP dispatch when modal opens
  useEffect(() => {
    let active = true
    if (isOpen && channel) {
      setOtp('')
      setError(null)
      setResendNotice(null)
      setDevDemoCode(null)
      setRequestingInitial(true)

      api('/api/profile/verify/request-otp', {
        method: 'POST',
        body: { channel },
      })
        .then((res) => {
          if (!active) return
          if (import.meta.env.DEV && res.demo_code) {
            setDevDemoCode(res.demo_code)
          }
          setResendNotice(res.message || 'OTP sent successfully.')
        })
        .catch((err: any) => {
          if (!active) return
          setError(err?.message || 'Unable to send OTP. Please try again.')
        })
        .finally(() => {
          if (active) setRequestingInitial(false)
        })
    }
    return () => {
      active = false
    }
  }, [isOpen, channel])

  if (!isOpen || !channel) return null

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!otp.trim()) {
      setError('Please enter the 6-digit verification code.')
      return
    }

    try {
      setSubmitting(true)
      setError(null)
      await api('/api/profile/verify/confirm-otp', {
        method: 'POST',
        body: { channel, otp: otp.trim() },
      })
      onSuccess()
      onClose()
    } catch (err: any) {
      setError(err?.message || 'Invalid verification code. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleResend = async () => {
    try {
      setResending(true)
      setError(null)
      setResendNotice(null)
      const res = await api('/api/profile/verify/request-otp', {
        method: 'POST',
        body: { channel },
      })
      if (import.meta.env.DEV && res.demo_code) {
        setDevDemoCode(res.demo_code)
      }
      setResendNotice(res.message || 'OTP sent successfully.')
    } catch (err: any) {
      setError(err?.message || 'Unable to send OTP. Please try again.')
    } finally {
      setResending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-[#091528] text-white p-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-orange-500/20 text-[#ff7518] border border-orange-500/30 flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Verify {channel === 'email' ? 'Email Address' : 'Mobile Number'}
              </h3>
              <p className="text-xs text-slate-300">Two-factor contact verification</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleVerify} className="p-6 space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            We have dispatched a 6-digit one-time verification passcode to{' '}
            <strong className="text-slate-900">{target}</strong>.
          </p>

          {requestingInitial && (
            <div className="p-2.5 rounded-lg bg-orange-50 border border-orange-200 text-xs text-orange-800 font-medium flex items-center gap-2">
              <div className="w-3.5 h-3.5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
              <span>Dispatching verification passcode to {target}...</span>
            </div>
          )}

          {import.meta.env.DEV && devDemoCode && (
            <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl text-xs text-blue-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-bold">Development Passcode:</span>
                <code className="px-2 py-0.5 bg-blue-100 rounded font-mono font-bold text-blue-900">{devDemoCode}</code>
              </div>
              <button
                type="button"
                onClick={() => setOtp(devDemoCode)}
                className="text-blue-600 hover:underline font-semibold"
              >
                Fill code
              </button>
            </div>
          )}

          {resendNotice && (
            <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium">
              {resendNotice}
            </div>
          )}

          {error && (
            <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-800 font-medium">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Enter 6-Digit Passcode
            </label>
            <input
              type="text"
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              placeholder="• • • • • •"
              className="w-full text-center tracking-widest text-xl font-bold font-mono rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518] focus:border-[#ff7518]"
            />
          </div>

          <div className="flex items-center justify-between text-xs pt-1">
            <span className="text-slate-500">Didn't receive code?</span>
            <button
              type="button"
              onClick={handleResend}
              disabled={resending}
              className="font-semibold text-[#ff7518] hover:underline disabled:opacity-50 cursor-pointer"
            >
              {resending ? 'Sending...' : 'Resend OTP'}
            </button>
          </div>

          <div className="pt-2 flex items-center justify-end gap-2.5 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-xl transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 text-xs font-semibold text-white bg-[#ff7518] hover:bg-[#ea6309] rounded-xl transition shadow-md shadow-[#ff7518]/20 disabled:opacity-50 cursor-pointer"
            >
              {submitting ? 'Verifying...' : 'Confirm Verification'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
