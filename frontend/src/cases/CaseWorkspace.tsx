import { useCallback, useEffect, useState } from 'react'
import { api, fmtTime } from '../api'
import type { CaseWorkspaceData } from './types'
import { OverviewTab } from './tabs/OverviewTab'
import { TimelineTab } from './tabs/TimelineTab'
import { EvidenceTab } from './tabs/EvidenceTab'
import { HospitalTab } from './tabs/HospitalTab'
import { PoliceInsuranceTab } from './tabs/PoliceInsuranceTab'
import { FamilyTasksTab } from './tabs/FamilyTasksTab'
import { CaseAssistantDrawer } from './CaseAssistantDrawer'

interface CaseWorkspaceProps {
  caseId: string
  onBackToCases: () => void
  onOpenVehicle: (vehicleId: string) => void
  onBackHome: () => void
}

export type CaseWorkspaceTab =
  | 'overview'
  | 'timeline'
  | 'evidence'
  | 'hospital'
  | 'police-insurance'
  | 'family-tasks'

const WORKSPACE_TABS: Array<{ id: CaseWorkspaceTab; label: string; icon: string }> = [
  { id: 'overview', label: 'Overview', icon: '📍' },
  { id: 'timeline', label: 'Timeline', icon: '⏱️' },
  { id: 'evidence', label: 'Evidence & Documents', icon: '📁' },
  { id: 'hospital', label: 'Hospital & PM-RAHAT', icon: '🏥' },
  { id: 'police-insurance', label: 'Police & Insurance', icon: '👮' },
  { id: 'family-tasks', label: 'Family & Tasks', icon: '👥' },
]

