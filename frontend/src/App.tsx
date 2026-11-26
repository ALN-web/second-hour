import { useCallback, useEffect, useState } from 'react'
import { api, getUser, setUser, fmtTime } from './api'
import { Dashboard, Chat, Documents, Tasks, ReportView, McpPanel, McpTicker } from './Views'
import { Navbar, type NavItem } from './components/Navbar'
import { Homepage } from './components/Homepage'
import { ReportAccidentModal, ProfileModal, NotificationsModal } from './components/Modals'
import { VehiclesOverview } from './vehicles/VehiclesOverview'
import { VehicleDetails } from './vehicles/VehicleDetails'
import { AddVehicleWizard } from './vehicles/AddVehicleWizard'
import type { VehicleSummary, VehicleDetail, VehicleFormData } from './vehicles/types'

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

  // Vehicles Module state
  const [vehicleSubView, setVehicleSubView] = useState<'overview' | 'detail' | 'add'>('overview')
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null)
  const [vehicles, setVehicles] = useState<VehicleSummary[]>([])
  const [activeVehicle, setActiveVehicle] = useState<VehicleDetail | null>(null)
  const [vehiclesLoading, setVehiclesLoading] = useState(false)

  // Modals state
  const [reportModalOpen, setReportModalOpen] = useState(false)
  const [profileModalOpen, setProfileModalOpen] = useState(false)
  const [notificationsModalOpen, setNotificationsModalOpen] = useState(false)

  const refresh = () => setTick(t => t + 1)

  // Load vehicles list
  const loadVehicles = useCallback(async () => {
    setVehiclesLoading(true)
    try {
      const list = await api<VehicleSummary[]>('/api/vehicles')
      setVehicles(list)
    } catch (e) {
      console.error('Failed to load vehicles:', e)
    } finally {
      setVehiclesLoading(false)
    }
  }, [])

  // Load single vehicle detail
  const loadVehicleDetail = useCallback(async (id: string) => {
    try {
      const detail = await api<VehicleDetail>(`/api/vehicles/${id}`)
      setActiveVehicle(detail)
      return detail
    } catch (e) {
      console.error(`Failed to load vehicle ${id}:`, e)
      return null
    }
  }, [])

  // Navigation helpers for Vehicle management module
  const navigateToVehicles = useCallback((subView: 'overview' | 'detail' | 'add' = 'overview', id?: string) => {
    setActiveNav('vehicles')
    setVehicleSubView(subView)
    if (id) {
      setSelectedVehicleId(id)
      loadVehicleDetail(id)
      window.history.pushState({}, '', `/vehicles/${id}`)
    } else if (subView === 'add') {
      setSelectedVehicleId(null)
      window.history.pushState({}, '', '/vehicles/add')
    } else {
      setSelectedVehicleId(null)
      loadVehicles()
      window.history.pushState({}, '', '/vehicles')
    }
  }, [loadVehicleDetail, loadVehicles])

  const navigateToHome = useCallback(() => {
    setActiveNav('home')
    setVehicleSubView('overview')
    setSelectedVehicleId(null)
    window.history.pushState({}, '', '/')
  }, [])

  // Synchronize route from browser location
  const syncFromLocation = useCallback(() => {
    const path = window.location.pathname
    const q = new URLSearchParams(window.location.search)
    const viewParam = q.get('view')
    const idParam = q.get('id')

    if (path.startsWith('/vehicles') || viewParam === 'vehicles') {
      setActiveNav('vehicles')
      const pathSuffix = path.replace(/^\/vehicles\/?/, '').trim()
      const pathAction = pathSuffix.split('/')[0]

      if (pathAction === 'add' || q.get('action') === 'add') {
        setVehicleSubView('add')
        setSelectedVehicleId(null)
      } else if (pathAction && pathAction.length > 0) {
        setVehicleSubView('detail')
        setSelectedVehicleId(pathAction)
        loadVehicleDetail(pathAction)
      } else if (idParam) {
        setVehicleSubView('detail')
        setSelectedVehicleId(idParam)
        loadVehicleDetail(idParam)
      } else {
        setVehicleSubView('overview')
        setSelectedVehicleId(null)
        loadVehicles()
      }
    } else if (path === '/' && !viewParam) {
      setActiveNav('home')
    }
  }, [loadVehicleDetail, loadVehicles])

  // Initialize and handle URL params + popstate history listener
  useEffect(() => {
    const q = new URLSearchParams(window.location.search)
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

      // Initial route sync
      syncFromLocation()

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

    window.addEventListener('popstate', syncFromLocation)
    return () => window.removeEventListener('popstate', syncFromLocation)
  }, [syncFromLocation])

  // Load vehicles whenever user changes
  useEffect(() => {
    if (user) {
      loadVehicles()
    }
  }, [user, loadVehicles])

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
      navigateToHome()
    } else if (nav === 'vehicles') {
      navigateToVehicles('overview')
    } else if (nav === 'cases') {
      ensureCaseAndNavigate('dashboard', 'cases')
    } else if (nav === 'documents') {
      ensureCaseAndNavigate('documents', 'documents')
    } else if (nav === 'ai-assistant') {
      ensureCaseAndNavigate('chat', 'ai-assistant')
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
        loadVehicles()
      }
    } catch (e) {
      console.error(e)
    }
  }

  const logout = () => {
    setUser('')
    setU(null)
    setKase(null)
    setVehicles([])
    setActiveVehicle(null)
    navigateToHome()
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
    loadVehicles()
  }

  // Vehicle action handlers
  const handleCreateVehicle = async (
    data: VehicleFormData,
    photoFile: File | null,
    docFiles: { type: string; file: File }[]
  ) => {
    try {
      const created = await api<VehicleDetail>('/api/vehicles', {
        method: 'POST',
        body: data,
      })

      if (photoFile && created?.id) {
        try {
          const pForm = new FormData()
          pForm.append('file', photoFile)
          pForm.append('category', 'main')
          pForm.append('is_primary', 'true')
          await api(`/api/vehicles/${created.id}/photos`, {
            method: 'POST',
            form: pForm,
          })
        } catch (pe) {
          console.error('Failed to upload primary photo for created vehicle:', pe)
        }
      }

      if (docFiles && docFiles.length > 0 && created?.id) {
        for (const df of docFiles) {
          try {
            const dForm = new FormData()
            dForm.append('file', df.file)
            dForm.append('doc_type', df.type)
            dForm.append('doc_name', df.file.name)
            await api(`/api/vehicles/${created.id}/documents`, {
              method: 'POST',
              form: dForm,
            })
          } catch (de) {
            console.error(`Failed to upload doc ${df.type} for created vehicle:`, de)
          }
        }
      }

      await loadVehicles()
      if (created?.id) {
        navigateToVehicles('detail', created.id)
      } else {
        navigateToVehicles('overview')
      }
    } catch (e: any) {
      console.error('Error creating vehicle:', e)
      throw e
    }
  }

  const handleUpdateVehicle = async (updatedData: Partial<VehicleFormData>) => {
    if (!activeVehicle) return
    try {
      const updated = await api<VehicleDetail>(`/api/vehicles/${activeVehicle.id}`, {
        method: 'PUT',
        body: updatedData,
      })
      setActiveVehicle(updated)
      await loadVehicles()
    } catch (e: any) {
      console.error('Error updating vehicle:', e)
      throw e
    }
  }

  const handleDeleteVehicle = async (vehicleId: string) => {
    try {
      await api(`/api/vehicles/${vehicleId}`, { method: 'DELETE' })
      if (activeVehicle?.id === vehicleId) {
        setActiveVehicle(null)
      }
      await loadVehicles()
      navigateToVehicles('overview')
    } catch (e: any) {
      console.error('Error deleting vehicle:', e)
      throw e
    }
  }

  const handleUploadPhoto = async (file: File, category: string, isPrimary: boolean) => {
    if (!activeVehicle) return
    const fd = new FormData()
    fd.append('file', file)
    fd.append('category', category)
    fd.append('is_primary', String(isPrimary))
    await api(`/api/vehicles/${activeVehicle.id}/photos`, { method: 'POST', form: fd })
    await loadVehicleDetail(activeVehicle.id)
    await loadVehicles()
  }

  const handleSetPrimaryPhoto = async (photoId: string) => {
    if (!activeVehicle) return
    await api(`/api/vehicles/${activeVehicle.id}/photos/${photoId}/primary`, { method: 'POST' })
    await loadVehicleDetail(activeVehicle.id)
    await loadVehicles()
  }

  const handleDeletePhoto = async (photoId: string) => {
    if (!activeVehicle) return
    await api(`/api/vehicles/${activeVehicle.id}/photos/${photoId}`, { method: 'DELETE' })
    await loadVehicleDetail(activeVehicle.id)
    await loadVehicles()
  }

  const handleUploadDocument = async (file: File, docType: string, docName: string, expiryDate?: string) => {
    if (!activeVehicle) return
    const fd = new FormData()
    fd.append('file', file)
    fd.append('doc_type', docType)
    fd.append('doc_name', docName)
    if (expiryDate) {
      fd.append('expiry_date', expiryDate)
    }
    await api(`/api/vehicles/${activeVehicle.id}/documents`, { method: 'POST', form: fd })
    await loadVehicleDetail(activeVehicle.id)
    await loadVehicles()
  }

  const handleDeleteDocument = async (docId: string) => {
    if (!activeVehicle) return
    await api(`/api/vehicles/${activeVehicle.id}/documents/${docId}`, { method: 'DELETE' })
    await loadVehicleDetail(activeVehicle.id)
    await loadVehicles()
  }

  // Check if current view is a Case workspace view
  const isCaseView = ['cases', 'documents', 'ai-assistant'].includes(activeNav) && !!kase

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
        onOpenVehicles={() => navigateToVehicles('overview')}
        activeCaseNumber={kase?.case_number}
      />

      {/* Case Sub-Navigation Bar (shown only when inside case workspace) */}
      {isCaseView && (
        <div className="bg-navy-900 border-b border-navy-800 text-white">
          <div className="max-w-6xl mx-auto px-4 sm:px-6">
            <div className="flex items-center justify-between py-2 border-b border-navy-800/80 text-xs text-slate-400">
              <div className="flex items-center gap-2">
                <button
                  onClick={navigateToHome}
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
      <main className={`flex-1 ${isCaseView && caseTab !== 'mcp' ? 'pb-48 sm:pb-24' : ''}`}>
        
        {/* VIEW 1: Homepage */}
        {activeNav === 'home' && (
          <Homepage
            user={user}
            onReportAccident={() => setReportModalOpen(true)}
            onOpenVehicles={() => navigateToVehicles('overview')}
            onOpenDocuments={() => ensureCaseAndNavigate('documents', 'documents')}
            onOpenCases={() => ensureCaseAndNavigate('dashboard', 'cases')}
            onOpenAI={() => ensureCaseAndNavigate('chat', 'ai-assistant')}
            onOpenProfile={() => setProfileModalOpen(true)}
            onDemoStaged={handleDemoStaged}
          />
        )}

        {/* VIEW 2: Complete Vehicle Management Module */}
        {activeNav === 'vehicles' && (
          <>
            {vehicleSubView === 'overview' && (
              <VehiclesOverview
                vehicles={vehicles}
                loading={vehiclesLoading}
                onAddVehicle={() => navigateToVehicles('add')}
                onViewDetails={(id) => navigateToVehicles('detail', id)}
                onEditVehicle={(v) => navigateToVehicles('detail', v.id)}
                onDeleteVehicle={handleDeleteVehicle}
                onBackHome={navigateToHome}
              />
            )}

            {vehicleSubView === 'add' && (
              <AddVehicleWizard
                onCancel={() => navigateToVehicles('overview')}
                onSave={handleCreateVehicle}
              />
            )}

            {vehicleSubView === 'detail' && (
              activeVehicle ? (
                <VehicleDetails
                  key={selectedVehicleId || activeVehicle.id}
                  vehicle={activeVehicle}
                  onBack={() => navigateToVehicles('overview')}
                  onUpdateVehicle={handleUpdateVehicle}
                  onUploadPhoto={handleUploadPhoto}
                  onSetPrimaryPhoto={handleSetPrimaryPhoto}
                  onDeletePhoto={handleDeletePhoto}
                  onUploadDocument={handleUploadDocument}
                  onDeleteDocument={handleDeleteDocument}
                  onDeleteVehicle={async () => {
                    if (activeVehicle) await handleDeleteVehicle(activeVehicle.id)
                  }}
                />
              ) : (
                <div className="max-w-6xl mx-auto px-4 sm:px-6 py-20 text-center">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-navy-900 border-t-accent-500 mb-4" />
                  <p className="text-sm font-semibold text-slate-600">Loading vehicle details...</p>
                  <div className="mt-4">
                    <button
                      onClick={() => navigateToVehicles('overview')}
                      className="text-xs text-accent-500 font-semibold hover:underline"
                    >
                      ← Back to My Vehicles
                    </button>
                  </div>
                </div>
              )
            )}
          </>
        )}

        {/* VIEW 3: Case Workspace View */}
        {isCaseView && (
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
        {activeNav !== 'home' && activeNav !== 'vehicles' && !kase && user && (
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
      {isCaseView && caseTab !== 'mcp' && (
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
