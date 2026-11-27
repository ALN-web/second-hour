import { useState } from 'react'
import type { VehicleDetail, VehiclePhoto, VehicleFormData } from './types'
import { api } from '../api'

interface VehicleDetailsProps {
  vehicle: VehicleDetail
  onBack: () => void
  onUpdateVehicle: (updatedData: Partial<VehicleFormData>) => Promise<void>
  onUploadPhoto: (file: File, category: string, isPrimary: boolean) => Promise<void>
  onSetPrimaryPhoto: (photoId: string) => Promise<void>
  onDeletePhoto: (photoId: string) => Promise<void>
  onUploadDocument: (file: File, docType: string, docName: string, expiryDate?: string) => Promise<void>
  onDeleteDocument: (docId: string) => Promise<void>
  onDeleteVehicle: () => Promise<void>
  onRefresh?: () => void
}

export function VehicleDetails({
  vehicle,
  onBack,
  onUpdateVehicle,
  onUploadPhoto,
  onSetPrimaryPhoto,
  onDeletePhoto,
  onUploadDocument,
  onDeleteDocument,
  onDeleteVehicle,
  onRefresh,
}: VehicleDetailsProps) {
  const [activeTab, setActiveTab] = useState<'specs' | 'photos' | 'documents' | 'insurance'>('specs')
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [lightboxPhoto, setLightboxPhoto] = useState<VehiclePhoto | null>(null)
  const [verifyingVahan, setVerifyingVahan] = useState(false)
  const [vahanNotice, setVahanNotice] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  const handleVerifyVahan = async () => {
    try {
      setVerifyingVahan(true)
      setVahanNotice(null)
      const res = await api(`/api/verify/vehicles/${vehicle.id}/vahan`, { method: 'POST' })
      if (res.status === 'verified') {
        setVahanNotice({
          type: 'success',
          msg: `Vehicle successfully verified against VAHAN/Parivahan (Ref: ${res.reference_id}).`,
        })
        if (onRefresh) onRefresh()
        else window.location.reload()
      } else {
        setVahanNotice({
          type: 'error',
          msg: `VAHAN verification failed: ${res.reason || 'Record not found in registry.'}`,
        })
      }
    } catch (err: any) {
      setVahanNotice({
        type: 'error',
        msg: err?.message || 'Failed to verify vehicle with VAHAN.',
      })
    } finally {
      setVerifyingVahan(false)
    }
  }

  // Photo upload form state
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [photoCategory, setPhotoCategory] = useState<string>('front')
  const [isPhotoPrimary, setIsPhotoPrimary] = useState(false)
  const [photoUploading, setPhotoUploading] = useState(false)

  // Document upload form state
  const [docFile, setDocFile] = useState<File | null>(null)
  const [docType, setDocType] = useState<string>('rc')
  const [docName, setDocName] = useState('')
  const [docExpiry, setDocExpiry] = useState('')
  const [docUploading, setDocUploading] = useState(false)

  // Edit form state
  const [editForm, setEditForm] = useState({
    registration_number: vehicle.registration_number,
    category: vehicle.category,
    manufacturer: vehicle.manufacturer,
    model: vehicle.model,
    variant: vehicle.variant || '',
    manufacturing_year: vehicle.manufacturing_year || new Date().getFullYear(),
    fuel_type: vehicle.fuel_type,
    color: vehicle.color || '',
    chassis_number: vehicle.chassis_number || '',
    engine_number: vehicle.engine_number || '',
    vin: vehicle.vin || '',
    engine_capacity: vehicle.engine_capacity || '',
    transmission: vehicle.transmission || 'Manual',
    owner_name: vehicle.owner_name || '',
    ownership_type: vehicle.ownership_type || 'Individual',
    relationship_to_user: vehicle.relationship_to_user || 'Self',
    insurance: {
      provider: vehicle.insurance.provider || '',
      policy_number: vehicle.insurance.policy_number || '',
      policy_type: vehicle.insurance.policy_type || 'Comprehensive',
      expiry_date: vehicle.insurance.expiry_date || '',
    },
  })
  const [savingEdit, setSavingEdit] = useState(false)
  const [message, setMessage] = useState('')

  const handlePhotoUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!photoFile) return
    setPhotoUploading(true)
    try {
      await onUploadPhoto(photoFile, photoCategory, isPhotoPrimary)
      setPhotoFile(null)
      setIsPhotoPrimary(false)
      setMessage('Photo uploaded successfully!')
      setTimeout(() => setMessage(''), 3000)
    } finally {
      setPhotoUploading(false)
    }
  }

  const handleDocUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!docFile) return
    setDocUploading(true)
    try {
      await onUploadDocument(docFile, docType, docName || docFile.name, docExpiry)
      setDocFile(null)
      setDocName('')
      setDocExpiry('')
      setMessage('Document uploaded successfully!')
      setTimeout(() => setMessage(''), 3000)
    } finally {
      setDocUploading(false)
    }
  }

  const handleSaveEdit = async () => {
    setSavingEdit(true)
    try {
      await onUpdateVehicle(editForm)
      setEditModalOpen(false)
      setMessage('Vehicle specifications updated successfully!')
      setTimeout(() => setMessage(''), 3000)
    } finally {
      setSavingEdit(false)
    }
  }

  const getInsuranceBadge = (ins: VehicleDetail['insurance']) => {
    if (ins.status === 'active') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          Insurance Active {ins.days_left !== null && `(${ins.days_left} days left)`}
        </span>
      )
    }
    if (ins.status === 'expiring_soon') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
          <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
          Expiring Soon {ins.days_left !== null && `(${ins.days_left} days left)`}
        </span>
      )
    }
    if (ins.status === 'expired') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
          <span className="h-2 w-2 rounded-full bg-red-500" />
          Insurance Expired
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
        No Policy Added
      </span>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 animate-fade-in">
      {/* Toast Feedback */}
      {message && (
        <div className="fixed top-6 right-6 z-50 p-4 rounded-xl bg-emerald-600 text-white text-xs font-bold shadow-2xl animate-fade-in flex items-center gap-2">
          <span>✓</span>
          <span>{message}</span>
        </div>
      )}

      {/* Breadcrumbs */}
      <nav className="flex items-center gap-2 text-xs text-slate-500 mb-4">
        <button onClick={onBack} className="hover:text-navy-950 font-medium transition cursor-pointer">
          Home
        </button>
        <span>/</span>
        <button onClick={onBack} className="hover:text-navy-950 font-medium transition cursor-pointer">
          My Vehicles
        </button>
        <span>/</span>
        <span className="text-slate-800 font-semibold">{vehicle.registration_number}</span>
      </nav>

      {/* ==================================================== HERO SECTION */}
      <div className="bg-navy-950 text-white rounded-3xl overflow-hidden shadow-xl border border-navy-900 mb-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 items-stretch">
          
          {/* Hero Left: Prominent Vehicle Photograph (7 cols) */}
          <div className="lg:col-span-7 relative h-72 sm:h-96 bg-black overflow-hidden group">
            {vehicle.main_image ? (
              <img
                src={vehicle.main_image}
                alt={`${vehicle.manufacturer} ${vehicle.model}`}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
              />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 bg-gradient-to-br from-navy-950 via-navy-900 to-navy-950">
                <span className="text-5xl mb-2">🚗</span>
                <span className="text-sm font-semibold">No Main Photo Uploaded</span>
              </div>
            )}

            {/* Quick Upload Photo Overlay */}
            <label className="absolute bottom-4 left-4 px-3 py-1.5 rounded-xl bg-black/70 hover:bg-black/90 text-white font-semibold text-xs backdrop-blur-md cursor-pointer transition flex items-center gap-2 border border-white/20">
              <span>📷</span>
              <span>Change Photo</span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    onUploadPhoto(e.target.files[0], 'main', true)
                  }
                }}
                className="hidden"
              />
            </label>
          </div>

          {/* Hero Right: Profile Details & Actions (5 cols) */}
          <div className="lg:col-span-5 p-6 sm:p-8 flex flex-col justify-between space-y-6">
            <div>
              {/* Registration Number Badge */}
              <div className="inline-block px-3.5 py-1 rounded-xl text-sm font-mono font-bold bg-[#1a2e4c] border border-slate-700 text-white tracking-wider mb-3">
                {vehicle.registration_number}
              </div>

              {/* Vehicle Title & Subtitle */}
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                {vehicle.manufacturer} {vehicle.model}
              </h1>
              <p className="text-sm text-slate-300 mt-1">
                {vehicle.variant || 'Standard Model'} · {vehicle.manufacturing_year || 'Year not set'} · {vehicle.fuel_type}
              </p>

              {/* Status Chips */}
              <div className="flex flex-wrap items-center gap-2 mt-4">
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-white/10 text-slate-200 border border-white/15">
                  {vehicle.category}
                </span>
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-white/10 text-slate-200 border border-white/15">
                  👤 {vehicle.owner_name || 'Individual'} ({vehicle.relationship_to_user || 'Self'})
                </span>
                {getInsuranceBadge(vehicle.insurance)}
                {vehicle.verification_status === 'verified' ? (
                  <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                    <svg className="w-3 h-3 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
                    </svg>
                    <span>VAHAN Verified {vehicle.verification_reference_id ? `(${vehicle.verification_reference_id})` : ''}</span>
                  </span>
                ) : vehicle.verification_status === 'failed' ? (
                  <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/20 text-red-300 border border-red-500/30 flex items-center gap-1">
                    <span>✗ VAHAN Check Failed</span>
                  </span>
                ) : (
                  <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                    <span>⚠️ Unverified RC</span>
                  </span>
                )}
              </div>

              {vahanNotice && (
                <div className={`mt-3 p-3 rounded-xl text-xs font-medium ${
                  vahanNotice.type === 'success'
                    ? 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-200'
                    : 'bg-red-500/20 border border-red-500/30 text-red-200'
                }`}>
                  {vahanNotice.msg}
                </div>
              )}
            </div>

            {/* CTA Action Buttons */}
            <div className="flex flex-wrap items-center gap-2.5 pt-4 border-t border-slate-800">
              {vehicle.verification_status !== 'verified' && (
                <button
                  onClick={handleVerifyVahan}
                  disabled={verifyingVahan}
                  className="px-4 py-2.5 rounded-xl font-semibold text-xs bg-emerald-600 hover:bg-emerald-500 text-white shadow-md transition cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <span>{verifyingVahan ? 'Verifying with VAHAN...' : vehicle.verification_status === 'failed' ? 'Retry VAHAN Check' : 'Verify with VAHAN'}</span>
                </button>
              )}

              <button
                onClick={() => setEditModalOpen(true)}
                className="px-4 py-2.5 rounded-xl font-semibold text-xs bg-white text-navy-950 hover:bg-slate-100 shadow transition cursor-pointer flex items-center gap-1.5"
              >
                <span>✏️</span>
                <span>Edit Vehicle</span>
              </button>

              <button
                onClick={() => setActiveTab('photos')}
                className="px-4 py-2.5 rounded-xl font-medium text-xs bg-white/10 hover:bg-white/20 text-white border border-white/20 transition cursor-pointer flex items-center gap-1.5"
              >
                <span>🖼️</span>
                <span>Gallery ({vehicle.photos.length})</span>
              </button>

              <button
                onClick={onBack}
                className="px-4 py-2.5 rounded-xl font-medium text-xs bg-transparent hover:bg-white/5 text-slate-300 transition cursor-pointer ml-auto"
              >
                ← Back
              </button>
            </div>
          </div>

        </div>
      </div>

      {/* ==================================================== TABBED NAVIGATION */}
      <div className="border-b border-slate-200 mb-6">
        <nav className="flex space-x-6 overflow-x-auto">
          {[
            { id: 'specs', label: 'Specifications & Details', icon: '📋' },
            { id: 'photos', label: `Photo Gallery (${vehicle.photos.length})`, icon: '📸' },
            { id: 'documents', label: `Documents Vault (${vehicle.documents.length})`, icon: '📁' },
            { id: 'insurance', label: 'Insurance Details', icon: '🛡️' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-3 px-1 text-xs sm:text-sm font-semibold flex items-center gap-2 border-b-2 transition cursor-pointer whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-[#ff7518] text-navy-950'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* ==================================================== TAB 1: SPECIFICATIONS */}
      {activeTab === 'specs' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Basic Specifications Card */}
            <div className="rounded-2xl bg-white border border-slate-200/90 shadow-sm p-6 space-y-4">
              <h3 className="text-sm font-bold text-navy-950 uppercase tracking-wider border-b border-slate-100 pb-2">
                Basic Details
              </h3>
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Registration Number:</span>
                  <span className="font-mono font-bold text-slate-800">{vehicle.registration_number}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Manufacturer:</span>
                  <span className="font-semibold text-slate-800">{vehicle.manufacturer}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Model:</span>
                  <span className="font-semibold text-slate-800">{vehicle.model}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Variant:</span>
                  <span className="font-medium text-slate-800">{vehicle.variant || 'Not provided'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Year:</span>
                  <span className="font-medium text-slate-800">{vehicle.manufacturing_year || 'Not provided'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Fuel Type:</span>
                  <span className="font-semibold text-slate-800">{vehicle.fuel_type}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Color:</span>
                  <span className="font-medium text-slate-800">{vehicle.color || 'Not provided'}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Category:</span>
                  <span className="font-medium text-slate-800">{vehicle.category}</span>
                </div>
              </div>
            </div>

            {/* Technical Specifications Card */}
            <div className="rounded-2xl bg-white border border-slate-200/90 shadow-sm p-6 space-y-4">
              <h3 className="text-sm font-bold text-navy-950 uppercase tracking-wider border-b border-slate-100 pb-2">
                Technical Specifications
              </h3>
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Chassis Number:</span>
                  <span className="font-mono text-slate-800">{vehicle.chassis_number || 'Not provided'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Engine Number:</span>
                  <span className="font-mono text-slate-800">{vehicle.engine_number || 'Not provided'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">VIN:</span>
                  <span className="font-mono text-slate-800">{vehicle.vin || 'Not provided'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Engine Capacity:</span>
                  <span className="font-medium text-slate-800">{vehicle.engine_capacity || 'Not provided'}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Transmission:</span>
                  <span className="font-medium text-slate-800">{vehicle.transmission || 'Not provided'}</span>
                </div>
              </div>
            </div>

            {/* Ownership Information Card */}
            <div className="rounded-2xl bg-white border border-slate-200/90 shadow-sm p-6 space-y-4">
              <h3 className="text-sm font-bold text-navy-950 uppercase tracking-wider border-b border-slate-100 pb-2">
                Ownership & Registration
              </h3>
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Registered Owner:</span>
                  <span className="font-semibold text-slate-800">{vehicle.owner_name || 'Individual'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Ownership Type:</span>
                  <span className="font-medium text-slate-800">{vehicle.ownership_type}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Relationship:</span>
                  <span className="font-medium text-slate-800">{vehicle.relationship_to_user || 'Self'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Created In Vault:</span>
                  <span className="text-slate-600">{new Date(vehicle.created_at).toLocaleDateString('en-IN')}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Last Updated:</span>
                  <span className="text-slate-600">{new Date(vehicle.updated_at).toLocaleDateString('en-IN')}</span>
                </div>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* ==================================================== TAB 2: PHOTO GALLERY */}
      {activeTab === 'photos' && (
        <div className="space-y-6">
          {/* Upload New Photo Container */}
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-5">
            <h3 className="text-sm font-bold text-navy-950 mb-3">Upload Vehicle Photograph</h3>
            <form onSubmit={handlePhotoUploadSubmit} className="flex flex-wrap items-center gap-3">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => e.target.files && setPhotoFile(e.target.files[0])}
                className="text-xs text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-navy-950 hover:file:bg-slate-200 cursor-pointer"
                required
              />

              <select
                value={photoCategory}
                onChange={(e) => setPhotoCategory(e.target.value)}
                className="px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-navy-800"
              >
                <option value="main">Main Image</option>
                <option value="front">Front View</option>
                <option value="rear">Rear View</option>
                <option value="left">Left Side</option>
                <option value="right">Right Side</option>
                <option value="additional">Additional Photo</option>
              </select>

              <label className="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isPhotoPrimary}
                  onChange={(e) => setIsPhotoPrimary(e.target.checked)}
                  className="rounded text-accent-500"
                />
                <span>Set as Main Cover</span>
              </label>

              <button
                type="submit"
                disabled={!photoFile || photoUploading}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#ff7518] text-white hover:bg-[#ea6309] transition disabled:opacity-50 shadow-sm"
              >
                {photoUploading ? 'Uploading…' : '+ Upload Photo'}
              </button>
            </form>
          </div>

          {/* Photo Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {vehicle.photos.map((p) => (
              <div
                key={p.id}
                className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm group hover:shadow-md transition flex flex-col justify-between"
              >
                <div
                  className="relative h-44 bg-slate-100 overflow-hidden cursor-pointer"
                  onClick={() => setLightboxPhoto(p)}
                >
                  <img src={p.url} alt={p.file_name} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                  {p.is_primary && (
                    <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#ff7518] text-white shadow">
                      ★ Primary Image
                    </span>
                  )}
                  <span className="absolute bottom-2 left-2 px-2 py-0.5 rounded text-[10px] font-semibold bg-black/60 text-white backdrop-blur-sm uppercase">
                    {p.photo_category}
                  </span>
                </div>

                <div className="p-3 bg-white flex items-center justify-between text-xs">
                  <span className="text-slate-400 text-[11px] truncate max-w-[120px]">{p.file_name}</span>
                  <div className="flex items-center gap-1">
                    {!p.is_primary && (
                      <button
                        onClick={() => onSetPrimaryPhoto(p.id)}
                        className="px-2 py-1 rounded-md text-[10px] font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
                      >
                        Set Main
                      </button>
                    )}
                    <button
                      onClick={() => onDeletePhoto(p.id)}
                      className="p-1 rounded-md text-slate-400 hover:text-red-600 transition"
                      title="Delete Photo"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {vehicle.photos.length === 0 && (
            <div className="text-center py-12 text-slate-400 text-xs">
              No gallery photographs uploaded yet.
            </div>
          )}
        </div>
      )}

      {/* ==================================================== TAB 3: DOCUMENTS VAULT */}
      {activeTab === 'documents' && (
        <div className="space-y-6">
          {/* Upload Document Box */}
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-5">
            <h3 className="text-sm font-bold text-navy-950 mb-3">Upload Vehicle Document</h3>
            <form onSubmit={handleDocUploadSubmit} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Document Category</label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-navy-800"
                >
                  <option value="rc">Registration Certificate (RC)</option>
                  <option value="insurance">Insurance Policy Schedule</option>
                  <option value="puc">Pollution Under Control (PUC)</option>
                  <option value="purchase_invoice">Purchase Invoice</option>
                  <option value="service_record">Service Record</option>
                  <option value="other">Other Document</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Document Title</label>
                <input
                  type="text"
                  placeholder="e.g. Form 23 RC, Tata AIG Policy"
                  value={docName}
                  onChange={(e) => setDocName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Expiry Date (If applicable)</label>
                <input
                  type="date"
                  value={docExpiry}
                  onChange={(e) => setDocExpiry(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div>
                <input
                  type="file"
                  accept=".pdf,image/png,image/jpeg,image/webp"
                  onChange={(e) => e.target.files && setDocFile(e.target.files[0])}
                  className="w-full text-xs text-slate-500 file:mr-2 file:py-1.5 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-navy-950 hover:file:bg-slate-200 cursor-pointer"
                  required
                />
              </div>

              <div className="sm:col-span-2 lg:col-span-4 flex justify-end">
                <button
                  type="submit"
                  disabled={!docFile || docUploading}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-[#ff7518] text-white hover:bg-[#ea6309] transition disabled:opacity-50 shadow-sm"
                >
                  {docUploading ? 'Saving Document…' : '+ Attach Document'}
                </button>
              </div>
            </form>
          </div>

          {/* Document Records List */}
          <div className="space-y-3">
            {vehicle.documents.map((d) => (
              <div
                key={d.id}
                className="rounded-2xl border border-slate-200 bg-white p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm hover:border-slate-300 transition"
              >
                <div className="flex items-start gap-3.5">
                  <div className="h-10 w-10 rounded-xl bg-orange-50 text-orange-600 border border-orange-100 flex items-center justify-center text-lg flex-shrink-0">
                    📄
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-navy-950">{d.document_name}</h4>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 mt-0.5">
                      <span className="uppercase text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {d.document_type.replace('_', ' ')}
                      </span>
                      <span>·</span>
                      <span>{(d.file_size / 1024).toFixed(1)} KB</span>
                      <span>·</span>
                      <span>Uploaded {new Date(d.uploaded_at).toLocaleDateString('en-IN')}</span>
                      {d.expiry_date && (
                        <>
                          <span>·</span>
                          <span className={d.verification_status === 'expiring_soon' ? 'text-amber-600 font-semibold' : 'text-slate-600'}>
                            Valid until {new Date(d.expiry_date).toLocaleDateString('en-IN')}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-center">
                  <a
                    href={d.url}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-navy-950 hover:bg-slate-200 transition"
                  >
                    View / Download
                  </a>
                  <button
                    onClick={() => onDeleteDocument(d.id)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 transition"
                    title="Delete document"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>

          {vehicle.documents.length === 0 && (
            <div className="text-center py-12 text-slate-400 text-xs">
              No documents attached to this vehicle yet.
            </div>
          )}
        </div>
      )}

      {/* ==================================================== TAB 4: INSURANCE DETAILS */}
      {activeTab === 'insurance' && (
        <div className="space-y-6">
          <div className="rounded-2xl bg-white border border-slate-200/90 shadow-sm p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-base font-bold text-navy-950">Active Insurance Policy</h3>
                <p className="text-xs text-slate-500">Details verified for PM-RAHAT cashless eligibility</p>
              </div>
              {getInsuranceBadge(vehicle.insurance)}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5 text-xs">
              <div>
                <span className="text-slate-400 block text-[11px]">Insurance Provider:</span>
                <span className="text-sm font-bold text-slate-800">{vehicle.insurance.provider || 'Not provided'}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Policy Number:</span>
                <span className="text-sm font-mono font-bold text-slate-800">{vehicle.insurance.policy_number || 'Not provided'}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Policy Type:</span>
                <span className="text-sm font-semibold text-slate-800">{vehicle.insurance.policy_type || 'Comprehensive'}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Start Date:</span>
                <span className="font-medium text-slate-800">
                  {vehicle.insurance.start_date ? new Date(vehicle.insurance.start_date).toLocaleDateString('en-IN') : 'Not provided'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Expiry Date:</span>
                <span className="font-bold text-slate-800">
                  {vehicle.insurance.expiry_date ? new Date(vehicle.insurance.expiry_date).toLocaleDateString('en-IN') : 'Not provided'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Remaining Validity:</span>
                <span className="font-bold text-slate-800">
                  {vehicle.insurance.days_left !== null
                    ? `${vehicle.insurance.days_left} calendar days left`
                    : 'Not calculated'}
                </span>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                To update policy validity or provider details, click Edit Vehicle.
              </span>
              <button
                onClick={() => setEditModalOpen(true)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-navy-950 text-white hover:bg-navy-900 transition"
              >
                Update Policy Details
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================== LIGHTBOX PHOTO MODAL */}
      {lightboxPhoto && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md animate-fade-in"
          onClick={() => setLightboxPhoto(null)}
        >
          <div className="max-w-4xl max-h-[90vh] overflow-hidden rounded-2xl relative" onClick={(e) => e.stopPropagation()}>
            <img src={lightboxPhoto.url} alt={lightboxPhoto.file_name} className="max-h-[85vh] w-auto mx-auto object-contain" />
            <div className="absolute top-4 right-4">
              <button
                onClick={() => setLightboxPhoto(null)}
                className="h-8 w-8 rounded-full bg-white/20 text-white flex items-center justify-center font-bold hover:bg-white/40 transition"
              >
                ✕
              </button>
            </div>
            <div className="absolute bottom-4 left-4 right-4 bg-black/60 backdrop-blur-sm p-3 rounded-xl text-white text-xs flex justify-between">
              <span>{lightboxPhoto.file_name} ({lightboxPhoto.photo_category})</span>
              <span>Uploaded {new Date(lightboxPhoto.uploaded_at).toLocaleDateString('en-IN')}</span>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================== EDIT MODAL */}
      {editModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl border border-slate-200 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-lg font-bold text-navy-950">Edit Vehicle Information</h3>
              <button onClick={() => setEditModalOpen(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Registration Number</label>
                <input
                  type="text"
                  value={editForm.registration_number}
                  onChange={(e) => setEditForm({ ...editForm, registration_number: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 font-mono font-bold"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Category</label>
                <select
                  value={editForm.category}
                  onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 bg-white"
                >
                  <option value="Four Wheeler">Four Wheeler</option>
                  <option value="Two Wheeler">Two Wheeler</option>
                  <option value="Commercial">Commercial</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Manufacturer</label>
                <input
                  type="text"
                  value={editForm.manufacturer}
                  onChange={(e) => setEditForm({ ...editForm, manufacturer: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Model</label>
                <input
                  type="text"
                  value={editForm.model}
                  onChange={(e) => setEditForm({ ...editForm, model: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Variant</label>
                <input
                  type="text"
                  value={editForm.variant}
                  onChange={(e) => setEditForm({ ...editForm, variant: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Manufacturing Year</label>
                <input
                  type="number"
                  value={editForm.manufacturing_year}
                  onChange={(e) => setEditForm({ ...editForm, manufacturing_year: parseInt(e.target.value) || 2024 })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Fuel Type</label>
                <select
                  value={editForm.fuel_type}
                  onChange={(e) => setEditForm({ ...editForm, fuel_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 bg-white"
                >
                  <option value="Petrol">Petrol</option>
                  <option value="Diesel">Diesel</option>
                  <option value="Electric">Electric</option>
                  <option value="Hybrid">Hybrid</option>
                  <option value="CNG">CNG</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Color</label>
                <input
                  type="text"
                  value={editForm.color}
                  onChange={(e) => setEditForm({ ...editForm, color: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Chassis Number</label>
                <input
                  type="text"
                  value={editForm.chassis_number}
                  onChange={(e) => setEditForm({ ...editForm, chassis_number: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 font-mono"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Engine Number</label>
                <input
                  type="text"
                  value={editForm.engine_number}
                  onChange={(e) => setEditForm({ ...editForm, engine_number: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 font-mono"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Insurance Provider</label>
                <input
                  type="text"
                  value={editForm.insurance.provider}
                  onChange={(e) =>
                    setEditForm({
                      ...editForm,
                      insurance: { ...editForm.insurance, provider: e.target.value },
                    })
                  }
                  className="w-full px-3 py-2 rounded-xl border border-slate-300"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Policy Expiry Date</label>
                <input
                  type="date"
                  value={editForm.insurance.expiry_date ? editForm.insurance.expiry_date.slice(0, 10) : ''}
                  onChange={(e) =>
                    setEditForm({
                      ...editForm,
                      insurance: { ...editForm.insurance, expiry_date: e.target.value ? new Date(e.target.value).toISOString() : '' },
                    })
                  }
                  className="w-full px-3 py-2 rounded-xl border border-slate-300"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setDeleteConfirmOpen(true)}
                className="text-xs font-semibold text-red-600 hover:text-red-700"
              >
                Delete Vehicle…
              </button>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setEditModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveEdit}
                  disabled={savingEdit}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-[#ff7518] text-white hover:bg-[#ea6309] shadow"
                >
                  {savingEdit ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================== DELETE CONFIRMATION */}
      {deleteConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="h-12 w-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center text-xl mx-auto">
              ⚠️
            </div>
            <div className="text-center">
              <h3 className="text-base font-bold text-navy-950">Delete this vehicle permanently?</h3>
              <p className="text-xs text-slate-500 mt-1">
                All uploaded documents, photographs and policy records for {vehicle.registration_number} will be deleted.
              </p>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setDeleteConfirmOpen(false)}
                className="flex-1 py-2 rounded-xl text-xs font-semibold border border-slate-300 text-slate-700 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  setDeleteConfirmOpen(false)
                  setEditModalOpen(false)
                  await onDeleteVehicle()
                }}
                className="flex-1 py-2 rounded-xl text-xs font-semibold bg-red-600 text-white hover:bg-red-700 shadow"
              >
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