export function CaseWorkspace({
  caseId,
  onBackToCases,
  onOpenVehicle,
  onBackHome,
}: CaseWorkspaceProps) {
  const [workspace, setWorkspace] = useState<CaseWorkspaceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<CaseWorkspaceTab>('overview')
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [tick, setTick] = useState(0)

  const refresh = () => setTick((t) => t + 1)

  const loadWorkspace = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api<CaseWorkspaceData>(`/api/cases/${caseId}/workspace`)
      setWorkspace(data)
    } catch (e) {
      console.error('Failed to load case workspace:', e)
    } finally {
      setLoading(false)
    }
  }, [caseId])

  useEffect(() => {
    loadWorkspace()
  }, [loadWorkspace, tick])

  if (loading && !workspace) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-8">
        <div className="text-center space-y-3">
          <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-navy-900 border-t-accent-500" />
          <p className="text-sm font-bold text-navy-950">Loading Case Workspace...</p>
        </div>
      </div>
    )
  }

  if (!workspace) {
    return (
      <div className="max-w-4xl mx-auto py-20 text-center space-y-4">
        <h2 className="text-xl font-bold text-navy-950">Case Not Found</h2>
        <p className="text-xs text-slate-500">The requested accident case workspace could not be loaded.</p>
        <button onClick={onBackToCases} className="btn-accent text-xs px-4 py-2">
          ← Back to My Cases
        </button>
      </div>
    )
  }

  const { case: c, alerts } = workspace
  const isActive = c.status === 'active' || c.status === 'open'
  const isResolved = c.status === 'resolved' || c.status === 'closed'

  return (
    <div className="min-h-screen bg-slate-50/70 pb-24">
      {/* Top Sticky Header */}
      <div className="bg-navy-950 text-white border-b border-navy-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {/* Breadcrumb Navigation */}
          <div className="flex items-center justify-between text-xs text-slate-400 mb-3">
            <div className="flex items-center gap-2">
              <button
                onClick={onBackHome}
                className="hover:text-white transition cursor-pointer"
              >
                Home
              </button>
              <span>/</span>
              <button
                onClick={onBackToCases}
                className="hover:text-white transition cursor-pointer"
              >
                My Cases
              </button>
              <span>/</span>
              <span className="text-white font-medium">{c.case_number}</span>
            </div>

            <button
              onClick={onBackToCases}
              className="text-xs text-accent-500 hover:text-accent-400 font-semibold flex items-center gap-1 cursor-pointer"
            >
              <span>←</span>
              <span>Back to Overview</span>
            </button>
          </div>

          {/* Main Case Title & Badges */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {c.case_number}
                </h1>
                <span className={`chip text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                  isActive
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                    : isResolved
                    ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
                    : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                }`}>
                  {c.status.replace('_', ' ').toUpperCase()}
                </span>
                {c.victim_display_name && (
                  <span className="text-xs text-slate-300 bg-white/10 px-2.5 py-1 rounded-lg">
                    Patient: <strong className="text-white font-semibold">{c.victim_display_name}</strong>
                  </span>
                )}
                {c.hospital_name && (
                  <span className="hidden sm:inline-block text-xs text-slate-300 bg-white/10 px-2.5 py-1 rounded-lg">
                    🏥 {c.hospital_name}
                  </span>
                )}
              </div>

              <div className="text-xs text-slate-400 mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                <span>Incident: <strong className="text-slate-200">{fmtTime(c.incident_at)} IST</strong></span>
                <span>·</span>
                <span>Location: <strong className="text-slate-200">{c.approximate_location}</strong></span>
              </div>
            </div>

            {/* Quick Actions Header Buttons */}
            <div className="flex items-center gap-2.5">
              <button
                onClick={() => setAssistantOpen(true)}
                className="btn-accent px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-md shadow-accent-500/20 cursor-pointer"
              >
                <span>🤖</span>
                <span>Ask AI Assistant</span>
                {alerts.length > 0 && (
                  <span className="bg-white text-accent-500 px-1.5 py-0.2 rounded-full font-bold text-[10px]">
                    {alerts.length}
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Workspace Tab Bar */}
        <div className="border-t border-navy-800/80 bg-navy-900/60">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <nav className="flex gap-1 overflow-x-auto py-1.5 scrollbar-none">
              {WORKSPACE_TABS.map((tab) => {
                const isCurrent = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-2.5 text-xs sm:text-sm font-semibold rounded-xl whitespace-nowrap transition-all cursor-pointer flex items-center gap-2 ${
                      isCurrent
                        ? 'bg-accent-500 text-white shadow-sm'
                        : 'text-slate-300 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    <span>{tab.icon}</span>
                    <span>{tab.label}</span>
                  </button>
                )
              })}
            </nav>
          </div>
        </div>
      </div>

      {/* Main Tab Content View */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' && (
          <OverviewTab
            workspace={workspace}
            onRefresh={refresh}
            onOpenVehicle={onOpenVehicle}
            onOpenTab={(tabId) => setActiveTab(tabId as any)}
          />
        )}

        {activeTab === 'timeline' && (
          <TimelineTab
            timeline={workspace.timeline}
            onRefresh={refresh}
          />
        )}

        {activeTab === 'evidence' && (
          <EvidenceTab
            caseId={caseId}
            evidence={workspace.evidence}
            onRefresh={refresh}
          />
        )}

        {activeTab === 'hospital' && (
          <HospitalTab
            caseId={caseId}
            hospitalPmrahat={workspace.hospital_pmrahat}
            onRefresh={refresh}
          />
        )}

        {activeTab === 'police-insurance' && (
          <PoliceInsuranceTab
            caseId={caseId}
            policeInfo={workspace.police_info}
            insuranceInfo={workspace.insurance_info}
            onRefresh={refresh}
          />
        )}

        {activeTab === 'family-tasks' && (
          <FamilyTasksTab
            caseId={caseId}
            familyMembers={workspace.family_members}
            tasks={workspace.tasks}
            onRefresh={refresh}
          />
        )}
      </div>

      {/* Embedded AI Assistant Drawer */}
      <CaseAssistantDrawer
        isOpen={assistantOpen}
        onClose={() => setAssistantOpen(false)}
        caseId={caseId}
        caseNumber={c.case_number}
        victimName={c.victim_display_name}
        alerts={alerts}
      />
    </div>
  )
}
