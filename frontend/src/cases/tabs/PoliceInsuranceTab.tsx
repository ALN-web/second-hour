import { useState } from 'react'
import type { PoliceInfo, InsuranceInfo } from '../types'
import { api, fmtTime } from '../../api'

interface PoliceInsuranceTabProps {
  caseId: string
  policeInfo: PoliceInfo
  insuranceInfo: InsuranceInfo
  onRefresh: () => void
}

export function PoliceInsuranceTab({
  caseId,
  policeInfo: pol,
  insuranceInfo: ins,
  onRefresh,
}: PoliceInsuranceTabProps) {
  const [agreedToStatement, setAgreedToStatement] = useState(false)
  const [approving, setApproving] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [showRevisionBox, setShowRevisionBox] = useState(false)

  const isApproved = pol.draft_status === 'approved_by_user'

  const handleApprove = async () => {
    if (!agreedToStatement) return
    setApproving(true)
    try {
      await api(`/api/cases/${caseId}/police/approve`, {
        method: 'POST',
        body: {
          approved: true,
          feedback: 'Statement reviewed and confirmed by user.',
        },
      })
      onRefresh()
    } catch (e) {
      console.error('Failed to approve statement:', e)
    } finally {
      setApproving(false)
    }
  }

  const handleRequestRevision = async () => {
    if (!feedback.trim()) return
    setApproving(true)
    try {
      await api(`/api/cases/${caseId}/police/approve`, {
        method: 'POST',
        body: {
          approved: false,
          feedback: feedback.trim(),
        },
      })
      setShowRevisionBox(false)
      onRefresh()
    } catch (e) {
      console.error('Failed to request revision:', e)
    } finally {
      setApproving(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* LEFT COLUMN: Police Documentation & AI Draft with User Approval */}
      <div className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-5">
        <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-navy-950 flex items-center gap-2">
              <span>👮</span>
              <span>Police Documentation & Intimation</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              General Diary, FIR records and official statement of incident
            </p>
          </div>

          <span className={`chip text-xs font-semibold px-2.5 py-1 rounded-full border ${
            isApproved
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : 'bg-amber-50 text-amber-800 border-amber-300'
          }`}>
            {isApproved ? '✓ Statement Approved' : 'Review Required'}
          </span>
        </div>

        {/* Station and FIR Metadata */}
        <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200/80 space-y-2 text-xs">
          <div className="flex justify-between items-start">
            <span className="text-slate-400">Jurisdiction Police Station:</span>
            <span className="font-bold text-navy-950 text-right">{pol.station_name || pol.police_station}</span>
          </div>
          <div className="flex justify-between items-start">
            <span className="text-slate-400">Station Address:</span>
            <span className="text-slate-700 text-right max-w-xs">{pol.station_address}</span>
          </div>
          <div className="flex justify-between items-center pt-2 border-t border-slate-200">
            <span className="text-slate-400">Investigating Officer:</span>
            <span className="font-semibold text-navy-900">
              {pol.investigating_officer} ({pol.officer_contact})
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Registered FIR No:</span>
            <span className="font-mono font-bold bg-white px-2 py-0.5 rounded border border-slate-300 text-navy-900">
              {pol.fir_number || 'Pending Intimation'}
            </span>
          </div>
          {pol.fir_sections && (
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Statutory Sections:</span>
              <span className="text-slate-700 font-medium">{pol.fir_sections}</span>
            </div>
          )}
        </div>

        {/* AI Draft Complaint / Statement Box */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-navy-900 uppercase tracking-wide">
              Statement of Incident (Prepared by Second Hour AI)
            </span>
            <span className="text-[11px] text-slate-400">Grounded in verified facts</span>
          </div>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 max-h-72 overflow-y-auto">
            <pre className="text-xs font-mono text-slate-800 whitespace-pre-wrap leading-relaxed font-normal">
              {pol.draft_report}
            </pre>
          </div>
        </div>

        {/* MANDATORY USER APPROVAL PANEL */}
        {!isApproved ? (
          <div className="p-4 rounded-xl border-2 border-amber-300 bg-amber-50/50 space-y-3">
            <div className="flex items-start gap-2">
              <span className="text-amber-600 text-base">⚠️</span>
              <div>
                <h4 className="text-xs font-bold text-amber-950">
                  Explicit Family Approval Required
                </h4>
                <p className="text-[11px] text-amber-800 mt-0.5 leading-relaxed">
                  Second Hour AI will never submit statements to authorities without your explicit sign-off. Please review the details above carefully.
                </p>
              </div>
            </div>

            <label className="flex items-start gap-2 cursor-pointer pt-1 text-xs text-slate-800">
              <input
                type="checkbox"
                checked={agreedToStatement}
                onChange={(e) => setAgreedToStatement(e.target.checked)}
                className="mt-0.5 rounded text-accent-500 focus:ring-accent-500"
              />
              <span className="leading-snug">
                I have reviewed this statement of incident and verify that the date, time, vehicle registration, and incident details are true and correct.
              </span>
            </label>

            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={handleApprove}
                disabled={!agreedToStatement || approving}
                className="btn-accent text-xs px-4 py-2 rounded-xl font-semibold shadow disabled:opacity-50 cursor-pointer"
              >
                {approving ? 'Approving...' : '✓ Approve Statement for Submission'}
              </button>

              <button
                onClick={() => setShowRevisionBox(!showRevisionBox)}
                className="btn-ghost text-xs px-3 py-2 cursor-pointer"
              >
                Request Revision
              </button>
            </div>

            {showRevisionBox && (
              <div className="pt-2 space-y-2">
                <textarea
                  rows={2}
                  placeholder="Specify what details need correction or updating..."
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  className="w-full text-xs p-2 bg-white border border-slate-300 rounded-lg"
                />
                <button
                  onClick={handleRequestRevision}
                  disabled={!feedback.trim() || approving}
                  className="text-xs bg-slate-800 text-white px-3 py-1.5 rounded-lg hover:bg-slate-900"
                >
                  Submit Revision Note
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 rounded-xl border border-emerald-300 bg-emerald-50/60 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="text-emerald-600 text-lg">✓</span>
              <div>
                <span className="font-bold text-emerald-950 block">
                  Statement Approved by Family Coordinator
                </span>
                <span className="text-emerald-800 text-[11px]">
                  Approved by {pol.approved_by || 'User'} on{' '}
                  {pol.approved_at ? fmtTime(pol.approved_at) : 'recently'} IST
                </span>
              </div>
            </div>
            <button
              onClick={() => window.print()}
              className="text-xs font-semibold bg-white border border-emerald-300 text-emerald-800 px-3 py-1.5 rounded-lg hover:bg-emerald-100/50 transition cursor-pointer"
            >
              Print / Export Statement
            </button>
          </div>
        )}
      </div>

      {/* RIGHT COLUMN: Motor Insurance Claim Management */}
      <div className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-5">
        <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-navy-950 flex items-center gap-2">
              <span>📋</span>
              <span>Motor Insurance Claim Tracking</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Comprehensive damage claim and surveyor inspection records
            </p>
          </div>

          <span className="chip bg-blue-50 text-blue-800 text-xs font-semibold px-2.5 py-1 rounded-full border border-blue-200">
            {ins.stage}
          </span>
        </div>

        {/* Claim Details Card */}
        <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200/80 space-y-3 text-xs">
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Insurance Provider:</span>
            <span className="font-bold text-navy-950 text-sm">{ins.provider}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Policy Schedule Number:</span>
            <span className="font-mono text-navy-900 font-semibold">{ins.policy_number}</span>
          </div>
          <div className="flex justify-between items-center pt-2 border-t border-slate-200">
            <span className="text-slate-400">Intimated Claim Reference:</span>
            <span className="font-mono font-bold bg-white text-navy-950 px-2 py-0.5 rounded border border-slate-300 shadow-2xs">
              {ins.claim_number}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Claim Settlement Status:</span>
            <span className="chip bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded text-[11px] font-semibold">
              {ins.settlement_status}
            </span>
          </div>
        </div>

        {/* Assigned Surveyor Information */}
        <div className="p-4 rounded-xl border border-blue-100 bg-blue-50/30 space-y-2 text-xs">
          <span className="text-xs font-bold text-blue-900 uppercase tracking-wide block">
            Assigned Independent Surveyor
          </span>
          <div className="flex justify-between items-center">
            <span className="text-slate-500">Surveyor Name:</span>
            <span className="font-semibold text-navy-950">{ins.surveyor_name}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500">Contact Number:</span>
            <span className="font-mono font-semibold text-navy-950">{ins.surveyor_phone}</span>
          </div>
          <div className="flex justify-between items-center pt-1 border-t border-blue-100/80">
            <span className="text-slate-500">Designated Network Garage:</span>
            <span className="font-medium text-slate-800">{ins.cashless_garage}</span>
          </div>
        </div>

        {/* Next Steps for Insurance */}
        <div className="space-y-2 pt-2">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            Recommended Next Steps
          </span>
          <div className="space-y-2 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-start gap-2.5">
              <span className="text-accent-500 font-bold text-sm">1.</span>
              <div>
                <span className="font-semibold text-navy-950 block">Surveyor Vehicle Inspection</span>
                <span className="text-slate-500 text-[11px]">
                  Confirm surveyor visit to authorized service workshop for repair estimate approval.
                </span>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-start gap-2.5">
              <span className="text-accent-500 font-bold text-sm">2.</span>
              <div>
                <span className="font-semibold text-navy-950 block">Share Document Wallet Links</span>
                <span className="text-slate-500 text-[11px]">
                  Driving Licence and RC copies are pre-verified and available under Case Evidence.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
