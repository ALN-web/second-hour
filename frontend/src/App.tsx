import { useCallback, useEffect, useState } from 'react'
import { api, getUser, setUser } from './api'
import { McpTicker } from './Views'
import { Navbar, type NavItem } from './components/Navbar'
import { Homepage } from './components/Homepage'
import { ReportAccidentModal, ProfileModal, NotificationsModal } from './components/Modals'
import { VehiclesOverview } from './vehicles/VehiclesOverview'
import { VehicleDetails } from './vehicles/VehicleDetails'
import { AddVehicleWizard } from './vehicles/AddVehicleWizard'
import { DocumentsDashboard } from './documents/DocumentsDashboard'
import { UploadDocumentWizard } from './documents/UploadDocumentWizard'
import { DocumentViewerModal } from './documents/DocumentViewerModal'
import { EditDocumentModal } from './documents/EditDocumentModal'
import { ReplaceFileModal } from './documents/ReplaceFileModal'
import { CasesOverview } from './cases/CasesOverview'
import { CaseWorkspace } from './cases/CaseWorkspace'
import { AssistantModule } from './assistant/AssistantModule'
import type { VehicleSummary, VehicleDetail, VehicleFormData } from './vehicles/types'
import type { DocumentItem, DocumentSummary, UploadDocumentFormData } from './documents/types'

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

