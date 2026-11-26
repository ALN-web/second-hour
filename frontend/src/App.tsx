import { useCallback, useEffect, useState } from 'react'
import { api, getUser, setUser, fmtTime } from './api'
import { Dashboard, Chat, Documents, Tasks, ReportView, McpPanel, McpTicker } from './Views'
import { Navbar, type NavItem } from './components/Navbar'
import { Homepage } from './components/Homepage'
import { ReportAccidentModal, VehiclesModal, ProfileModal, NotificationsModal } from './components/Modals'

type User = { user_id: string; name: string; role_label: string }
type CaseRow = { case_id: string; case_number: string; victim_display_name?: string; hospital_name?: string; incident_at: string }

const CASE_TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'chat', label: 'Agent' },
  { id: 'documents', label: 'Documents' },
  { id: 'tasks', label: 'Tasks & timeline' },
  { id: 'report', label: 'Report' },
  { id: 'mcp', label: 'MCP' },
] as const
type CaseTab = (typeof CASE_TABS)[number]['id']

function EmergencyBanner() {
  return (
    <div className="bg-accent-500 text-white text-xs sm:text-sm text-center px-4 py-1.5 font-medium flex items-center justify-center gap-2" role="alert">
      <span>🚨 Second Hour is an assistance platform, not an emergency service. In an emergency, call</span>
      <a className="underline font-bold bg-white/20 px-1.5 py-0.5 rounded hover:bg-white/30 transition" href="tel:112">112</a>
    </div>
  )
}

