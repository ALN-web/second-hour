import { useState } from 'react'
import type { ReportItem, ReportDetailItem, InsuranceClaimItem, ExternalSubmissionItem } from '../types'
import { api, fmtTime } from '../../api'

interface ReportsClaimsTabProps {
  caseId: string
  reports?: ReportItem[]
  claims?: InsuranceClaimItem[]
  submissions?: ExternalSubmissionItem[]
  onRefresh: () => void
}

export function ReportsClaimsTab({
  caseId,
  reports = [],
  claims = [],
  submissions = [],
  onRefresh,
}: ReportsClaimsTabProps) {
  // Navigation / sub-tabs within this tab
  const [subSection, setSubSection] = useState<'reports' | 'claims' | 'submissions'>('reports')

  // Generate Report Modal
  const [showGenerateModal, setShowGenerateModal] = useState(false)
  const [genReportType, setGenReportType] = useState('accident_summary')
  const [genTitle, setGenTitle] = useState('')
  const [genNotes, setGenNotes] = useState('')
  const [generating, setGenerating] = useState(false)

  // Report Detail & Version History
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null)
  const [reportDetail, setReportDetail] = useState<ReportDetailItem | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  // Approval / Revision
  const [approving, setApproving] = useState(false)
  const [showReviseModal, setShowReviseModal] = useState(false)
  const [revisionNotes, setRevisionNotes] = useState('')
  const [revising, setRevising] = useState(false)

  // New Claim Modal
  const [showClaimModal, setShowClaimModal] = useState(false)
  const [claimType, setClaimType] = useState('own_damage')
  const [insurerName, setInsurerName] = useState('Tata AIG General Insurance')
  const [policyNumber, setPolicyNumber] = useState('POL-99283401-2026')
  const [estimatedAmount, setEstimatedAmount] = useState('45000')
  const [claimDesc, setClaimDesc] = useState('')
  const [cashlessGarage, setCashlessGarage] = useState('Authorized Honda Service Centre, Koramangala')
  const [savingClaim, setSavingClaim] = useState(false)

  // New Submission Modal
  const [showSubmissionModal, setShowSubmissionModal] = useState(false)
  const [subOrgName, setSubOrgName] = useState('Tata AIG General Insurance Claims Portal')
  const [subOrgType, setSubOrgType] = useState('insurer')
  const [subMethod, setSubMethod] = useState('manual_user_submission')
  const [subRefNum, setSubRefNum] = useState('')
  const [savingSub, setSavingSub] = useState(false)

  // Confirm Manual Submission Modal
  const [confirmingSubId, setConfirmingSubId] = useState<string | null>(null)
  const [confirmRef, setConfirmRef] = useState('')
  const [confirmNotes, setConfirmNotes] = useState('')
  const [confirming, setConfirming] = useState(false)

  // Handlers
  const handleGenerateReport = async () => {
    setGenerating(true)
    try {
      await api(`/api/cases/${caseId}/reports`, {
        method: 'POST',
        body: {
          report_type: genReportType,
          title: genTitle.trim() || undefined,
          custom_notes: genNotes.trim(),
          generation_method: 'ai_assisted',
        },
      })
      setShowGenerateModal(false)
      setGenTitle('')
      setGenNotes('')
      onRefresh()
    } catch (e) {
      console.error('Failed to generate report:', e)
      alert('Failed to generate report draft. Check case details.')
    } finally {
      setGenerating(false)
    }
  }

  const handleOpenReportDetail = async (reportId: string) => {
    setSelectedReportId(reportId)
    setDetailLoading(true)
    try {
      const data = await api<ReportDetailItem>(`/api/cases/${caseId}/reports/${reportId}`)
      setReportDetail(data)
    } catch (e) {
      console.error('Failed to load report details:', e)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleApproveReport = async (reportId: string, versionId?: string) => {
    setApproving(true)
    try {
      await api(`/api/cases/${caseId}/reports/${reportId}/approve`, {
        method: 'POST',
        body: { version_id: versionId, notes: 'Confirmed and approved by family coordinator' },
      })
      if (selectedReportId === reportId) {
        handleOpenReportDetail(reportId)
      }
      onRefresh()
    } catch (e: any) {
      console.error('Failed to approve report:', e)
      alert(e.message || 'Only case coordinator can approve reports')
    } finally {
      setApproving(false)
    }
  }

  const handleReviseReport = async () => {
    if (!selectedReportId || !reportDetail) return
    setRevising(true)
    try {
      const updated = {
        ...reportDetail.active_content,
        user_revision_notes: revisionNotes.trim(),
        revised_at: new Date().toISOString(),
      }
      await api(`/api/cases/${caseId}/reports/${selectedReportId}/revise`, {
        method: 'POST',
        body: { updated_content: updated, notes: revisionNotes.trim() },
      })
      setShowReviseModal(false)
      setRevisionNotes('')
      handleOpenReportDetail(selectedReportId)
      onRefresh()
    } catch (e) {
      console.error('Failed to revise report:', e)
      alert('Failed to save report revision.')
    } finally {
      setRevising(false)
    }
  }

  const handleCreateClaim = async () => {
    setSavingClaim(true)
    try {
      await api(`/api/cases/${caseId}/claims`, {
        method: 'POST',
        body: {
          claim_type: claimType,
          insurer_name: insurerName.trim(),
          policy_number: policyNumber.trim(),
          estimated_amount: parseFloat(estimatedAmount) || undefined,
          description: claimDesc.trim(),
          cashless_garage: cashlessGarage.trim(),
        },
      })
      setShowClaimModal(false)
      setClaimDesc('')
      onRefresh()
    } catch (e) {
      console.error('Failed to initiate claim:', e)
      alert('Failed to initiate claim.')
    } finally {
      setSavingClaim(false)
    }
  }

  const handleUpdateClaimStatus = async (claimId: string, newStatus: string) => {
    try {
      await api(`/api/cases/${caseId}/claims/${claimId}/status`, {
        method: 'POST',
        body: { status: newStatus, reason: `Status updated to ${newStatus}` },
      })
      onRefresh()
    } catch (e) {
      console.error('Failed to update claim status:', e)
    }
  }

  const handleCreateSubmission = async () => {
    setSavingSub(true)
    try {
      await api(`/api/cases/${caseId}/submissions`, {
        method: 'POST',
        body: {
          external_org_name: subOrgName.trim(),
          external_org_type: subOrgType,
          submission_method: subMethod,
          external_reference_number: subRefNum.trim() || undefined,
          submission_status: subMethod === 'manual_user_submission' ? 'draft' : 'queued',
        },
      })
      setShowSubmissionModal(false)
      setSubRefNum('')
      onRefresh()
    } catch (e) {
      console.error('Failed to create submission:', e)
      alert('Failed to create external submission.')
    } finally {
      setSavingSub(false)
    }
  }

  const handleConfirmManualSub = async () => {
    if (!confirmingSubId) return
    setConfirming(true)
    try {
      await api(`/api/cases/${caseId}/submissions/${confirmingSubId}/confirm-manual`, {
        method: 'POST',
        body: {
          external_reference_number: confirmRef.trim() || undefined,
          notes: confirmNotes.trim(),
        },
      })
      setConfirmingSubId(null)
      setConfirmRef('')
      setConfirmNotes('')
      onRefresh()
    } catch (e) {
      console.error('Failed to confirm submission:', e)
      alert('Failed to confirm submission.')
    } finally {
      setConfirming(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* SECTION NAV / TOP BAR */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-white border border-slate-200 rounded-2xl shadow-sm">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSubSection('reports')}
            className={`px-4 py-2 text-xs font-bold rounded-xl transition cursor-pointer flex items-center gap-2 ${
              subSection === 'reports'
                ? 'bg-navy-950 text-white shadow-xs'
                : 'text-slate-600 hover:text-navy-950 hover:bg-slate-100'
            }`}
          >
            <span>📑</span>
            <span>Case Reports & Dossiers ({reports.length})</span>
          </button>
          <button
            onClick={() => setSubSection('claims')}
            className={`px-4 py-2 text-xs font-bold rounded-xl transition cursor-pointer flex items-center gap-2 ${
              subSection === 'claims'
                ? 'bg-navy-950 text-white shadow-xs'
                : 'text-slate-600 hover:text-navy-950 hover:bg-slate-100'
            }`}
          >
            <span>🛡️</span>
            <span>Insurance Claims ({claims.length})</span>
          </button>
          <button
            onClick={() => setSubSection('submissions')}
            className={`px-4 py-2 text-xs font-bold rounded-xl transition cursor-pointer flex items-center gap-2 ${
              subSection === 'submissions'
                ? 'bg-navy-950 text-white shadow-xs'
                : 'text-slate-600 hover:text-navy-950 hover:bg-slate-100'
            }`}
          >
            <span>📤</span>
            <span>External Filings ({submissions.length})</span>
          </button>
        </div>

        <div>
          {subSection === 'reports' && (
            <button
              onClick={() => setShowGenerateModal(true)}
              className="text-xs font-bold bg-accent-500 hover:bg-accent-600 text-white px-4 py-2 rounded-xl transition shadow-xs cursor-pointer flex items-center gap-1.5"
            >
              <span>+</span>
              <span>Generate New Report Draft</span>
            </button>
          )}
          {subSection === 'claims' && (
            <button
              onClick={() => setShowClaimModal(true)}
              className="text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl transition shadow-xs cursor-pointer flex items-center gap-1.5"
            >
              <span>+</span>
              <span>Lodge Motor Insurance Claim</span>
            </button>
          )}
          {subSection === 'submissions' && (
            <button
              onClick={() => setShowSubmissionModal(true)}
              className="text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl transition shadow-xs cursor-pointer flex items-center gap-1.5"
            >
              <span>+</span>
              <span>Record External Filing</span>
            </button>
          )}
        </div>
      </div>

      {/* SUB-SECTION 1: REPORTS & DOSSIERS */}
      {subSection === 'reports' && (
        <div className="space-y-4">
          {reports.length === 0 ? (
            <div className="p-12 text-center bg-white border border-slate-200 rounded-2xl space-y-3">
              <span className="text-4xl block">📄</span>
              <h3 className="text-sm font-bold text-navy-950">No Reports Generated Yet</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Generate formal accident dossiers synthesized strictly from case records, verified garage quotes, and evidence items.
              </p>
              <button
                onClick={() => setShowGenerateModal(true)}
                className="btn-accent text-xs px-4 py-2"
              >
                Generate First Report
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {reports.map((r) => {
                const isApproved = r.status === 'approved'
                const isReady = r.status === 'ready_for_review'
                return (
                  <div
                    key={r.id}
                    className="card p-5 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-3 hover:border-slate-300 transition"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="chip bg-slate-100 text-slate-700 font-mono text-[10px] px-2 py-0.5 rounded">
                        v{r.current_version_number}
                      </span>
                      <span
                        className={`chip text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                          isApproved
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                            : isReady
                            ? 'bg-blue-50 text-blue-800 border-blue-300'
                            : 'bg-amber-50 text-amber-800 border-amber-300'
                        }`}
                      >
                        {isApproved ? '✓ Approved' : isReady ? 'Review Ready' : 'Draft'}
                      </span>
                    </div>

                    <div>
                      <h4 className="text-sm font-bold text-navy-950 line-clamp-1">{r.title}</h4>
                      <span className="text-xs text-slate-500 block mt-0.5">{r.report_type_label}</span>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                      <span>{fmtTime(r.created_at)}</span>
                      <span>{r.generation_source === 'ai_generated' ? '🤖 AI-Assisted' : '👤 User Drafted'}</span>
                    </div>

                    <div className="flex items-center gap-2 pt-1">
                      <button
                        onClick={() => handleOpenReportDetail(r.id)}
                        className="flex-1 text-xs font-semibold py-1.5 px-3 bg-slate-100 hover:bg-slate-200 text-navy-950 rounded-lg transition cursor-pointer"
                      >
                        Inspect & History
                      </button>
                      <a
                        href={r.download_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs font-semibold py-1.5 px-3 bg-navy-900 hover:bg-navy-950 text-white rounded-lg transition cursor-pointer"
                      >
                        PDF
                      </a>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* SUB-SECTION 2: INSURANCE CLAIMS */}
      {subSection === 'claims' && (
        <div className="space-y-4">
          {claims.length === 0 ? (
            <div className="p-12 text-center bg-white border border-slate-200 rounded-2xl space-y-3">
              <span className="text-4xl block">🛡️</span>
              <h3 className="text-sm font-bold text-navy-950">No Insurance Claims Tracked</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Initiate own-damage or third-party claims linked to your registered vehicle policy and monitor surveyor inspection progress.
              </p>
              <button
                onClick={() => setShowClaimModal(true)}
                className="btn-accent text-xs px-4 py-2"
              >
                Lodge Claim
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {claims.map((c) => {
                return (
                  <div
                    key={c.id}
                    className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-xs space-y-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-base font-bold text-navy-950">{c.insurer_name}</h4>
                          <span className="chip bg-blue-50 text-blue-800 text-[11px] font-semibold px-2 py-0.5 rounded border border-blue-200">
                            {c.claim_type.replace('_', ' ').toUpperCase()}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Policy #{c.policy_number} | Claim Ref: <span className="font-mono font-bold text-navy-900">{c.claim_reference_number || 'Pending allocation'}</span>
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <select
                          value={c.claim_status}
                          onChange={(e) => handleUpdateClaimStatus(c.id, e.target.value)}
                          className="text-xs p-1.5 bg-slate-50 border border-slate-300 rounded-lg font-semibold text-navy-950 cursor-pointer"
                        >
                          <option value="draft">Draft</option>
                          <option value="preparing">Preparing Documentation</option>
                          <option value="ready_for_review">Ready for Review</option>
                          <option value="approved_by_user">Approved by User</option>
                          <option value="submitted">Submitted to Insurer</option>
                          <option value="under_review">Under Surveyor Review</option>
                          <option value="additional_info_required">Additional Info Required</option>
                          <option value="approved_by_insurer">Approved by Insurer</option>
                          <option value="settled">Claim Settled</option>
                          <option value="rejected">Rejected</option>
                          <option value="withdrawn">Withdrawn</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                      <div className="p-3 bg-slate-50 rounded-xl">
                        <span className="text-slate-400 block text-[11px]">Estimated Repair</span>
                        <span className="font-bold text-navy-950 text-sm">
                          {c.estimated_amount ? `₹${c.estimated_amount.toLocaleString()}` : '-'}
                        </span>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-xl">
                        <span className="text-slate-400 block text-[11px]">Approved Claim Amount</span>
                        <span className="font-bold text-emerald-800 text-sm">
                          {c.approved_amount ? `₹${c.approved_amount.toLocaleString()}` : 'Under Assessment'}
                        </span>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-xl">
                        <span className="text-slate-400 block text-[11px]">Independent Surveyor</span>
                        <span className="font-semibold text-navy-900 block truncate">
                          {c.surveyor_name || 'Unassigned'}
                        </span>
                        <span className="text-slate-500 text-[10px]">{c.surveyor_phone || '-'}</span>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-xl">
                        <span className="text-slate-400 block text-[11px]">Cashless Network Workshop</span>
                        <span className="font-medium text-slate-800 block truncate">
                          {c.cashless_garage || 'Authorized Garage'}
                        </span>
                      </div>
                    </div>

                    {c.description && (
                      <p className="text-xs text-slate-600 bg-slate-50/60 p-3 rounded-xl border border-slate-100">
                        {c.description}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* SUB-SECTION 3: EXTERNAL SUBMISSIONS */}
      {subSection === 'submissions' && (
        <div className="space-y-4">
          {/* Statutory boundary banner */}
          <div className="p-4 rounded-xl border border-amber-300 bg-amber-50/70 text-xs text-amber-950 flex items-start gap-2.5">
            <span className="text-amber-600 text-base">⚠️</span>
            <div>
              <span className="font-bold block">Statutory Filing Boundary & Integrity Policy</span>
              <span>
                User report approval does NOT equal external authority submission. Manual filings require explicit coordinator confirmation, and delivery acknowledgements are strictly recorded only upon genuine third-party receipt.
              </span>
            </div>
          </div>

          {submissions.length === 0 ? (
            <div className="p-12 text-center bg-white border border-slate-200 rounded-2xl space-y-3">
              <span className="text-4xl block">📤</span>
              <h3 className="text-sm font-bold text-navy-950">No Outbound Filings Recorded</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Record transmissions of formal case packages to Traffic Police Stations, Insurer Portals, or Hospital Schemes.
              </p>
              <button
                onClick={() => setShowSubmissionModal(true)}
                className="btn-accent text-xs px-4 py-2"
              >
                Record Filing
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {submissions.map((s) => {
                const isAcknowledged = s.submission_status === 'acknowledged'
                const isSubmitted = s.submission_status === 'submitted'
                return (
                  <div
                    key={s.id}
                    className="p-5 bg-white border border-slate-200 rounded-2xl shadow-xs flex flex-wrap items-center justify-between gap-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-navy-950">{s.external_org_name}</span>
                        <span className="chip bg-slate-100 text-slate-700 text-[10px] font-semibold px-2 py-0.5 rounded">
                          {s.external_org_type.toUpperCase()}
                        </span>
                        <span className="chip bg-blue-50 text-blue-800 text-[10px] font-semibold px-2 py-0.5 rounded">
                          {s.submission_method.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500">
                        External Reference / Receipt:{' '}
                        <span className="font-mono font-bold text-navy-900">
                          {s.external_reference_number || 'Pending receipt'}
                        </span>
                        {s.submitted_at && ` • Dispatched: ${fmtTime(s.submitted_at)}`}
                      </p>
                    </div>

                    <div className="flex items-center gap-3">
                      <span
                        className={`chip text-xs font-semibold px-3 py-1 rounded-full border ${
                          isAcknowledged
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                            : isSubmitted
                            ? 'bg-blue-50 text-blue-800 border-blue-300'
                            : 'bg-amber-50 text-amber-800 border-amber-300'
                        }`}
                      >
                        {isAcknowledged
                          ? '✓ Acknowledged by Authority'
                          : isSubmitted
                          ? 'Dispatched (Awaiting Receipt)'
                          : 'Draft Filing'}
                      </span>

                      {!isSubmitted && !isAcknowledged && (
                        <button
                          onClick={() => setConfirmingSubId(s.id)}
                          className="text-xs font-bold bg-navy-900 hover:bg-navy-950 text-white px-3 py-1.5 rounded-xl transition cursor-pointer"
                        >
                          Confirm Dispatch
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* MODAL 1: GENERATE REPORT DRAFT */}
      {showGenerateModal && (
        <div className="fixed inset-0 bg-navy-950/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <div className="border-b border-slate-100 pb-3 flex justify-between items-center">
              <h3 className="text-base font-bold text-navy-950">Generate Report Draft</h3>
              <button
                onClick={() => setShowGenerateModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Report Category</label>
                <select
                  value={genReportType}
                  onChange={(e) => setGenReportType(e.target.value)}
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl"
                >
                  <option value="accident_summary">Accident Case Summary Report</option>
                  <option value="insurance_incident">Motor Insurance Incident Report</option>
                  <option value="police_incident_info">Police Information & Intimation Dossier</option>
                  <option value="evidence_summary">Accident Evidence & Damage Summary</option>
                  <option value="medical_expense_summary">Medical Expense & Coverage Report</option>
                  <option value="general_accident_doc">General Accident Documentation Package</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Custom Title (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Preliminary Crash Report for Insurer"
                  value={genTitle}
                  onChange={(e) => setGenTitle(e.target.value)}
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Coordinator Context Notes</label>
                <textarea
                  rows={3}
                  placeholder="Specify particular details to highlight in the synthesized draft..."
                  value={genNotes}
                  onChange={(e) => setGenNotes(e.target.value)}
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>

              <div className="p-3 rounded-xl bg-blue-50/60 border border-blue-200 text-blue-950 text-[11px]">
                🤖 <strong>Grounding Rule:</strong> The report synthesizes only verified case items, documents, and evidence files. Missing fields will be explicitly flagged without fabrication.
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => setShowGenerateModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerateReport}
                disabled={generating}
                className="px-4 py-2 text-xs font-bold bg-accent-500 hover:bg-accent-600 text-white rounded-xl transition cursor-pointer"
              >
                {generating ? 'Synthesizing...' : 'Generate Draft (v1)'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: REPORT DETAIL & VERSION HISTORY */}
      {selectedReportId && detailLoading && (
        <div className="fixed inset-0 bg-navy-950/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl p-6 shadow-xl flex items-center gap-3">
            <div className="inline-block animate-spin rounded-full h-5 w-5 border-2 border-navy-900 border-t-accent-500" />
            <span className="text-xs font-bold text-navy-950">Loading Report Details...</span>
          </div>
        </div>
      )}

      {selectedReportId && !detailLoading && reportDetail && (
        <div className="fixed inset-0 bg-navy-950/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-xl border border-slate-200 max-h-[90vh] overflow-y-auto">
            <div className="border-b border-slate-100 pb-3 flex justify-between items-start">
              <div>
                <span className="chip bg-slate-100 text-slate-700 font-mono text-[10px] px-2 py-0.5 rounded">
                  v{reportDetail.current_version_number} • {reportDetail.report_type_label}
                </span>
                <h3 className="text-base font-bold text-navy-950 mt-1">{reportDetail.title}</h3>
              </div>
              <button
                onClick={() => setSelectedReportId(null)}
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                ✕
              </button>
            </div>

            {/* Status & Coordinator Actions */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div>
                <span className="text-slate-400 block text-[11px]">Status</span>
                <span className="font-bold text-navy-950 uppercase">{reportDetail.status}</span>
                {reportDetail.approved_by && (
                  <span className="text-emerald-800 text-[10px] block">
                    Approved by coordinator on {fmtTime(reportDetail.approved_at || '')}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                {reportDetail.status !== 'approved' && (
                  <button
                    onClick={() => handleApproveReport(reportDetail.id, reportDetail.current_version_id)}
                    disabled={approving}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs cursor-pointer"
                  >
                    {approving ? 'Approving...' : '✓ Approve Report'}
                  </button>
                )}
                <button
                  onClick={() => setShowReviseModal(true)}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-900 text-white font-semibold rounded-xl text-xs cursor-pointer"
                >
                  Revise / Edit
                </button>
                <a
                  href={reportDetail.download_url}
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1.5 bg-accent-500 hover:bg-accent-600 text-white font-bold rounded-xl text-xs cursor-pointer"
                >
                  Download PDF
                </a>
              </div>
            </div>

            {/* Version History Stream */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-navy-950 uppercase tracking-wide">
                Immutable Version History ({reportDetail.versions.length})
              </h4>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {reportDetail.versions.map((v) => (
                  <div
                    key={v.id}
                    className="p-3 bg-white border border-slate-200 rounded-xl text-xs flex justify-between items-center"
                  >
                    <div>
                      <span className="font-bold text-navy-900">Version {v.version_number}</span>
                      <span className="text-slate-400 text-[11px] ml-2">
                        {fmtTime(v.created_at)} • {v.generation_method}
                      </span>
                      {v.sha256 && (
                        <span className="font-mono text-[10px] text-slate-400 block truncate max-w-xs">
                          SHA: {v.sha256}
                        </span>
                      )}
                    </div>
                    {v.download_url && (
                      <a
                        href={v.download_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-blue-600 hover:underline font-semibold"
                      >
                        Download PDF
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Missing Info warnings if any */}
            {reportDetail.active_content?.missing_information?.length > 0 && (
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-950">
                <span className="font-bold block mb-1">⚠️ Missing Information Grounding Note:</span>
                <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
                  {reportDetail.active_content.missing_information.map((m: string, idx: number) => (
                    <li key={idx}>{m}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL 3: REVISE REPORT */}
      {showReviseModal && (
        <div className="fixed inset-0 bg-navy-950/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <h3 className="text-base font-bold text-navy-950">Draft Report Revision</h3>
            <p className="text-xs text-slate-500">
              Creating a revision generates a new immutable version without silently overwriting previous approved records.
            </p>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Revision Notes</label>
              <textarea
                rows={3}
                placeholder="Explain what facts or corrections are being incorporated..."
                value={revisionNotes}
                onChange={(e) => setRevisionNotes(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => setShowReviseModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleReviseReport}
                disabled={revising || !revisionNotes.trim()}
                className="px-4 py-2 text-xs font-bold bg-navy-950 text-white rounded-xl"
              >
                {revising ? 'Publishing...' : 'Publish Revision (New Version)'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: LODGE CLAIM */}
      {showClaimModal && (
        <div className="fixed inset-0 bg-navy-950/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <div className="border-b border-slate-100 pb-3 flex justify-between items-center">
              <h3 className="text-base font-bold text-navy-950">Lodge Motor Insurance Claim</h3>
              <button
                onClick={() => setShowClaimModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Claim Type</label>
                <select
                  value={claimType}
                  onChange={(e) => setClaimType(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl"
                >
                  <option value="own_damage">Own Damage (Accidental Collision)</option>
                  <option value="third_party_liability">Third-Party Liability</option>
                  <option value="comprehensive">Comprehensive Package Claim</option>
                  <option value="personal_accident">Personal Accident Cover</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Insurer Provider</label>
                <input
                  type="text"
                  value={insurerName}
                  onChange={(e) => setInsurerName(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Policy Schedule Number</label>
                <input
                  type="text"
                  value={policyNumber}
                  onChange={(e) => setPolicyNumber(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl font-mono"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Estimated Repair (₹)</label>
                <input
                  type="number"
                  value={estimatedAmount}
                  onChange={(e) => setEstimatedAmount(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Network / Cashless Garage</label>
                <input
                  type="text"
                  value={cashlessGarage}
                  onChange={(e) => setCashlessGarage(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Description / Garage Notes</label>
                <textarea
                  rows={2}
                  value={claimDesc}
                  onChange={(e) => setClaimDesc(e.target.value)}
                  placeholder="Damage summary and repair quotation notes..."
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => setShowClaimModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateClaim}
                disabled={savingClaim}
                className="px-4 py-2 text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white rounded-xl"
              >
                {savingClaim ? 'Creating...' : 'Initiate Claim'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 5: RECORD SUBMISSION */}
      {showSubmissionModal && (
        <div className="fixed inset-0 bg-navy-950/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <h3 className="text-base font-bold text-navy-950">Record External Filing</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Target Authority / Portal</label>
                <input
                  type="text"
                  value={subOrgName}
                  onChange={(e) => setSubOrgName(e.target.value)}
                  placeholder="e.g. HSR Layout Police Station or Tata AIG Portal"
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Organization Type</label>
                <select
                  value={subOrgType}
                  onChange={(e) => setSubOrgType(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl"
                >
                  <option value="insurer">Motor Insurance Provider</option>
                  <option value="police">Traffic Police Department</option>
                  <option value="hospital">Hospital Administration / Billing</option>
                  <option value="government">Government Scheme (PM-RAHAT)</option>
                  <option value="legal">Legal Counsel</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Submission Channel</label>
                <select
                  value={subMethod}
                  onChange={(e) => setSubMethod(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl"
                >
                  <option value="manual_user_submission">Manual User Submission (Physical / Counter)</option>
                  <option value="portal_upload">External Portal Self-Upload</option>
                  <option value="email">Direct Email Dispatch</option>
                  <option value="physical_handover">Physical Handover at Station</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">External Receipt Number (If received)</label>
                <input
                  type="text"
                  value={subRefNum}
                  onChange={(e) => setSubRefNum(e.target.value)}
                  placeholder="Optional acknowledgment number"
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl font-mono"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => setShowSubmissionModal(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateSubmission}
                disabled={savingSub}
                className="px-4 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl"
              >
                {savingSub ? 'Recording...' : 'Record Filing'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 6: CONFIRM MANUAL SUBMISSION */}
      {confirmingSubId && (
        <div className="fixed inset-0 bg-navy-950/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200">
            <h3 className="text-base font-bold text-navy-950">Confirm Manual Dispatch</h3>
            <p className="text-xs text-slate-500">
              Confirm that you have physically or digitally transmitted the dossier to the recipient organization.
            </p>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Receipt / Acknowledgment Number</label>
                <input
                  type="text"
                  value={confirmRef}
                  onChange={(e) => setConfirmRef(e.target.value)}
                  placeholder="e.g. GD-Entry # or Insurer Intake ID"
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl font-mono"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Dispatch Notes</label>
                <textarea
                  rows={2}
                  value={confirmNotes}
                  onChange={(e) => setConfirmNotes(e.target.value)}
                  placeholder="Submitted at station desk by coordinator..."
                  className="w-full p-2 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={() => setConfirmingSubId(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmManualSub}
                disabled={confirming}
                className="px-4 py-2 text-xs font-bold bg-navy-950 text-white rounded-xl"
              >
                {confirming ? 'Confirming...' : 'Confirm Submission'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
