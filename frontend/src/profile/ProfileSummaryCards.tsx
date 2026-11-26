import type { UserProfileData } from './types'

interface ProfileSummaryCardsProps {
  profile: UserProfileData
  onNavigateToVehicles: () => void
  onSelectTab: (tabId: string) => void
}

export function ProfileSummaryCards({
  profile,
  onNavigateToVehicles,
  onSelectTab,
}: ProfileSummaryCardsProps) {
  const stats = profile.stats

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {/* 1. Profile Completion */}
      <div
        onClick={() => onSelectTab('personal')}
        className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-all cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Profile Readiness
          </span>
          <div className="w-8 h-8 rounded-xl bg-orange-50 border border-orange-100 text-[#ff7518] flex items-center justify-center">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-bold text-slate-900">{stats.completion_percentage}%</span>
          <span className="text-xs text-slate-500 font-medium">Ready</span>
        </div>
        <p className="text-xs text-slate-500 mt-1 line-clamp-1">
          {stats.missing_items.length > 0 ? stats.missing_items[0] : 'All primary details complete'}
        </p>
      </div>

      {/* 2. Registered Vehicles */}
      <div
        onClick={onNavigateToVehicles}
        className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-all cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Registered Vehicles
          </span>
          <div className="w-8 h-8 rounded-xl bg-sky-50 border border-sky-100 text-sky-600 flex items-center justify-center">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 19H5a2 2 0 01-2-2V9a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2z" />
              <circle cx="7.5" cy="14.5" r="1.5" />
              <circle cx="16.5" cy="14.5" r="1.5" />
            </svg>
          </div>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-bold text-slate-900">{stats.registered_vehicles_count}</span>
          <span className="text-xs text-slate-500 font-medium">Active</span>
        </div>
        <div className="flex items-center justify-between mt-1 text-xs text-sky-600 font-medium group-hover:underline">
          <span>Manage in My Vehicles</span>
          <svg className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>

      {/* 3. Emergency Contacts */}
      <div
        onClick={() => onSelectTab('contacts')}
        className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-all cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Emergency Contacts
          </span>
          <div className="w-8 h-8 rounded-xl bg-rose-50 border border-rose-100 text-rose-600 flex items-center justify-center">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-bold text-slate-900">{stats.emergency_contacts_count}</span>
          <span className="text-xs text-slate-500 font-medium">Designated</span>
        </div>
        <p className="text-xs text-slate-500 mt-1 line-clamp-1">
          {stats.emergency_contacts_count > 0 ? 'Primary contact assigned' : 'No emergency contact set'}
        </p>
      </div>

      {/* 4. Verified Contact Methods */}
      <div
        onClick={() => onSelectTab('security')}
        className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md transition-all cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Verified Contact Info
          </span>
          <div className="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-bold text-slate-900">{stats.verified_contacts_count} / 2</span>
          <span className="text-xs text-slate-500 font-medium">Verified</span>
        </div>
        <p className="text-xs text-slate-500 mt-1 line-clamp-1">
          {profile.phone_verified && profile.email_verified
            ? 'Mobile & Email 2-factor ready'
            : 'Click to verify phone/email'}
        </p>
      </div>
    </div>
  )
}