function CaseList({ user, onOpen, onNew }: { user: User; onOpen: (c: CaseRow) => void; onNew: () => void }) {
  const [cases, setCases] = useState<CaseRow[]>([])
  const load = useCallback(() => { api<CaseRow[]>('/api/cases').then(setCases).catch(() => {}) }, [])
  useEffect(load, [load])

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-navy-950">Accident Cases</h1>
          <p className="text-xs text-slate-500">Active and past cases coordinated by {user.name}</p>
        </div>
        <button className="btn-accent text-xs" onClick={onNew}>+ Report New Accident</button>
      </div>

      <div className="space-y-3">
        {cases.map(c => (
          <div
            key={c.case_id}
            onClick={() => onOpen(c)}
            className="card p-4 hover:border-navy-700 hover:shadow-md transition cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-navy-900 text-base">{c.case_number}</span>
                <span className="chip bg-emerald-50 text-emerald-700 text-[11px] font-semibold border border-emerald-200">PM-RAHAT Active</span>
              </div>
              <div className="text-sm text-slate-700 mt-1 font-medium">
                Victim: {c.victim_display_name || 'Ravi Kumar'} · Hospital: {c.hospital_name || 'Sample City Hospital'}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">
                Incident: {fmtTime(c.incident_at)} IST
              </div>
            </div>

            <div className="flex items-center gap-2 self-end sm:self-center">
              <span className="text-xs font-semibold text-accent-500 group-hover:underline">Open Workspace →</span>
            </div>
          </div>
        ))}

        {cases.length === 0 && (
          <div className="card text-center py-8 text-sm text-slate-500">
            No active cases found. Click "Report New Accident" to create a case.
          </div>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [user, setU] = useState<User | null>(null)
  const [kase, setKase] = useState<CaseRow | null>(null)
  const [activeNav, setActiveNav] = useState<NavItem>('home')
  const [caseTab, setCaseTab] = useState<CaseTab>('dashboard')
  const [tick, setTick] = useState(0)

  // Modals state
  const [reportModalOpen, setReportModalOpen] = useState(false)
  const [vehiclesModalOpen, setVehiclesModalOpen] = useState(false)
  const [profileModalOpen, setProfileModalOpen] = useState(false)
  const [notificationsModalOpen, setNotificationsModalOpen] = useState(false)

  const refresh = () => setTick(t => t + 1)

  // Initialize and handle URL params
  useEffect(() => {
    const q = new URLSearchParams(location.search)
    const asUser = q.get('as')
    if (asUser) setUser(asUser)

    api<User[]>('/api/users').then((us) => {
      let currentId = getUser()
      // Default to Priya if no user selected
      if (!currentId && us.length > 0) {
        currentId = us[0].user_id
        setUser(currentId)
      }
      const matchedUser = us.find(x => x.user_id === currentId) || us[0] || null
      setU(matchedUser)

      const wantCase = q.get('case')
      const wantTab = q.get('tab')

      if (wantCase) {
        api<CaseRow[]>('/api/cases').then((cs) => {
          const c = cs.find(x => x.case_id === wantCase)
          if (c) {
            setKase(c)
            setActiveNav('cases')
            if (wantTab && CASE_TABS.some(x => x.id === wantTab)) {
              setCaseTab(wantTab as CaseTab)
            }
          }
        }).catch(() => {})
      }
    }).catch(() => {})
  }, [])

  // Helper to ensure an active case exists before navigating to case views
  const ensureCaseAndNavigate = async (tab: CaseTab, navId: NavItem) => {
    if (!kase) {
      try {
        const cs = await api<CaseRow[]>('/api/cases')
        if (cs && cs.length > 0) {
          setKase(cs[0])
        }
      } catch (e) {
        console.error(e)
      }
    }
    setCaseTab(tab)
    setActiveNav(navId)
  }

  const handleNav = (nav: NavItem) => {
    if (nav === 'home') {
      setActiveNav('home')
    } else if (nav === 'cases') {
      ensureCaseAndNavigate('dashboard', 'cases')
    } else if (nav === 'documents') {
      ensureCaseAndNavigate('documents', 'documents')
    } else if (nav === 'ai-assistant') {
      ensureCaseAndNavigate('chat', 'ai-assistant')
    } else if (nav === 'vehicles') {
      setVehiclesModalOpen(true)
    } else if (nav === 'profile') {
      setProfileModalOpen(true)
    }
  }

  const switchUser = async () => {
    try {
      const us = await api<User[]>('/api/users')
      if (us.length > 1) {
        const next = us.find(u => u.user_id !== user?.user_id) || us[0]
        setUser(next.user_id)
        setU(next)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const logout = () => {
    setUser('')
    setU(null)
    setKase(null)
    setActiveNav('home')
  }

  const handleCaseCreated = (newCase: any) => {
    setKase(newCase)
    setActiveNav('cases')
    setCaseTab('dashboard')
    refresh()
  }

  const handleDemoStaged = (priyaUser: User) => {
    setU(priyaUser)
    api<CaseRow[]>('/api/cases').then((cs) => {
      const demo = cs.find(c => c.case_id === 'case_demo') || cs[0]
      if (demo) {
        setKase(demo)
        setActiveNav('cases')
        setCaseTab('dashboard')
        refresh()
      }
    }).catch(() => {})
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-800 font-sans antialiased">
      {/* Top Banner */}
      <EmergencyBanner />

      {/* Top Navigation Bar */}
      <Navbar
        activeNav={activeNav}
        onNavigate={handleNav}
        user={user}
        onSwitchUser={switchUser}
        onLogout={logout}
        onOpenNotifications={() => setNotificationsModalOpen(true)}
        onOpenProfile={() => setProfileModalOpen(true)}
        onOpenVehicles={() => setVehiclesModalOpen(true)}
        activeCaseNumber={kase?.case_number}
      />

      {/* Case Sub-Navigation Bar (shown when inside case workspace) */}
      {activeNav !== 'home' && kase && (
        <div className="bg-navy-900 border-b border-navy-800 text-white">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="flex items-center justify-between py-2 border-b border-navy-800/80 text-xs text-slate-400">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveNav('home')}
                  className="hover:text-white transition flex items-center gap-1 cursor-pointer"
                >
                  <span>←</span> <span>Back to Home</span>
                </button>
                <span>/</span>
                <span className="text-white font-medium">{kase.case_number}</span>
                <span>({kase.victim_display_name || 'Ravi Kumar'})</span>
              </div>
              <div className="hidden sm:block text-slate-400">
                Hospital: <span className="text-slate-200">{kase.hospital_name || 'City Hospital'}</span>
              </div>
            </div>

            <nav className="flex gap-1 overflow-x-auto py-1">
              {CASE_TABS.map((t) => (
                <button
                  key={t.id}
                  onClick={() => {
                    setCaseTab(t.id)
                    if (t.id === 'documents') setActiveNav('documents')
                    else if (t.id === 'chat') setActiveNav('ai-assistant')
                    else setActiveNav('cases')
                  }}
                  className={`px-3.5 py-2 text-xs sm:text-sm font-medium whitespace-nowrap border-b-2 transition-all cursor-pointer ${
                    caseTab === t.id
                      ? 'border-accent-500 text-white bg-white/10 rounded-t-lg'
                      : 'border-transparent text-slate-300 hover:text-white hover:bg-white/5 rounded-t-lg'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </nav>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className={`flex-1 ${activeNav !== 'home' && kase && caseTab !== 'mcp' ? 'pb-48 sm:pb-24' : ''}`}>
        
        {/* VIEW 1: Homepage */}
        {activeNav === 'home' && (
          <Homepage
            user={user}
            onReportAccident={() => setReportModalOpen(true)}
            onOpenVehicles={() => setVehiclesModalOpen(true)}
            onOpenDocuments={() => ensureCaseAndNavigate('documents', 'documents')}
            onOpenCases={() => ensureCaseAndNavigate('dashboard', 'cases')}
            onOpenAI={() => ensureCaseAndNavigate('chat', 'ai-assistant')}
            onOpenProfile={() => setProfileModalOpen(true)}
            onDemoStaged={handleDemoStaged}
          />
        )}

        {/* VIEW 2: Case Workspace View */}
        {activeNav !== 'home' && kase && (
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
            {caseTab === 'dashboard' && (
              <Dashboard
                caseId={kase.case_id}
                tick={tick}
                refresh={refresh}
                goChat={() => {
                  setCaseTab('chat')
                  setActiveNav('ai-assistant')
                }}
              />
            )}
            {caseTab === 'chat' && <Chat caseId={kase.case_id} refresh={refresh} />}
            {caseTab === 'documents' && <Documents caseId={kase.case_id} refresh={refresh} />}
            {caseTab === 'tasks' && <Tasks caseId={kase.case_id} tick={tick} refresh={refresh} />}
            {caseTab === 'report' && <ReportView caseId={kase.case_id} />}
            {caseTab === 'mcp' && <McpPanel caseId={kase.case_id} />}
          </div>
        )}

        {/* Fallback if user clicked cases but no cases loaded yet */}
        {activeNav !== 'home' && !kase && user && (
          <CaseList
            user={user}
            onOpen={(c) => {
              setKase(c)
              setCaseTab('dashboard')
              refresh()
            }}
            onNew={() => setReportModalOpen(true)}
          />
        )}
      </main>

      {/* MCP Live Activity Ticker (displayed during case operations) */}
      {activeNav !== 'home' && kase && caseTab !== 'mcp' && (
        <McpTicker
          caseId={kase.case_id}
          onOpen={() => setCaseTab('mcp')}
        />
      )}

      {/* Modals */}
      <ReportAccidentModal
        isOpen={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
        onCaseCreated={handleCaseCreated}
      />

      <VehiclesModal
        isOpen={vehiclesModalOpen}
        onClose={() => setVehiclesModalOpen(false)}
      />

      <ProfileModal
        isOpen={profileModalOpen}
        onClose={() => setProfileModalOpen(false)}
        userName={user?.name}
        roleLabel={user?.role_label}
      />

      <NotificationsModal
        isOpen={notificationsModalOpen}
        onClose={() => setNotificationsModalOpen(false)}
      />
    </div>
  )
}
