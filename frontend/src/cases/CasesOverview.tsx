import { useCallback, useEffect, useState } from 'react'
import { api, fmtTime } from '../api'
import type { CasesOverviewResponse } from './types'
import { ShieldCheckCardIcon, FrontCarIcon, ArrowRightIcon } from '../components/Icons'

interface CasesOverviewProps {
  onOpenCase: (caseId: string) => void
  onReportAccident: () => void
  onBackHome: () => void
}

export function CasesOverview({
  onOpenCase,
  onReportAccident,
  onBackHome,
}: CasesOverviewProps) {
  const [data, setData] = useState<CasesOverviewResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'under_review' | 'resolved'>('all')
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest'>('newest')

  const loadCases = useCallback(async () => {
    setLoading(true)
    try {
      const q = new URLSearchParams()
      if (search.trim()) q.set('search', search.trim())
      if (statusFilter !== 'all') q.set('status', statusFilter)
      const res = await api<CasesOverviewResponse>(`/api/cases/overview?${q.toString()}`)
      setData(res)
    } catch (e) {
      console.error('Failed to load cases overview:', e)
    } finally {
      setLoading(false)
    }
  }, [search, statusFilter])

  useEffect(() => {
    const timer = setTimeout(() => {
      loadCases()
    }, 200)
    return () => clearTimeout(timer)
  }, [loadCases])

  const casesList = data?.cases || []
  const sortedCases = [...casesList].sort((a, b) => {
    const tA = new Date(a.incident_at).getTime()
    const tB = new Date(b.incident_at).getTime()
    return sortOrder === 'newest' ? tB - tA : tA - tB
  })

  const summary = data?.summary || {
    total_cases: 0,
    active_cases: 0,
    resolved_cases: 0,
    pending_actions: 0,
  }

  return (
    <div className="min-h-screen bg-slate-50/70 pb-24">
      {/* Top Header Banner */}
      <div className="bg-navy-950 text-white border-b border-navy-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-3">
            <button
              onClick={onBackHome}
              className="hover:text-white transition flex items-center gap-1 cursor-pointer"
            >
              <span>Home</span>
            </button>
            <span>/</span>
            <span className="text-white font-medium">My Cases</span>
          </div>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-orange-500/20 border border-orange-500/30 flex items-center justify-center text-accent-500">
                  <ShieldCheckCardIcon className="w-6 h-6" />
                </div>
                <div>
                  <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                    My Cases
                  </h1>
                  <p className="text-sm text-slate-300 mt-0.5">
                    Post-accident case management, hospital stabilization, PM-RAHAT assistance, and insurance claims.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={onReportAccident}
                className="btn-accent px-5 py-2.5 rounded-xl font-semibold shadow-lg shadow-accent-500/20 hover:shadow-accent-500/40 transition flex items-center gap-2 cursor-pointer text-sm"
              >
                <span>🚨</span>
                <span>Report an Accident</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* 4 Summary Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Cases */}
          <div className="card p-5 bg-white border border-slate-200/80 rounded-2xl shadow-sm hover:shadow transition">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Total Cases
              </span>
              <div className="w-8 h-8 rounded-lg bg-navy-50 text-navy-800 flex items-center justify-center font-bold text-xs">
                📁
              </div>
            </div>
            <div className="text-3xl font-extrabold text-navy-950 mt-2">
              {summary.total_cases}
            </div>
            <p className="text-xs text-slate-500 mt-1">All registered incident records</p>
          </div>

          {/* Active Cases */}
          <div className="card p-5 bg-white border border-slate-200/80 rounded-2xl shadow-sm hover:shadow transition">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">
                Active Cases
              </span>
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
              </span>
            </div>
            <div className="text-3xl font-extrabold text-navy-950 mt-2">
              {summary.active_cases}
            </div>
            <p className="text-xs text-emerald-600 mt-1 font-medium">Currently in post-crash workflow</p>
          </div>

          {/* Resolved Cases */}
          <div className="card p-5 bg-white border border-slate-200/80 rounded-2xl shadow-sm hover:shadow transition">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-blue-700 uppercase tracking-wider">
                Resolved Cases
              </span>
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center text-xs">
                ✓
              </div>
            </div>
            <div className="text-3xl font-extrabold text-navy-950 mt-2">
              {summary.resolved_cases}
            </div>
            <p className="text-xs text-slate-500 mt-1">Settled medical & claim records</p>
          </div>

          {/* Pending Actions */}
          <div className="card p-5 bg-white border border-amber-200/90 rounded-2xl shadow-sm hover:shadow transition bg-gradient-to-br from-white to-amber-50/30">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-amber-800 uppercase tracking-wider">
                Pending Actions
              </span>
              <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-xs">
                ⚠️
              </div>
            </div>
            <div className="text-3xl font-extrabold text-amber-700 mt-2">
              {summary.pending_actions}
            </div>
            <p className="text-xs text-amber-700 font-medium mt-1">Requires user attention</p>
          </div>
        </div>

        {/* Search, Filter & Sort Controls Bar */}
        <div className="card p-4 bg-white border border-slate-200/80 rounded-2xl shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
          {/* Search Box */}
          <div className="relative flex-1">
            <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              🔍
            </span>
            <input
              type="text"
              placeholder="Search by Case ID, vehicle number, victim, or location..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-500 transition"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 text-xs"
              >
                ✕
              </button>
            )}
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
            {[
              { id: 'all', label: 'All Cases' },
              { id: 'active', label: 'Active' },
              { id: 'under_review', label: 'Under Review' },
              { id: 'resolved', label: 'Resolved' },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setStatusFilter(f.id as any)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition cursor-pointer ${
                  statusFilter === f.id
                    ? 'bg-navy-950 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Sort Selector */}
          <div className="flex items-center gap-2 self-end md:self-auto">
            <span className="text-xs text-slate-500 whitespace-nowrap">Sort:</span>
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as any)}
              className="text-xs font-medium bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent-500"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
            </select>
          </div>
        </div>

        {/* Case Cards List */}
        {loading ? (
          <div className="py-20 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-navy-900 border-t-accent-500 mb-3" />
            <p className="text-sm font-medium text-slate-600">Loading accident cases...</p>
          </div>
        ) : sortedCases.length > 0 ? (
          <div className="space-y-4">
            {sortedCases.map((c) => {
              const isActive = c.status === 'active' || c.status === 'open'
              const isResolved = c.status === 'resolved' || c.status === 'closed'
              const statusBadgeClass = isActive
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : isResolved
                ? 'bg-blue-50 text-blue-700 border-blue-200'
                : 'bg-amber-50 text-amber-700 border-amber-200'

              return (
                <div
                  key={c.case_id}
                  onClick={() => onOpenCase(c.case_id)}
                  className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm hover:shadow-md hover:border-navy-300 transition duration-200 cursor-pointer group"
                >
                  {/* Top Bar: Case ID, Status, Timestamp */}
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
                    <div className="flex items-center gap-3">
                      <span className="font-extrabold text-navy-950 text-base sm:text-lg tracking-tight group-hover:text-accent-500 transition">
                        {c.case_number}
                      </span>
                      <span className={`chip text-xs font-semibold px-2.5 py-0.5 rounded-full border ${statusBadgeClass}`}>
                        {c.status.replace('_', ' ').toUpperCase()}
                      </span>
                      {c.pending_actions_count > 0 && (
                        <span className="chip bg-amber-50 text-amber-800 border-amber-300 text-xs font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1">
                          <span>⚠️</span>
                          <span>{c.pending_actions_count} Actions Required</span>
                        </span>
                      )}
                    </div>

                    <div className="text-xs text-slate-400">
                      Incident: <span className="text-slate-600 font-medium">{fmtTime(c.incident_at)} IST</span>
                    </div>
                  </div>

                  {/* Middle Content Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 py-4">
                    {/* Column 1: Registered Vehicle Information */}
                    <div className="bg-slate-50/80 p-3.5 rounded-xl border border-slate-100 flex items-center gap-3">
                      {c.vehicle?.photo_url ? (
                        <img
                          src={c.vehicle.photo_url}
                          alt={c.vehicle.model}
                          className="w-14 h-14 rounded-lg object-cover border border-slate-200 bg-white"
                        />
                      ) : (
                        <div className="w-14 h-14 rounded-lg bg-navy-900 text-white flex items-center justify-center font-bold text-lg">
                          <FrontCarIcon className="w-8 h-8 text-white/90" />
                        </div>
                      )}
                      <div className="overflow-hidden">
                        <div className="text-xs text-slate-400 font-medium">Registered Vehicle</div>
                        <div className="text-sm font-bold text-navy-950 truncate">
                          {c.vehicle ? `${c.vehicle.manufacturer} ${c.vehicle.model}` : 'Unlinked Vehicle'}
                        </div>
                        <div className="mt-1">
                          <span className="inline-block bg-white text-navy-900 font-mono text-[11px] font-bold px-2 py-0.5 rounded border border-slate-300 shadow-2xs">
                            {c.vehicle?.registration_number || 'N/A'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Column 2: Victim & Hospital Details */}
                    <div className="space-y-1.5 justify-center flex flex-col">
                      <div>
                        <span className="text-xs text-slate-400">Victim / Patient:</span>
                        <span className="text-sm font-semibold text-navy-900 ml-1.5">
                          {c.victim_display_name || 'Patient'}
                          {c.victim_relationship && (
                            <span className="text-xs font-normal text-slate-500 ml-1">
                              ({c.victim_relationship})
                            </span>
                          )}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-slate-400">Hospital:</span>
                        <span className="text-sm font-medium text-slate-800 ml-1.5">
                          {c.hospital_name || 'Emergency Stabilization Facility'}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 truncate">
                        📍 {c.approximate_location}
                      </div>
                    </div>

                    {/* Column 3: Injury & Damage Assessment */}
                    <div className="flex flex-col justify-center space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-400">Injury Severity:</span>
                        <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                          c.injury_severity === 'Critical'
                            ? 'bg-red-100 text-red-800'
                            : c.injury_severity === 'Severe'
                            ? 'bg-orange-100 text-orange-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}>
                          {c.injury_severity}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-400">Vehicle Damage:</span>
                        <span className="text-xs font-medium text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                          {c.damage_severity}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Bottom Row: Independent Stage Badges & CTA */}
                  <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <span className="chip bg-blue-50 text-blue-800 border border-blue-200">
                        🏥 {c.hospital_treatment_status}
                      </span>
                      <span className="chip bg-emerald-50 text-emerald-800 border border-emerald-200">
                        🛡️ PM-RAHAT: ₹1.5L Cover
                      </span>
                      <span className={`chip border ${
                        c.police_draft_status === 'approved_by_user'
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                          : 'bg-amber-50 text-amber-800 border-amber-200'
                      }`}>
                        👮 Police: {c.police_draft_status === 'approved_by_user' ? 'Approved' : 'Review Draft'}
                      </span>
                      <span className="chip bg-slate-100 text-slate-700 border border-slate-200">
                        📋 Insurance: {c.insurance_stage}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs font-bold text-accent-500 group-hover:text-accent-600 group-hover:translate-x-0.5 transition">
                      <span>View Case Details</span>
                      <ArrowRightIcon className="w-3.5 h-3.5" />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          /* Empty State */
          <div className="card py-16 px-6 text-center bg-white border border-slate-200 rounded-2xl">
            <div className="w-16 h-16 mx-auto rounded-full bg-navy-50 text-navy-800 flex items-center justify-center text-3xl mb-4">
              🛡️
            </div>
            <h3 className="text-lg font-bold text-navy-950">No accident cases found</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto mt-1">
              {search || statusFilter !== 'all'
                ? 'No cases match your active search or filter criteria. Try clearing filters.'
                : 'You have no accident cases recorded. When an accident occurs, you can log it here to get instant post-accident assistance, PM-RAHAT cashless tracking, and police documentation.'}
            </p>
            <div className="mt-6 flex justify-center gap-3">
              {search || statusFilter !== 'all' ? (
                <button
                  onClick={() => {
                    setSearch('')
                    setStatusFilter('all')
                  }}
                  className="btn-ghost text-xs px-4 py-2"
                >
                  Clear Filters
                </button>
              ) : (
                <button
                  onClick={onReportAccident}
                  className="btn-accent text-xs px-5 py-2.5 rounded-xl font-semibold shadow"
                >
                  + Report an Accident
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
