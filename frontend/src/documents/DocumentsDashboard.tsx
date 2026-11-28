import { useState, useMemo } from 'react'
import type { DocumentItem, DocumentSummary, VehicleOption } from './types'
import { api } from '../api'

interface DocumentsDashboardProps {
  documents: DocumentItem[]
  summary: DocumentSummary | null
  vehicles: VehicleOption[]
  loading: boolean
  onUploadDocument: () => void
  onPreviewDocument: (doc: DocumentItem) => void
  onEditDocument: (doc: DocumentItem) => void
  onReplaceFile: (doc: DocumentItem) => void
  onDeleteDocument: (docId: string) => void
  onBackHome: () => void
  onRefresh?: () => void
}

const CATEGORY_TABS = [
  { id: 'all', label: 'All Documents', icon: '📁' },
  { id: 'personal', label: 'Personal', icon: '👤' },
  { id: 'driving_licence', label: 'Driving Licence', icon: '🪪' },
  { id: 'vehicle', label: 'Vehicle Documents', icon: '🚗' },
  { id: 'insurance', label: 'Insurance', icon: '🛡️' },
  { id: 'medical', label: 'Medical Records', icon: '🏥', sensitive: true },
  { id: 'accident_case', label: 'Accident Cases', icon: '🚨' },
]

