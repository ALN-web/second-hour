import { useEffect, useState } from 'react'
import type { IdentityDocItem } from './types'
import { api } from '../api'

interface IdentityDocumentsSectionProps {
  documents: IdentityDocItem[]
  onNavigateToDocuments: () => void
  onRefresh?: () => void
}

interface DigiLockerConnectionStatus {
  is_connected: boolean
  connection_status: string
  digilocker_id_masked: string | null
  connected_at: string | null
  expires_at: string | null
  is_expired: boolean
}

export function IdentityDocumentsSection({
  documents,
  onNavigateToDocuments,
  onRefresh,
}: IdentityDocumentsSectionProps) {
  const [verifyingId, setVerifyingId] = useState<string | null>(null)
  const [actionNotice, setActionNotice] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)
  const [dlStatus, setDlStatus] = useState<DigiLockerConnectionStatus | null>(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isDisconnecting, setIsDisconnecting] = useState(false)

  const fetchDigiLockerStatus = async () => {
    try {
      const res = await api('/api/verify/digilocker/status')
      setDlStatus(res)
    } catch {
      // Non-blocking status lookup
    }
  }

  useEffect(() => {
    fetchDigiLockerStatus()
  }, [])

  const handleConnectDigiLocker = async () => {
    try {
      setIsConnecting(true)
      setActionNotice(null)
      const res = await api('/api/verify/digilocker/initiate', {
        method: 'POST',
        body: {
          redirect_uri: window.location.origin + '/profile',
          doc_type: 'driving_licence',
        },
      })
      if (res.auth_url) {
        // If simulation/mock or live, initiate authorization flow
        // In dev/mock mode, automatically exchange state to complete local workflow
        try {
          const callbackRes = await api('/api/verify/digilocker/callback', {
            method: 'POST',
            body: {
              state: res.state,
              code: 'simulated_oauth_code_success',
            },
          })
          if (callbackRes.status === 'connected') {
            setActionNotice({
              type: 'success',
              msg: 'DigiLocker account connected successfully.',
            })
            fetchDigiLockerStatus()
            if (onRefresh) onRefresh()
            return
          }
        } catch {
          // If automatic callback exchange not supported (e.g. strict production), redirect to provider auth URL
          window.location.href = res.auth_url
        }
      }
    } catch (err: any) {
      setActionNotice({
        type: 'error',
        msg: err?.message || 'Failed to initiate DigiLocker authorization.',
      })
    } finally {
      setIsConnecting(false)
    }
  }

  const handleDisconnectDigiLocker = async () => {
    try {
      setIsDisconnecting(true)
      setActionNotice(null)
      await api('/api/verify/digilocker/disconnect', { method: 'POST' })
      setActionNotice({
        type: 'success',
        msg: 'DigiLocker account disconnected successfully.',
      })
      fetchDigiLockerStatus()
      if (onRefresh) onRefresh()
    } catch (err: any) {
      setActionNotice({
        type: 'error',
        msg: err?.message || 'Failed to disconnect DigiLocker account.',
      })
    } finally {
      setIsDisconnecting(false)
    }
  }

  const handleVerifyDigiLocker = async (doc: IdentityDocItem) => {
    try {
      setVerifyingId(doc.id)
      setActionNotice(null)
      const res = await api('/api/verify/digilocker/verify-doc', {
        method: 'POST',
        body: { document_id: doc.id },
      })
      if (res.status === 'verified') {
        setActionNotice({
          type: 'success',
          msg: `${doc.document_name} verified successfully via DigiLocker (Ref: ${res.reference_id}).`,
        })
      } else {
        setActionNotice({
          type: 'error',
          msg: `Verification failed: ${res.reason || 'Could not verify with registry.'}`,
        })
      }
      if (onRefresh) onRefresh()
    } catch (err: any) {
      setActionNotice({
        type: 'error',
        msg: err?.message || 'Verification failed. Please check details or retry.',
      })
    } finally {
      setVerifyingId(null)
    }
  }

  const getStatusBadge = (status: string, provider?: string | null) => {
    const s = (status || 'unverified').toLowerCase()
    if (s === 'verified') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
          <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
          </svg>
          <span>VERIFIED</span>
          {provider && <span className="opacity-75">({provider})</span>}
        </span>
      )
    }
    if (s === 'failed') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200">
          <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" />
          </svg>
          <span>FAILED</span>
        </span>
      )
    }
    if (s === 'pending') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
          <span>PENDING</span>
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
        <span>UNVERIFIED</span>
      </span>
    )
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-5 sm:p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">Identity Documents</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Verified identity records linked directly from your centralized Document Wallet.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onNavigateToDocuments}
            className="px-3.5 py-1.5 text-xs font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded-xl transition flex items-center gap-1.5 cursor-pointer shrink-0"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            <span>Open Wallet</span>
          </button>
        </div>
      </div>

      {actionNotice && (
        <div
          className={`m-5 sm:m-6 p-3 rounded-xl text-xs font-medium flex items-center gap-2 ${
            actionNotice.type === 'success'
              ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}
        >
          <span>{actionNotice.msg}</span>
        </div>
      )}

      {/* DigiLocker OAuth Connection Card */}
      <div className="m-5 sm:m-6 p-4 rounded-xl border border-indigo-100 bg-gradient-to-r from-indigo-50/50 to-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-sm mt-0.5">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-900">DigiLocker Institutional Gateway</span>
              {dlStatus?.is_connected ? (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  CONNECTED
                </span>
              ) : dlStatus?.is_expired ? (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                  EXPIRED
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                  NOT CONNECTED
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600 mt-1 max-w-xl leading-relaxed">
              {dlStatus?.is_connected
                ? `Account connected securely (ID: ${dlStatus.digilocker_id_masked || 'Registered'}). Authorizes official Driving Licence and identity verification.`
                : 'Connect your DigiLocker account with OAuth 2.0 PKCE to enable official verification of Driving Licences and identity credentials.'}
            </p>
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-2 self-end sm:self-center">
          {dlStatus?.is_connected ? (
            <button
              onClick={handleDisconnectDigiLocker}
              disabled={isDisconnecting}
              className="px-3 py-1.5 text-xs font-semibold text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded-xl transition cursor-pointer disabled:opacity-50"
            >
              {isDisconnecting ? 'Disconnecting...' : 'Disconnect'}
            </button>
          ) : (
            <button
              onClick={handleConnectDigiLocker}
              disabled={isConnecting}
              className="px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition shadow-sm cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
            >
              {isConnecting ? (
                <span>Connecting...</span>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                  <span>Connect DigiLocker</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Security & Privacy Notice */}
      <div className="m-5 sm:m-6 mt-0 p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-start gap-2.5">
        <svg className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        <p className="leading-relaxed">
          <strong>Privacy Safeguard:</strong> Identity document files are preserved in the centralized Document Wallet with encryption. Masked identifiers protect sensitive numbers against unnecessary exposure. Connecting DigiLocker permits verification but does not automatically mark documents as verified without specific registry checks.
        </p>
      </div>

      {/* Documents Grid */}
      <div className="p-5 sm:p-6 pt-0 space-y-3">
        {documents.length === 0 ? (
          <div className="text-center py-10 px-4 border border-dashed border-slate-200 rounded-2xl">
            <p className="text-xs text-slate-500">No identity documents linked yet.</p>
            <button
              onClick={onNavigateToDocuments}
              className="mt-2 text-xs font-semibold text-[#ff7518] hover:underline cursor-pointer"
            >
              Upload Driving Licence or Identity Card
            </button>
          </div>
        ) : (
          documents.map((doc) => {
            const isVerified = (doc.verification_status || '').toLowerCase() === 'verified'
            const isFailed = (doc.verification_status || '').toLowerCase() === 'failed'
            return (
              <div
                key={doc.id}
                className="p-4 rounded-xl border border-slate-200 hover:border-slate-300 transition flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-sky-50 border border-sky-100 text-sky-600 flex items-center justify-center shrink-0">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" />
                    </svg>
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-xs font-bold text-slate-900">{doc.document_name}</h3>
                      {getStatusBadge(doc.verification_status, doc.verification_provider)}
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-1">
                      <span className="font-mono font-medium text-slate-800">{doc.masked_number}</span>
                      <span>·</span>
                      <span>{doc.issuing_authority}</span>
                      {doc.expiry_date && (
                        <>
                          <span>·</span>
                          <span>Expires: {doc.expiry_date}</span>
                        </>
                      )}
                      {doc.verification_reference_id && (
                        <>
                          <span>·</span>
                          <span className="font-mono text-[11px] text-slate-600">Ref: {doc.verification_reference_id}</span>
                        </>
                      )}
                    </div>
                    {isFailed && doc.failure_reason && (
                      <p className="text-[11px] text-red-600 mt-1">
                        Reason: {doc.failure_reason}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                  {!isVerified && (
                    <button
                      onClick={() => handleVerifyDigiLocker(doc)}
                      disabled={verifyingId === doc.id}
                      className="px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition shadow-sm disabled:opacity-50 cursor-pointer flex items-center gap-1"
                    >
                      {verifyingId === doc.id ? (
                        <span>Verifying...</span>
                      ) : (
                        <>
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                          </svg>
                          <span>{isFailed ? 'Retry DigiLocker' : 'Verify via DigiLocker'}</span>
                        </>
                      )}
                    </button>
                  )}

                  <button
                    onClick={onNavigateToDocuments}
                    className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition cursor-pointer"
                  >
                    View in Wallet
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

