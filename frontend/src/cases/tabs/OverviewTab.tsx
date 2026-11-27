import { useState } from 'react'
import type { CaseWorkspaceData } from '../types'
import { FrontCarIcon, ArrowRightIcon } from '../../components/Icons'
import { api } from '../../api'

interface OverviewTabProps {
  workspace: CaseWorkspaceData
  onRefresh: () => void
  onOpenVehicle: (vehicleId: string) => void
  onOpenTab: (tabId: string) => void
}

export function OverviewTab({
  workspace,
  onRefresh,
  onOpenVehicle,
  onOpenTab,
}: OverviewTabProps) {
  const { case: c, vehicle: v, progress_indicators: pi } = workspace
  const [editingDetails, setEditingDetails] = useState(false)
  const [editForm, setEditForm] = useState({
    approximate_location: c.approximate_location,
    location_landmark: c.location_landmark || '',
    accident_description: c.accident_description || '',
    accident_type: c.accident_type,
    weather_conditions: c.weather_conditions,
    vehicles_involved: c.vehicles_involved,
    people_affected: c.people_affected,
  })
  const [saving, setSaving] = useState(false)

  const handleSaveDetails = async () => {
    setSaving(true)
    try {
      await api(`/api/cases/${c.id}/section`, {
        method: 'PATCH',
        body: {
          section: 'overview',
          data: editForm,
        },
      })
      setEditingDetails(false)
      onRefresh()
    } catch (e) {
      console.error('Failed to update accident details:', e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* 4 Independent Domain Progress Indicators */}
      <div>
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2.5">
          Post-Accident Domain Progress
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Hospital */}
          <div
            onClick={() => onOpenTab('hospital')}
            className="card p-4 bg-white border border-blue-200 rounded-xl shadow-xs hover:border-blue-400 hover:shadow-sm transition cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-800 uppercase tracking-wide">
                🏥 Hospital Treatment
              </span>
              <span className="chip bg-blue-50 text-blue-700 text-[11px] font-semibold border border-blue-200 px-2 py-0.5 rounded">
                Active
              </span>
            </div>
            <div className="text-base font-bold text-navy-950 mt-2 truncate">
              {pi.hospital.stage}
            </div>
            <p className="text-xs text-slate-500 mt-1 truncate">{pi.hospital.subtitle}</p>
          </div>

          {/* PM-RAHAT */}
          <div
            onClick={() => onOpenTab('hospital')}
            className="card p-4 bg-white border border-emerald-200 rounded-xl shadow-xs hover:border-emerald-400 hover:shadow-sm transition cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-800 uppercase tracking-wide">
                🛡️ PM-RAHAT Scheme
              </span>
              <span className="chip bg-emerald-50 text-emerald-700 text-[11px] font-semibold border border-emerald-200 px-2 py-0.5 rounded">
                Cover Active
              </span>
            </div>
            <div className="text-base font-bold text-navy-950 mt-2 truncate">
              {pi.pmrahat.stage}
            </div>
            <p className="text-xs text-slate-500 mt-1 truncate">{pi.pmrahat.subtitle}</p>
          </div>

          {/* Police */}
          <div
            onClick={() => onOpenTab('police-insurance')}
            className="card p-4 bg-white border border-amber-200 rounded-xl shadow-xs hover:border-amber-400 hover:shadow-sm transition cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-amber-800 uppercase tracking-wide">
                👮 Police Records
              </span>
              <span className={`chip text-[11px] font-semibold border px-2 py-0.5 rounded ${
                workspace.police_info.draft_status === 'approved_by_user'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border-amber-300'
              }`}>
                {workspace.police_info.draft_status === 'approved_by_user' ? 'Approved' : 'Action Required'}
              </span>
            </div>
            <div className="text-base font-bold text-navy-950 mt-2 truncate">
              {pi.police.stage}
            </div>
            <p className="text-xs text-slate-500 mt-1 truncate">{pi.police.subtitle}</p>
          </div>

          {/* Insurance */}
          <div
            onClick={() => onOpenTab('police-insurance')}
            className="card p-4 bg-white border border-slate-200 rounded-xl shadow-xs hover:border-navy-300 hover:shadow-sm transition cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wide">
                📋 Motor Insurance
              </span>
              <span className="chip bg-slate-100 text-slate-700 text-[11px] font-semibold border border-slate-200 px-2 py-0.5 rounded">
                Processing
              </span>
            </div>
            <div className="text-base font-bold text-navy-950 mt-2 truncate">
              {pi.insurance.stage}
            </div>
            <p className="text-xs text-slate-500 mt-1 truncate">{pi.insurance.subtitle}</p>
          </div>
        </div>
      </div>

      {/* Main Grid: Accident Details + Linked Vehicle / Assessments */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Accident Details */}
        <div className="lg:col-span-2 space-y-6">
          <div className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-navy-950 flex items-center gap-2">
                  <span>📍</span>
                  <span>Accident & Incident Details</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Verified location, collision description and conditions
                </p>
              </div>

              {!editingDetails ? (
                <button
                  onClick={() => setEditingDetails(true)}
                  className="text-xs font-semibold text-accent-500 hover:underline cursor-pointer"
                >
                  ✎ Edit Details
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setEditingDetails(false)}
                    className="text-xs text-slate-500 hover:text-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveDetails}
                    disabled={saving}
                    className="btn-accent text-xs px-3 py-1 rounded-lg"
                  >
                    {saving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              )}
            </div>

            {editingDetails ? (
              <div className="space-y-4 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Accident Location Address
                  </label>
                  <input
                    type="text"
                    value={editForm.approximate_location}
                    onChange={(e) => setEditForm({ ...editForm, approximate_location: e.target.value })}
                    className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-1 focus:ring-accent-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Landmark / Junction
                  </label>
                  <input
                    type="text"
                    value={editForm.location_landmark}
                    onChange={(e) => setEditForm({ ...editForm, location_landmark: e.target.value })}
                    className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-1 focus:ring-accent-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Accident Type
                    </label>
                    <input
                      type="text"
                      value={editForm.accident_type}
                      onChange={(e) => setEditForm({ ...editForm, accident_type: e.target.value })}
                      className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-1 focus:ring-accent-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Weather / Road Conditions
                    </label>
                    <input
                      type="text"
                      value={editForm.weather_conditions}
                      onChange={(e) => setEditForm({ ...editForm, weather_conditions: e.target.value })}
                      className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-1 focus:ring-accent-500"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Vehicles Involved
                    </label>
                    <input
                      type="text"
                      value={editForm.vehicles_involved}
                      onChange={(e) => setEditForm({ ...editForm, vehicles_involved: e.target.value })}
                      className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-1 focus:ring-accent-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      People Affected
                    </label>
                    <input
                      type="text"
                      value={editForm.people_affected}
                      onChange={(e) => setEditForm({ ...editForm, people_affected: e.target.value })}
                      className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-1 focus:ring-accent-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Accident Narrative / Description
                  </label>
                  <textarea
                    rows={3}
                    value={editForm.accident_description}
                    onChange={(e) => setEditForm({ ...editForm, accident_description: e.target.value })}
                    className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:outline-none focus:ring-1 focus:ring-accent-500"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-slate-400 block">Date & Time</span>
                    <span className="text-sm font-semibold text-navy-950">
                      {new Date(c.incident_at).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}{' '}
                      · {c.accident_time} IST
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400 block">Accident Type</span>
                    <span className="text-sm font-semibold text-navy-950">{c.accident_type}</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400 block">Accurate Location</span>
                    <span className="text-sm font-semibold text-navy-950 block">
                      {c.approximate_location}
                    </span>
                    {c.location_landmark && (
                      <span className="text-xs text-slate-500 block mt-0.5">
                        Landmark: {c.location_landmark}
                      </span>
                    )}
                  </div>
                  <div>
                    <span className="text-xs text-slate-400 block">GPS Coordinates</span>
                    <span className="text-xs font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                      {c.latitude.toFixed(4)}° N, {c.longitude.toFixed(4)}° E
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400 block">Weather & Road Conditions</span>
                    <span className="text-sm font-medium text-slate-800">{c.weather_conditions}</span>
                  </div>
                  <div>
                    <span className="text-xs text-slate-400 block">Vehicles & People Affected</span>
                    <span className="text-sm font-medium text-slate-800">
                      {c.vehicles_involved} · {c.people_affected}
                    </span>
                  </div>
                </div>

                {/* Description Narrative */}
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                  <span className="text-xs font-semibold text-slate-500 block mb-1">
                    Accident Narrative / Statement:
                  </span>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {c.accident_description || 'No detailed narrative provided yet.'}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Injuries & Vehicle Damage Card */}
          <div className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
            <h3 className="text-base font-bold text-navy-950 flex items-center gap-2 border-b border-slate-100 pb-3">
              <span>🩺</span>
              <span>Injuries & Vehicle Damage Assessment</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Injury Section */}
              <div className="p-4 rounded-xl border border-orange-100 bg-orange-50/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-orange-900 uppercase tracking-wide">
                    Victim Injury Assessment
                  </span>
                  <span className={`text-xs font-bold px-2.5 py-0.5 rounded ${
                    c.injury_severity === 'Critical'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-orange-100 text-orange-800'
                  }`}>
                    {c.injury_severity}
                  </span>
                </div>
                <div className="text-sm font-semibold text-navy-950">
                  {c.victim_display_name || 'Patient'} ({c.victim_relationship || 'Family'})
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {c.injury_description || 'Stabilized in emergency unit. Medical reports uploaded under Evidence.'}
                </p>
              </div>

              {/* Damage Section */}
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wide">
                    Vehicle Damage
                  </span>
                  <span className="text-xs font-medium bg-slate-200 text-slate-800 px-2 py-0.5 rounded">
                    {c.damage_severity}
                  </span>
                </div>
                <div className="text-sm font-semibold text-navy-950">
                  {v ? `${v.manufacturer} ${v.model}` : 'Registered Vehicle'}
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {c.damage_description || 'Frontal impact damage. Under insurance survey assessment.'}
                </p>
              </div>
            </div>
          </div>

          {/* Phase 3: All Involved Vehicles (Multi-Vehicle & Third-Party Support) */}
          {workspace.case_vehicles && workspace.case_vehicles.length > 0 && (
            <div className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
              <h3 className="text-base font-bold text-navy-950 flex items-center justify-between border-b border-slate-100 pb-3">
                <span className="flex items-center gap-2">
                  <span>🚗</span>
                  <span>Involved Vehicles ({workspace.case_vehicles.length})</span>
                </span>
                <span className="text-xs font-semibold text-slate-500">
                  Normalized Multi-Vehicle Record
                </span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {workspace.case_vehicles.map((cv) => (
                  <div
                    key={cv.id}
                    className={`p-4 rounded-xl border ${
                      cv.is_third_party
                        ? 'border-amber-200 bg-amber-50/20'
                        : 'border-slate-200 bg-slate-50/50'
                    } space-y-2 text-xs`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-sm text-navy-950">
                        {cv.registration_number}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                          cv.is_third_party
                            ? 'bg-amber-100 text-amber-900 border border-amber-200'
                            : 'bg-blue-100 text-blue-900 border border-blue-200'
                        }`}
                      >
                        {cv.is_third_party ? 'Third-Party Vehicle' : 'Primary Subject'}
                      </span>
                    </div>

                    <div className="text-slate-800 font-semibold">
                      {cv.make_model || 'Vehicle Details'} {cv.color ? `· ${cv.color}` : ''}
                    </div>

                    <div className="space-y-1 text-slate-600 pt-1 border-t border-slate-100">
                      {cv.driver_name && (
                        <div>
                          <span className="text-slate-400">Driver: </span>
                          <span className="font-medium text-navy-900">{cv.driver_name}</span>
                          {cv.driver_contact ? ` (${cv.driver_contact})` : ''}
                        </div>
                      )}
                      {cv.insurance_company && (
                        <div>
                          <span className="text-slate-400">Insurer: </span>
                          <span className="font-medium">{cv.insurance_company}</span>
                          {cv.insurance_policy_no ? ` · #${cv.insurance_policy_no}` : ''}
                        </div>
                      )}
                      {cv.damage_description && (
                        <div className="mt-1 text-slate-700 bg-white/70 p-2 rounded border border-slate-100">
                          <span className="font-medium text-slate-500">Damage: </span>
                          {cv.damage_description} ({cv.damage_severity})
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Phase 3: Involved People (Drivers, Passengers, Pedestrians) */}
          {workspace.involved_people && workspace.involved_people.length > 0 && (
            <div className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
              <h3 className="text-base font-bold text-navy-950 flex items-center justify-between border-b border-slate-100 pb-3">
                <span className="flex items-center gap-2">
                  <span>👥</span>
                  <span>Involved Persons ({workspace.involved_people.length})</span>
                </span>
                <span className="text-xs text-slate-400">
                  User-Reported Status (Non-Diagnostic)
                </span>
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {workspace.involved_people.map((person) => (
                  <div
                    key={person.id}
                    className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-navy-950">
                        {person.full_name}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-200 text-slate-800 capitalize">
                        {person.involvement_type}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-slate-600">
                      <span>Relationship: {person.relationship_to_coordinator || 'Involved Party'}</span>
                      {person.contact_number && (
                        <>
                          <span>·</span>
                          <span className="font-mono">{person.contact_number}</span>
                        </>
                      )}
                    </div>

                    <div className="pt-2 border-t border-slate-100 space-y-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-400">Reported Injury:</span>
                        <span
                          className={`font-semibold capitalize ${
                            person.reported_injury_status === 'uninjured'
                              ? 'text-emerald-700'
                              : 'text-orange-700'
                          }`}
                        >
                          {person.reported_injury_status}
                        </span>
                      </div>
                      {person.injury_description && (
                        <p className="text-slate-600">{person.injury_description}</p>
                      )}
                      {person.hospital_name && (
                        <p className="text-slate-500 text-[11px]">
                          🏥 Hospital: {person.hospital_name}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Phase 3: Case Status Transition History */}
          {workspace.status_transitions && workspace.status_transitions.length > 0 && (
            <div className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-3">
              <h3 className="text-base font-bold text-navy-950 flex items-center justify-between border-b border-slate-100 pb-3">
                <span className="flex items-center gap-2">
                  <span>📜</span>
                  <span>Case Status Audit History</span>
                </span>
                <span className="text-xs font-semibold text-slate-500">
                  Append-Only State Machine
                </span>
              </h3>

              <div className="space-y-2">
                {workspace.status_transitions.map((st) => (
                  <div
                    key={st.id}
                    className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-navy-950 capitalize">
                          {st.from_status} → {st.to_status}
                        </span>
                        <span className="text-[11px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded">
                          {st.transition_trigger}
                        </span>
                      </div>
                      {st.reason && (
                        <p className="text-slate-600 text-[11px] mt-0.5">{st.reason}</p>
                      )}
                    </div>
                    <span className="text-slate-400 font-mono text-[11px]">
                      {new Date(st.created_at).toLocaleString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right 1 Col: Linked Vehicle Profile Card */}
        <div className="space-y-6">
          <div className="card p-5 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Linked Vehicle Profile
              </span>
              {v && (
                <button
                  onClick={() => onOpenVehicle(v.id)}
                  className="text-xs font-semibold text-accent-500 hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <span>Vehicle Wallet</span>
                  <ArrowRightIcon className="w-3 h-3" />
                </button>
              )}
            </div>

            {v ? (
              <div className="space-y-4">
                {/* Vehicle Photo / Placeholder */}
                <div className="w-full h-40 rounded-xl overflow-hidden bg-navy-950 relative border border-slate-200">
                  {v.photo_url ? (
                    <img
                      src={v.photo_url}
                      alt={v.model}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-white/80">
                      <FrontCarIcon className="w-12 h-12 mb-1" />
                      <span className="text-xs font-medium">Registered Vehicle</span>
                    </div>
                  )}
                  <div className="absolute bottom-2 left-2">
                    <span className="bg-navy-950/90 text-white font-mono text-xs font-bold px-2.5 py-1 rounded-md border border-white/20 shadow">
                      {v.registration_number}
                    </span>
                  </div>
                </div>

                <div>
                  <h4 className="text-base font-bold text-navy-950">
                    {v.manufacturer} {v.model} {v.variant}
                  </h4>
                  <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                    <span>{v.manufacturing_year || '2024'}</span>
                    <span>·</span>
                    <span>{v.fuel_type || 'Petrol'}</span>
                    <span>·</span>
                    <span>{v.color || 'White'}</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Registered Owner:</span>
                    <span className="font-semibold text-navy-900">{v.owner_name || 'Family Owner'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Active Insurer:</span>
                    <span className="font-semibold text-navy-900">{v.insurance_provider || 'Tata AIG'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Policy Number:</span>
                    <span className="font-mono text-slate-700">{v.insurance_policy_number || 'N/A'}</span>
                  </div>
                </div>

                <button
                  onClick={() => onOpenVehicle(v.id)}
                  className="w-full py-2 bg-slate-50 hover:bg-slate-100 text-navy-900 text-xs font-semibold rounded-xl border border-slate-200 transition text-center cursor-pointer"
                >
                  View Full Vehicle Specifications →
                </button>
              </div>
            ) : (
              <div className="text-center py-6">
                <p className="text-xs text-slate-500 mb-3">No vehicle linked to this accident case.</p>
                <button
                  onClick={() => onOpenVehicle('')}
                  className="btn-accent text-xs px-3 py-1.5"
                >
                  Link Registered Vehicle
                </button>
              </div>
            )}
          </div>

          {/* Quick Support & Help Card */}
          <div className="card p-5 bg-navy-950 text-white rounded-2xl shadow-sm space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-lg">🚑</span>
              <h4 className="text-sm font-bold text-white">Emergency Protocols</h4>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Second Hour is an aftermath and claims companion. In immediate medical emergencies, always call <span className="text-accent-500 font-bold">112</span>.
            </p>
            <div className="pt-2 border-t border-navy-800 flex items-center justify-between text-xs">
              <span className="text-slate-400">PM-RAHAT Helpline:</span>
              <span className="text-white font-mono font-semibold">1033 / 112</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