export default function App() {
  const [user, setU] = useState<User | null>(null)
  const [kase, setKase] = useState<CaseRow | null>(null)
  const [caseRows, setCaseRows] = useState<CaseRow[]>([])
  const [activeNav, setActiveNav] = useState<NavItem>('home')
  const [caseTab, setCaseTab] = useState<CaseTab>('dashboard')
  const [, setTick] = useState(0)

  // Vehicles Module state
  const [vehicleSubView, setVehicleSubView] = useState<'overview' | 'detail' | 'add'>('overview')
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null)
  const [vehicles, setVehicles] = useState<VehicleSummary[]>([])
  const [activeVehicle, setActiveVehicle] = useState<VehicleDetail | null>(null)
  const [vehiclesLoading, setVehiclesLoading] = useState(false)

  // Documents Module state
  const [documentsSubView, setDocumentsSubView] = useState<'dashboard' | 'upload'>('dashboard')
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [documentSummary, setDocumentSummary] = useState<DocumentSummary | null>(null)
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [previewingDoc, setPreviewingDoc] = useState<DocumentItem | null>(null)
  const [editingDoc, setEditingDoc] = useState<DocumentItem | null>(null)
  const [replacingDoc, setReplacingDoc] = useState<DocumentItem | null>(null)

  // Cases Module state
  const [caseSubView, setCaseSubView] = useState<'overview' | 'workspace'>('overview')
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null)

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

  // Load documents list and summary
  const loadDocuments = useCallback(async () => {
    setDocumentsLoading(true)
    try {
      const [docs, sum] = await Promise.all([
        api<DocumentItem[]>('/api/documents'),
        api<DocumentSummary>('/api/documents/summary'),
      ])
      setDocuments(docs)
      setDocumentSummary(sum)
    } catch (e) {
      console.error('Failed to load documents:', e)
    } finally {
      setDocumentsLoading(false)
    }
  }, [])

  // Navigation helpers for Vehicle management module
  const navigateToVehicles = useCallback((subView: 'overview' | 'detail' | 'add' = 'overview', id?: string) => {
    setActiveNav('vehicles')
    setVehicleSubView(subView)
    setSelectedVehicleId(id || null)
    if (id) {
      loadVehicleDetail(id)
      window.history.pushState({}, '', `/vehicles/${id}`)
    } else if (subView === 'add') {
      window.history.pushState({}, '', '/vehicles/add')
    } else {
      loadVehicles()
      window.history.pushState({}, '', '/vehicles')
    }
  }, [loadVehicleDetail, loadVehicles])

  // Navigation helpers for Documents management module
  const navigateToDocuments = useCallback((subView: 'dashboard' | 'upload' = 'dashboard') => {
    setActiveNav('documents')
    setDocumentsSubView(subView)
    loadDocuments()
    loadVehicles()
    window.history.pushState({}, '', subView === 'upload' ? '/documents/upload' : '/documents')
  }, [loadDocuments, loadVehicles])

  // Navigation helpers for Cases management module
  const navigateToCases = useCallback((subView: 'overview' | 'workspace' = 'overview', id?: string) => {
    setActiveNav('cases')
    setCaseSubView(subView)
    setSelectedCaseId(id || null)
    if (id) {
      window.history.pushState({}, '', `/cases/${id}`)
    } else {
      window.history.pushState({}, '', '/cases')
    }
  }, [])

  // Navigation helpers for AI Assistant module
  const navigateToAIAssistant = useCallback(() => {
    setActiveNav('ai-assistant')
    window.history.pushState({}, '', '/ai-assistant')
  }, [])

  const navigateToHome = useCallback(() => {
    setActiveNav('home')
    setVehicleSubView('overview')
    setSelectedVehicleId(null)
    setDocumentsSubView('dashboard')
    setCaseSubView('overview')
    setSelectedCaseId(null)
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
    } else if (path.startsWith('/documents') || viewParam === 'documents') {
      setActiveNav('documents')
      if (path.includes('/upload') || q.get('action') === 'upload') {
        setDocumentsSubView('upload')
      } else {
        setDocumentsSubView('dashboard')
      }
      loadDocuments()
      loadVehicles()
    } else if (path.startsWith('/cases') || viewParam === 'cases') {
      setActiveNav('cases')
      const pathSuffix = path.replace(/^\/cases\/?/, '').trim()
      const pathAction = pathSuffix.split('/')[0]

      if (pathAction && pathAction.length > 0 && pathAction !== 'overview') {
        setCaseSubView('workspace')
        setSelectedCaseId(pathAction)
      } else if (idParam) {
        setCaseSubView('workspace')
        setSelectedCaseId(idParam)
      } else {
        setCaseSubView('overview')
        setSelectedCaseId(null)
      }
    } else if (path.startsWith('/ai-assistant') || viewParam === 'ai-assistant') {
      setActiveNav('ai-assistant')
    } else if (path === '/' && !viewParam) {
      setActiveNav('home')
    }
  }, [loadDocuments, loadVehicleDetail, loadVehicles])

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

      api<CaseRow[]>('/api/cases').then((cs) => {
        setCaseRows(cs)
        if (wantCase) {
          const c = cs.find(x => x.case_id === wantCase)
          if (c) {
            setKase(c)
            setActiveNav('cases')
            if (wantTab && CASE_TABS.some(x => x.id === wantTab)) {
              setCaseTab(wantTab as CaseTab)
            }
          }
        }
      }).catch(() => {})
    }).catch(() => {})

    window.addEventListener('popstate', syncFromLocation)
    return () => window.removeEventListener('popstate', syncFromLocation)
  }, [syncFromLocation])

  // Load vehicles and documents whenever user changes
  useEffect(() => {
    if (user) {
      loadVehicles()
      loadDocuments()
    }
  }, [user, loadVehicles, loadDocuments])


  const handleNav = (nav: NavItem) => {
    if (nav === 'home') {
      navigateToHome()
    } else if (nav === 'vehicles') {
      navigateToVehicles('overview')
    } else if (nav === 'documents') {
      navigateToDocuments('dashboard')
    } else if (nav === 'cases') {
      navigateToCases('overview')
    } else if (nav === 'ai-assistant') {
      navigateToAIAssistant()
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
        loadDocuments()
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
    setDocuments([])
    setActiveVehicle(null)
    navigateToHome()
  }

  const handleCaseCreated = (newCase: any) => {
    const cId = newCase.case_id || 'case_demo'
    navigateToCases('workspace', cId)
    refresh()
  }

  const handleDemoStaged = (priyaUser: User) => {
    setU(priyaUser)
    api<CaseRow[]>('/api/cases').then((cs) => {
      setCaseRows(cs)
      const demo = cs.find(c => c.case_id === 'case_demo') || cs[0]
      if (demo) {
        setKase(demo)
        navigateToCases('workspace', demo.case_id)
        refresh()
      }
    }).catch(() => {})
    loadVehicles()
    loadDocuments()
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
      await loadDocuments()
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
      await loadDocuments()
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
      await loadDocuments()
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

  const handleUploadVehicleDocument = async (file: File, docType: string, docName: string, expiryDate?: string) => {
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
    await loadDocuments()
  }

  const handleDeleteVehicleDocument = async (docId: string) => {
    if (!activeVehicle) return
    await api(`/api/vehicles/${activeVehicle.id}/documents/${docId}`, { method: 'DELETE' })
    await loadVehicleDetail(activeVehicle.id)
    await loadVehicles()
    await loadDocuments()
  }

  // Document action handlers (Centralized Wallet)
  const handleCreateDocument = async (data: UploadDocumentFormData, file: File) => {
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('document_name', data.document_name)
      fd.append('category', data.category)
      fd.append('document_type', data.document_type)
      if (data.document_number) fd.append('document_number', data.document_number)
      if (data.issuing_authority) fd.append('issuing_authority', data.issuing_authority)
      if (data.issue_date) fd.append('issue_date', data.issue_date)
      if (data.expiry_date) fd.append('expiry_date', data.expiry_date)
      if (data.resource_type) fd.append('resource_type', data.resource_type)
      if (data.resource_id) fd.append('resource_id', data.resource_id)
      if (data.notes) fd.append('notes', data.notes)

      await api('/api/documents', {
        method: 'POST',
        form: fd,
      })
      await loadDocuments()
      await loadVehicles()
      navigateToDocuments('dashboard')
    } catch (e: any) {
      console.error('Failed to create document:', e)
      throw e
    }
  }

  const handleUpdateDocument = async (docId: string, updatedData: Partial<DocumentItem>) => {
    try {
      await api(`/api/documents/${docId}`, {
        method: 'PATCH',
        body: updatedData,
      })
      await loadDocuments()
      await loadVehicles()
    } catch (e: any) {
      console.error('Failed to update document:', e)
      throw e
    }
  }

  const handleReplaceFile = async (docId: string, newFile: File) => {
    try {
      const fd = new FormData()
      fd.append('file', newFile)
      await api(`/api/documents/${docId}/replace`, {
        method: 'POST',
        form: fd,
      })
      await loadDocuments()
      await loadVehicles()
    } catch (e: any) {
      console.error('Failed to replace document file:', e)
      throw e
    }
  }

  const handleDeleteDocument = async (docId: string) => {
    try {
      await api(`/api/documents/${docId}`, { method: 'DELETE' })
      await loadDocuments()
      await loadVehicles()
    } catch (e: any) {
      console.error('Failed to delete document:', e)
    }
  }

  // Check if current view is legacy AI Assistant / MCP panel view
  const isCaseView = activeNav === 'ai-assistant' && !!kase

  // Mapped options for selectors
  const vehicleOptions = vehicles.map(v => ({
    id: v.id,
    registration_number: v.registration_number,
    manufacturer: v.manufacturer,
    model: v.model,
  }))

  const caseOptions = caseRows.map(c => ({
    case_id: c.case_id,
    case_number: c.case_number,
    victim_display_name: c.victim_display_name,
    hospital_name: c.hospital_name,
  }))

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
                    if (t.id === 'chat') setActiveNav('ai-assistant')
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
            onOpenDocuments={() => navigateToDocuments('dashboard')}
            onOpenCases={() => navigateToCases('overview')}
            onOpenAI={navigateToAIAssistant}
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
                  onUploadDocument={handleUploadVehicleDocument}
                  onDeleteDocument={handleDeleteVehicleDocument}
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

        {/* VIEW 3: Dedicated Full-Screen Documents Management Module */}
        {activeNav === 'documents' && (
          <>
            {documentsSubView === 'dashboard' && (
              <DocumentsDashboard
                documents={documents}
                summary={documentSummary}
                vehicles={vehicleOptions}
                loading={documentsLoading}
                onUploadDocument={() => navigateToDocuments('upload')}
                onPreviewDocument={(doc) => setPreviewingDoc(doc)}
                onEditDocument={(doc) => setEditingDoc(doc)}
                onReplaceFile={(doc) => setReplacingDoc(doc)}
                onDeleteDocument={handleDeleteDocument}
                onBackHome={navigateToHome}
              />
            )}

            {documentsSubView === 'upload' && (
              <UploadDocumentWizard
                vehicles={vehicleOptions}
                cases={caseOptions}
                onCancel={() => navigateToDocuments('dashboard')}
                onSave={handleCreateDocument}
              />
            )}
          </>
        )}

        {/* VIEW 4: Dedicated Full-Screen Accident Cases Management Module */}
        {activeNav === 'cases' && (
          <>
            {caseSubView === 'overview' && (
              <CasesOverview
                onOpenCase={(id) => navigateToCases('workspace', id)}
                onReportAccident={() => setReportModalOpen(true)}
                onBackHome={navigateToHome}
              />
            )}

            {caseSubView === 'workspace' && (
              <CaseWorkspace
                key={selectedCaseId || 'case_demo'}
                caseId={selectedCaseId || 'case_demo'}
                onBackToCases={() => navigateToCases('overview')}
                onOpenVehicle={(vId) => navigateToVehicles(vId ? 'detail' : 'overview', vId)}
                onBackHome={navigateToHome}
              />
            )}
          </>
        )}

        {/* VIEW 5: Ask Second Hour AI Assistant */}
        {activeNav === 'ai-assistant' && (
          <AssistantModule
            user={user}
            onNavigateToVehicles={(vId) => navigateToVehicles(vId ? 'detail' : 'overview', vId)}
            onNavigateToDocuments={() => navigateToDocuments('dashboard')}
            onNavigateToCases={(caseId) => navigateToCases(caseId ? 'workspace' : 'overview', caseId)}
            onBackHome={navigateToHome}
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

      {/* Document View & Edit Modals */}
      <DocumentViewerModal
        document={previewingDoc}
        onClose={() => setPreviewingDoc(null)}
        onEdit={(doc) => {
          setPreviewingDoc(null)
          setEditingDoc(doc)
        }}
        onReplaceFile={(doc) => {
          setPreviewingDoc(null)
          setReplacingDoc(doc)
        }}
        onDelete={(docId) => {
          handleDeleteDocument(docId)
          setPreviewingDoc(null)
        }}
      />

      <EditDocumentModal
        document={editingDoc}
        onClose={() => setEditingDoc(null)}
        onSave={handleUpdateDocument}
      />

      <ReplaceFileModal
        document={replacingDoc}
        onClose={() => setReplacingDoc(null)}
        onReplace={handleReplaceFile}
      />

      {/* System Modals */}
      <ReportAccidentModal
        isOpen={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
        onCaseCreated={handleCaseCreated}
        vehicles={vehicleOptions}
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
