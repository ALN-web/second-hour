import { useState, useMemo } from 'react'
import type { VehicleSummary } from './types'

interface VehiclesOverviewProps {
  vehicles: VehicleSummary[]
  loading: boolean
  onAddVehicle: () => void
  onViewDetails: (vehicleId: string) => void
  onEditVehicle: (vehicle: VehicleSummary) => void
  onDeleteVehicle: (vehicleId: string) => void
  onBackHome: () => void
}

export function VehiclesOverview({
  vehicles,
  loading,
  onAddVehicle,
  onViewDetails,
  onEditVehicle,
  onDeleteVehicle,
  onBackHome,
}: VehiclesOverviewProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [selectedInsuranceStatus, setSelectedInsuranceStatus] = useState('All')
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  const categories = ['All', 'Four Wheeler', 'Two Wheeler', 'Commercial', 'Other']
  const insuranceStatuses = [
    { label: 'All', value: 'All' },
    { label: 'Active', value: 'active' },
    { label: 'Expiring Soon', value: 'expiring_soon' },
    { label: 'Expired', value: 'expired' },
  ]

  const filteredVehicles = useMemo(() => {
    return vehicles.filter((v) => {
      const q = searchQuery.toLowerCase().trim()
      const matchesSearch =
        !q ||
        v.registration_number.toLowerCase().includes(q) ||
        v.manufacturer.toLowerCase().includes(q) ||
        v.model.toLowerCase().includes(q) ||
        (v.variant && v.variant.toLowerCase().includes(q))

      const matchesCategory = selectedCategory === 'All' || v.category === selectedCategory
      const matchesInsurance =
        selectedInsuranceStatus === 'All' || v.insurance.status === selectedInsuranceStatus

      return matchesSearch && matchesCategory && matchesInsurance
    })
  }, [vehicles, searchQuery, selectedCategory, selectedInsuranceStatus])

  const getInsuranceBadge = (ins: VehicleSummary['insurance']) => {
    if (ins.status === 'active') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Insurance Active {ins.days_left !== null && `(${ins.days_left}d left)`}
        </span>
      )
    }
    if (ins.status === 'expiring_soon') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
          Expiring Soon {ins.days_left !== null && `(${ins.days_left}d left)`}
        </span>
      )
    }
    if (ins.status === 'expired') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          Insurance Expired
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
        No Policy Added
      </span>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Breadcrumb & Header */}
      <div className="mb-6">
        <nav className="flex items-center gap-2 text-xs text-slate-500 mb-2">
          <button onClick={onBackHome} className="hover:text-navy-950 font-medium transition cursor-pointer">
            Home
          </button>
          <span>/</span>
          <span className="text-slate-800 font-semibold">My Vehicles</span>
        </nav>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-950 tracking-tight">
                My Vehicles
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#1a2e4c] text-white">
                {vehicles.length} {vehicles.length === 1 ? 'Registered Vehicle' : 'Registered Vehicles'}
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Manage your registered vehicles, documents, photographs and insurance policy information.
            </p>
          </div>

          <button
            onClick={onAddVehicle}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-[#ff7518] hover:bg-[#ea6309] shadow-md shadow-orange-500/20 transition-all cursor-pointer self-start sm:self-auto hover:-translate-y-0.5"
          >
            <span>+</span>
            <span>Add New Vehicle</span>
          </button>
        </div>
      </div>

      {/* Search and Filters Bar */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-4 mb-8 space-y-4">
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              🔍
            </span>
            <input
              type="text"
              placeholder="Search by registration number, make or model (e.g. KA-01, Honda City)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-navy-800 bg-slate-50/50"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-xs text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            )}
          </div>

          {/* Category Filter */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
            <span className="text-xs text-slate-400 font-medium mr-1 hidden sm:inline">Category:</span>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition cursor-pointer ${
                  selectedCategory === cat
                    ? 'bg-navy-950 text-white font-semibold'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Insurance Filter Row */}
        <div className="flex items-center gap-2 pt-2 border-t border-slate-100 text-xs">
          <span className="text-slate-400 font-medium">Insurance Status:</span>
          <div className="flex items-center gap-1.5 overflow-x-auto">
            {insuranceStatuses.map((st) => (
              <button
                key={st.value}
                onClick={() => setSelectedInsuranceStatus(st.value)}
                className={`px-2.5 py-1 rounded-md transition cursor-pointer ${
                  selectedInsuranceStatus === st.value
                    ? 'bg-[#ff7518] text-white font-semibold'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-16 text-slate-500">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-accent-500 border-r-transparent mb-3" />
          <p className="text-sm">Loading vehicle records…</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredVehicles.length === 0 && (
        <div className="rounded-2xl border-2 border-dashed border-slate-300 bg-white p-12 text-center">
          <div className="h-16 w-16 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-3xl mb-4">
            🚗
          </div>
          <h3 className="text-base font-bold text-navy-950">No vehicles found</h3>
          <p className="text-xs sm:text-sm text-slate-500 max-w-sm mx-auto mt-1 mb-6">
            {searchQuery || selectedCategory !== 'All' || selectedInsuranceStatus !== 'All'
              ? 'No registered vehicles matched your search filters. Try clearing your filters.'
              : 'You have not registered any vehicles yet. Register your vehicle to store RC, insurance and documents in one place.'}
          </p>
          {searchQuery || selectedCategory !== 'All' || selectedInsuranceStatus !== 'All' ? (
            <button
              onClick={() => {
                setSearchQuery('')
                setSelectedCategory('All')
                setSelectedInsuranceStatus('All')
              }}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition"
            >
              Clear Filters
            </button>
          ) : (
            <button
              onClick={onAddVehicle}
              className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-accent-500 text-white hover:bg-accent-600 transition shadow"
            >
              + Add First Vehicle
            </button>
          )}
        </div>
      )}

      {/* Vehicle Cards Grid */}
      {!loading && filteredVehicles.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredVehicles.map((vehicle) => (
            <div
              key={vehicle.id}
              className="rounded-2xl bg-white border border-slate-200/90 shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden flex flex-col justify-between group hover:-translate-y-1"
            >
              <div>
                {/* Vehicle Photograph Header */}
                <div className="relative h-48 bg-navy-950 overflow-hidden cursor-pointer" onClick={() => onViewDetails(vehicle.id)}>
                  {vehicle.main_image ? (
                    <img
                      src={vehicle.main_image}
                      alt={`${vehicle.manufacturer} ${vehicle.model}`}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 bg-gradient-to-br from-navy-950 to-navy-900">
                      <span className="text-4xl mb-1">🚗</span>
                      <span className="text-xs">No Photo Uploaded</span>
                    </div>
                  )}

                  {/* Badges on Image */}
                  <div className="absolute top-3 left-3 flex items-center gap-1.5">
                    <span className="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-navy-950/90 text-white border border-slate-700 backdrop-blur-sm">
                      {vehicle.registration_number}
                    </span>
                  </div>

                  <div className="absolute top-3 right-3">
                    <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-white/90 text-navy-900 backdrop-blur-sm shadow-sm">
                      {vehicle.category}
                    </span>
                  </div>

                  {/* Photo count indicator */}
                  <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/60 text-white text-[10px] backdrop-blur-sm">
                    📷 {vehicle.photo_count} {vehicle.photo_count === 1 ? 'photo' : 'photos'}
                  </div>
                </div>

                {/* Card Body */}
                <div className="p-5 space-y-3">
                  <div>
                    <h3
                      onClick={() => onViewDetails(vehicle.id)}
                      className="text-lg font-bold text-navy-950 hover:text-accent-500 transition cursor-pointer leading-snug"
                    >
                      {vehicle.manufacturer} {vehicle.model}
                    </h3>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {vehicle.variant || 'Standard'} {vehicle.manufacturing_year ? `· ${vehicle.manufacturing_year}` : ''} · {vehicle.fuel_type}
                    </div>
                  </div>

                  {/* Insurance Status Indicator */}
                  <div className="pt-1">
                    {getInsuranceBadge(vehicle.insurance)}
                  </div>

                  {/* Key Specifications Grid */}
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-xs">
                    <div>
                      <span className="text-slate-400 block text-[11px]">Owner:</span>
                      <span className="font-medium text-slate-800 truncate block">
                        {vehicle.owner_name || 'Individual'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">Documents:</span>
                      <span className="font-medium text-slate-800 block">
                        📁 {vehicle.doc_count} file{vehicle.doc_count !== 1 ? 's' : ''} stored
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Card Footer Actions */}
              <div className="px-5 py-3.5 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
                <button
                  onClick={() => onViewDetails(vehicle.id)}
                  className="text-xs font-bold text-navy-900 hover:text-accent-500 transition flex items-center gap-1 cursor-pointer"
                >
                  <span>View Details</span>
                  <span>→</span>
                </button>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => onEditVehicle(vehicle)}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-navy-950 hover:bg-slate-200 transition text-xs"
                    title="Edit Vehicle"
                  >
                    ✏️
                  </button>
                  <button
                    onClick={() => setDeleteConfirmId(vehicle.id)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition text-xs"
                    title="Delete Vehicle"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="h-12 w-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center text-xl mx-auto">
              ⚠️
            </div>
            <div className="text-center">
              <h3 className="text-base font-bold text-navy-950">Delete this vehicle?</h3>
              <p className="text-xs text-slate-500 mt-1">
                This action will delete the vehicle record along with all stored documents and gallery photos. This cannot be undone.
              </p>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="flex-1 py-2 rounded-xl text-xs font-semibold border border-slate-300 text-slate-700 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onDeleteVehicle(deleteConfirmId)
                  setDeleteConfirmId(null)
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