export function DocumentsDashboard({
  documents,
  summary,
  vehicles,
  loading,
  onUploadDocument,
  onPreviewDocument,
  onEditDocument,
  onReplaceFile,
  onDeleteDocument,
  onBackHome,
  onRefresh,
}: DocumentsDashboardProps) {
  const [activeCategory, setActiveCategory] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStatus, setSelectedStatus] = useState('all')
  const [selectedVehicle, setSelectedVehicle] = useState('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [verifyingDocId, setVerifyingDocId] = useState<string | null>(null)
  const [verifyNotice, setVerifyNotice] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  const handleVerifyDoc = async (doc: DocumentItem) => {
    try {
      setVerifyingDocId(doc.id)
      setVerifyNotice(null)
      const res = await api(`/api/verify/documents/${doc.id}/verify`, { method: 'POST' })
      if (res.status === 'verified') {
        setVerifyNotice({
          type: 'success',
          msg: `"${doc.document_name}" verified successfully (Ref: ${res.reference_id || 'Registry'}).`,
        })
        if (onRefresh) onRefresh()
      } else {
        setVerifyNotice({
          type: 'error',
          msg: `Verification failed: ${res.reason || 'Could not verify document.'}`,
        })
      }
    } catch (err: any) {
      setVerifyNotice({
        type: 'error',
        msg: err?.message || 'Verification failed. Please retry.',
      })
    } finally {
      setVerifyingDocId(null)
    }
  }

  // Filtered documents
  const filteredDocs = useMemo(() => {
    return documents.filter((doc) => {
      // Category filter
      if (activeCategory !== 'all') {
        if (activeCategory === 'personal' && !['personal', 'identity', 'address_proof'].includes(doc.category)) {
          return false
        }
        if (activeCategory === 'driving_licence' && doc.category !== 'driving_licence' && doc.document_type !== 'driving_licence') {
          return false
        }
        if (activeCategory === 'vehicle' && doc.category !== 'vehicle' && doc.resource_type !== 'VEHICLE') {
          return false
        }
        if (activeCategory === 'insurance' && doc.category !== 'insurance' && !['insurance', 'insurance_policy'].includes(doc.document_type)) {
          return false
        }
        if (activeCategory === 'medical' && doc.category !== 'medical' && !['medical_report', 'hospital_bill', 'prescription'].includes(doc.document_type)) {
          return false
        }
        if (activeCategory === 'accident_case' && doc.category !== 'accident_case' && doc.resource_type !== 'ACCIDENT_CASE') {
          return false
        }
      }

      // Vehicle filter
      if (selectedVehicle !== 'all') {
        if (doc.resource_type !== 'VEHICLE' || doc.resource_id !== selectedVehicle) {
          return false
        }
      }

      // Status filter
      if (selectedStatus !== 'all' && doc.status !== selectedStatus) {
        return false
      }

      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim()
        const matchesName = doc.document_name.toLowerCase().includes(q)
        const matchesFile = doc.file_name.toLowerCase().includes(q)
        const matchesNumber = doc.document_number ? doc.document_number.toLowerCase().includes(q) : false
        const matchesAuth = doc.issuing_authority ? doc.issuing_authority.toLowerCase().includes(q) : false
        const matchesLabel = doc.resource_label ? doc.resource_label.toLowerCase().includes(q) : false
        if (!matchesName && !matchesFile && !matchesNumber && !matchesAuth && !matchesLabel) {
          return false
        }
      }

      return true
    })
  }, [documents, activeCategory, selectedVehicle, selectedStatus, searchQuery])

  // Category counts from summary
  const getTabCount = (tabId: string) => {
    if (!summary) return 0
    if (tabId === 'all') return summary.total
    return summary.categories[tabId] || 0
  }

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-800 pb-24">
      
      {/* ========================================================= HEADER BAR */}
      <div className="bg-[#091528] text-white border-b border-[#13243d]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
          
          {/* Breadcrumbs & Home Navigation */}
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 mb-2">
            <button
              onClick={onBackHome}
              className="hover:text-white transition flex items-center gap-1 cursor-pointer"
            >
              <span>Home</span>
            </button>
            <span>/</span>
            <span className="text-[#ff7518] font-bold">My Documents</span>
          </div>

          {/* Title & Action */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
                <span>My Documents</span>
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-[#1b2f4d] text-slate-300 border border-[#2b4d7e]">
                  Document Wallet
                </span>
              </h1>
              <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-xl font-normal">
                Securely manage your personal, vehicle and accident-related documents in one centralized repository.
              </p>
            </div>

            <button
              onClick={onUploadDocument}
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-full font-bold text-xs sm:text-sm text-white bg-[#ff7518] hover:bg-[#ea6309] shadow-lg shadow-[#ff7518]/25 transition hover:scale-[1.02] cursor-pointer self-start sm:self-auto"
            >
              <span>+</span>
              <span>Upload Document</span>
            </button>
          </div>

        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 -mt-4 sm:-mt-6">
        
        {/* ========================================================= 4 SUMMARY STAT CARDS */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-8">
          
          {/* Total Documents Card */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-4 sm:p-5 shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Total Documents
              </span>
              <span className="text-2xl sm:text-3xl font-extrabold text-navy-950 mt-1 block">
                {summary ? summary.total : 0}
              </span>
              <span className="text-[11px] text-slate-500 font-medium">In central wallet</span>
            </div>
            <div className="h-11 w-11 rounded-full bg-[#ebf3ff] text-[#2563eb] flex items-center justify-center text-lg flex-shrink-0">
              📁
            </div>
          </div>

          {/* Valid Documents Card */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-4 sm:p-5 shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Valid Documents
              </span>
              <span className="text-2xl sm:text-3xl font-extrabold text-emerald-600 mt-1 block">
                {summary ? summary.valid : 0}
              </span>
              <span className="text-[11px] text-emerald-700 font-medium">Active & verified</span>
            </div>
            <div className="h-11 w-11 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center text-lg flex-shrink-0">
              ✓
            </div>
          </div>

          {/* Expiring Soon Card */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-4 sm:p-5 shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Expiring Soon
              </span>
              <span className="text-2xl sm:text-3xl font-extrabold text-amber-600 mt-1 block">
                {summary ? summary.expiring_soon : 0}
              </span>
              <span className="text-[11px] text-amber-700 font-medium">Within 30 days</span>
            </div>
            <div className="h-11 w-11 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center text-lg flex-shrink-0">
              ⚠️
            </div>
          </div>

          {/* Expired Documents Card */}
          <div className="bg-white rounded-2xl border border-slate-200/90 p-4 sm:p-5 shadow-sm flex items-center justify-between">
            <div>
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Expired
              </span>
              <span className="text-2xl sm:text-3xl font-extrabold text-red-600 mt-1 block">
                {summary ? summary.expired : 0}
              </span>
              <span className="text-[11px] text-red-600 font-medium">Needs renewal</span>
            </div>
            <div className="h-11 w-11 rounded-full bg-red-50 text-red-600 flex items-center justify-center text-lg flex-shrink-0">
              🚨
            </div>
          </div>

        </div>

        {/* ========================================================= CATEGORY NAV TABS */}
        <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-2 mb-6 overflow-x-auto">
          <div className="flex items-center gap-1.5 min-w-max">
            {CATEGORY_TABS.map((tab) => {
              const isActive = activeCategory === tab.id
              const count = getTabCount(tab.id)
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveCategory(tab.id)}
                  className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer ${
                    isActive
                      ? 'bg-[#091528] text-white shadow-sm'
                      : 'text-slate-600 hover:text-navy-950 hover:bg-slate-100'
                  }`}
                >
                  <span>{tab.icon}</span>
                  <span>{tab.label}</span>
                  {tab.sensitive && (
                    <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-400/20 text-amber-400">
                      🔒 Sensitive
                    </span>
                  )}
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                      isActive ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Vehicle Sub-selector (shown when viewing Vehicle Documents or All) */}
        {(activeCategory === 'vehicle' || activeCategory === 'all') && vehicles.length > 0 && (
          <div className="mb-6 flex items-center gap-2 overflow-x-auto py-1">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex-shrink-0">
              Filter by Vehicle:
            </span>
            <button
              onClick={() => setSelectedVehicle('all')}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition cursor-pointer ${
                selectedVehicle === 'all'
                  ? 'bg-[#2563eb] text-white'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              All Vehicles
            </button>
            {vehicles.map((v) => (
              <button
                key={v.id}
                onClick={() => setSelectedVehicle(v.id)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                  selectedVehicle === v.id
                    ? 'bg-[#2563eb] text-white'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                <span>🚗</span>
                <span>{v.registration_number}</span>
                <span className="text-[10px] opacity-75">({v.model})</span>
              </button>
            ))}
          </div>
        )}

        {/* ========================================================= CONTROLS & SEARCH BAR */}
        <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-4 mb-6 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          
          {/* Search Input */}
          <div className="relative flex-1">
            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
              🔍
            </span>
            <input
              type="text"
              placeholder="Search by document name, number, authority or notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-8 py-2 text-xs font-medium rounded-xl border border-slate-200 bg-slate-50/70 focus:outline-none focus:ring-2 focus:ring-navy-900 focus:bg-white text-navy-950"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs p-1"
              >
                ✕
              </button>
            )}
          </div>

          {/* Filters & View Toggles */}
          <div className="flex items-center gap-2.5">
            {/* Status Dropdown */}
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="text-xs font-semibold rounded-xl border border-slate-200 px-3 py-2 bg-slate-50/70 text-slate-700 focus:outline-none focus:ring-2 focus:ring-navy-900 cursor-pointer"
            >
              <option value="all">Status: All</option>
              <option value="valid">Valid Only</option>
              <option value="expiring_soon">Expiring Soon</option>
              <option value="expired">Expired</option>
            </select>

            {/* View Mode Toggle */}
            <div className="flex items-center bg-slate-100 p-0.5 rounded-xl border border-slate-200">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                  viewMode === 'grid'
                    ? 'bg-white text-navy-950 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
                title="Grid View"
              >
                ▦ Grid
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-1.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                  viewMode === 'list'
                    ? 'bg-white text-navy-950 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
                title="List View"
              >
                ☰ List
              </button>
            </div>
          </div>

        </div>

        {verifyNotice && (
          <div className={`p-4 rounded-xl text-xs font-medium flex items-center justify-between gap-2 ${
            verifyNotice.type === 'success'
              ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}>
            <span>{verifyNotice.msg}</span>
            <button onClick={() => setVerifyNotice(null)} className="text-slate-400 hover:text-slate-700">✕</button>
          </div>
        )}

        {/* ========================================================= DOCUMENTS LISTING */}
        {loading ? (
          <div className="card py-16 text-center space-y-3">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-navy-900 border-t-accent-500" />
            <p className="text-xs font-semibold text-slate-500">Loading document wallet...</p>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="card text-center py-16 px-4 space-y-4">
            <div className="h-14 w-14 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center text-2xl">
              📂
            </div>
            <div>
              <h3 className="text-base font-bold text-navy-950">No documents found</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                {searchQuery || selectedStatus !== 'all' || activeCategory !== 'all'
                  ? 'No documents match your active filters. Try clearing your search query or status filter.'
                  : 'Your document wallet is empty. Click "+ Upload Document" to add your personal, vehicle or case documents.'}
              </p>
            </div>
            <div>
              <button
                onClick={onUploadDocument}
                className="btn-accent text-xs"
              >
                + Upload First Document
              </button>
            </div>
          </div>
        ) : viewMode === 'grid' ? (
          /* ========================================== GRID VIEW */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
            {filteredDocs.map((doc) => {
              const isPdf = doc.mime_type === 'application/pdf' || doc.file_name.endsWith('.pdf')
              const statusPill =
                doc.status === 'valid'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : doc.status === 'expiring_soon'
                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                  : 'bg-red-50 text-red-700 border-red-200'

              return (
                <div
                  key={doc.id}
                  className="bg-white rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between overflow-hidden group hover:border-[#1e3b63]"
                >
                  <div className="p-5 space-y-3.5">
                    {/* Card Top: Thumbnail/Icon & Status Chip */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-3">
                        <div
                          onClick={() => onPreviewDocument(doc)}
                          className={`h-11 w-11 rounded-xl flex items-center justify-center text-lg font-bold flex-shrink-0 cursor-pointer transition group-hover:scale-105 ${
                            isPdf ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'
                          }`}
                        >
                          {isPdf ? '📄' : '🖼️'}
                        </div>
                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                            {doc.category.replace('_', ' ')}
                          </span>
                          <h3
                            onClick={() => onPreviewDocument(doc)}
                            className="text-sm font-bold text-navy-950 group-hover:text-accent-500 transition line-clamp-1 cursor-pointer"
                            title={doc.document_name}
                          >
                            {doc.document_name}
                          </h3>
                        </div>
                      </div>

                      {/* Status and Verification Pills */}
                      <div className="flex flex-col items-end gap-1 flex-shrink-0">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border capitalize ${statusPill}`}>
                          {doc.status.replace('_', ' ')}
                        </span>
                        {doc.verification_status === 'verified' ? (
                          <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                            ✓ Verified
                          </span>
                        ) : doc.verification_status === 'failed' ? (
                          <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-red-50 text-red-700 border border-red-200">
                            ✗ Failed
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                            Unverified
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Resource Association Chip */}
                    <div className="flex items-center gap-1.5 p-2 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                      <span className="text-sm flex-shrink-0">
                        {doc.resource_type === 'VEHICLE'
                          ? '🚗'
                          : doc.resource_type === 'ACCIDENT_CASE'
                          ? '🚨'
                          : '👤'}
                      </span>
                      <span className="font-semibold text-slate-700 truncate" title={doc.resource_label}>
                        {doc.resource_label}
                      </span>
                    </div>

                    {/* Metadata details */}
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-500 pt-1">
                      <div>
                        <span className="text-slate-400 block text-[10px]">DOC NUMBER</span>
                        <span className="font-medium text-slate-700 font-mono truncate block">
                          {doc.document_number || '—'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px]">EXPIRY DATE</span>
                        <span className="font-medium text-slate-700 truncate block">
                          {doc.expiry_date
                            ? new Date(doc.expiry_date).toLocaleDateString('en-IN')
                            : 'No Expiry'}
                        </span>
                      </div>
                    </div>

                    {doc.days_left !== null && doc.days_left !== undefined && doc.status !== 'valid' && (
                      <div className="text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-1 rounded-lg border border-amber-200">
                        {doc.days_left < 0
                          ? `🚨 Expired ${Math.abs(doc.days_left)} days ago`
                          : `⚠️ Expires in ${doc.days_left} days`}
                      </div>
                    )}
                  </div>

                  {/* Card Action Footer */}
                  <div className="px-5 py-3 bg-slate-50/70 border-t border-slate-100 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => onPreviewDocument(doc)}
                        className="font-bold text-accent-500 hover:text-accent-600 transition flex items-center gap-1 cursor-pointer"
                      >
                        <span>Preview</span>
                        <span>→</span>
                      </button>
                      {doc.verification_status !== 'verified' && (
                        <button
                          onClick={() => handleVerifyDoc(doc)}
                          disabled={verifyingDocId === doc.id}
                          className="px-2 py-0.5 text-[11px] font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition disabled:opacity-50 cursor-pointer"
                        >
                          {verifyingDocId === doc.id ? '...' : doc.verification_status === 'failed' ? 'Retry' : 'Verify'}
                        </button>
                      )}
                      <a
                        href={`${doc.download_url}?download=true`}
                        download={doc.file_name}
                        className="text-slate-500 hover:text-navy-950 transition p-1"
                        title="Download file"
                      >
                        ⬇
                      </a>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => onEditDocument(doc)}
                        className="text-slate-400 hover:text-navy-950 p-1 transition"
                        title="Edit metadata"
                      >
                        ✏️
                      </button>
                      <button
                        onClick={() => onReplaceFile(doc)}
                        className="text-slate-400 hover:text-navy-950 p-1 transition"
                        title="Replace file"
                      >
                        🔄
                      </button>
                      <button
                        onClick={() => setDeleteConfirmId(doc.id)}
                        className="text-slate-400 hover:text-red-600 p-1 transition"
                        title="Delete document"
                      >
                        🗑
                      </button>
                    </div>
                  </div>

                  {/* Inline Delete Confirmation */}
                  {deleteConfirmId === doc.id && (
                    <div className="p-3 bg-red-50 border-t border-red-200 text-xs text-center space-y-2 animate-fade-in">
                      <span className="font-bold text-red-700 block">Delete this document?</span>
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => setDeleteConfirmId(null)}
                          className="px-2.5 py-1 text-[11px] font-semibold bg-white border border-slate-200 rounded"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => {
                            onDeleteDocument(doc.id)
                            setDeleteConfirmId(null)
                          }}
                          className="px-2.5 py-1 text-[11px] font-bold bg-red-600 text-white rounded shadow-sm"
                        >
                          Confirm
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          /* ========================================== LIST VIEW */
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#091528] text-white text-[11px] font-bold uppercase tracking-wider">
                  <tr>
                    <th className="py-3.5 px-4">Document</th>
                    <th className="py-3.5 px-4">Category</th>
                    <th className="py-3.5 px-4">Linked Resource</th>
                    <th className="py-3.5 px-4">Expiry Date</th>
                    <th className="py-3.5 px-4">Status</th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                  {filteredDocs.map((doc) => {
                    const isPdf = doc.mime_type === 'application/pdf' || doc.file_name.endsWith('.pdf')
                    const statusPill =
                      doc.status === 'valid'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : doc.status === 'expiring_soon'
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-red-50 text-red-700 border-red-200'

                    return (
                      <tr key={doc.id} className="hover:bg-slate-50/70 transition">
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2.5">
                            <span className="text-base">{isPdf ? '📄' : '🖼️'}</span>
                            <div>
                              <div
                                onClick={() => onPreviewDocument(doc)}
                                className="font-bold text-navy-950 hover:text-accent-500 cursor-pointer"
                              >
                                {doc.document_name}
                              </div>
                              <div className="text-[10px] text-slate-400">
                                {doc.file_name} · {(doc.file_size / 1024).toFixed(1)} KB
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-4 capitalize">
                          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px] font-bold">
                            {doc.category.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className="text-xs font-semibold text-slate-700">
                            {doc.resource_label}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          {doc.expiry_date
                            ? new Date(doc.expiry_date).toLocaleDateString('en-IN')
                            : '—'}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border capitalize ${statusPill}`}>
                            {doc.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => onPreviewDocument(doc)}
                              className="font-bold text-accent-500 hover:underline"
                            >
                              Preview
                            </button>
                            <a
                              href={`${doc.download_url}?download=true`}
                              download={doc.file_name}
                              className="text-slate-400 hover:text-navy-950"
                              title="Download"
                            >
                              ⬇
                            </a>
                            <button
                              onClick={() => onEditDocument(doc)}
                              className="text-slate-400 hover:text-navy-950"
                              title="Edit"
                            >
                              ✏️
                            </button>
                            <button
                              onClick={() => onDeleteDocument(doc.id)}
                              className="text-slate-400 hover:text-red-600"
                              title="Delete"
                            >
                              🗑
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>

    </div>
  )
}
