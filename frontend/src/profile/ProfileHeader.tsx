import type { UserProfileData } from './types'

interface ProfileHeaderProps {
  profile: UserProfileData
  onBackHome: () => void
  onEditPhoto?: () => void
  onOpenVerifyModal: (channel: 'email' | 'phone') => void
}

export function ProfileHeader({
  profile,
  onBackHome,
  onOpenVerifyModal,
}: ProfileHeaderProps) {
  const completion = profile.stats.completion_percentage

  return (
    <div className="bg-[#091528] border-b border-[#1a3152] text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between mb-6 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <button
              onClick={onBackHome}
              className="hover:text-white transition flex items-center gap-1.5 cursor-pointer text-slate-300"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              <span>Back to Home</span>
            </button>
            <span>/</span>
            <span className="text-white font-medium">My Profile</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>{profile.account_status}</span>
            </span>
          </div>
        </div>

        {/* Profile Card Main Row */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start sm:items-center gap-4 sm:gap-6">
            {/* Avatar */}
            <div className="relative group">
              <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-2xl bg-gradient-to-br from-[#122847] to-[#1c3a66] border-2 border-[#2b4c7e] text-white flex items-center justify-center text-2xl sm:text-3xl font-extrabold shadow-xl">
                {profile.profile_photo ? (
                  <img
                    src={profile.profile_photo}
                    alt={profile.name}
                    className="w-full h-full object-cover rounded-2xl"
                  />
                ) : (
                  profile.name.slice(0, 2).toUpperCase()
                )}
              </div>
              <span
                className="absolute -bottom-1.5 -right-1.5 w-6 h-6 rounded-full bg-[#ff7518] border-2 border-[#091528] flex items-center justify-center text-white text-[10px]"
                title="Verified Second Hour Profile"
              >
                ✓
              </span>
            </div>

            {/* Profile Info Details */}
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                  {profile.name}
                </h1>
                <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-[#142947] border border-[#234370] text-slate-300">
                  {profile.role_label}
                </span>
              </div>

              {/* Contact methods with verification status badges */}
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300 pt-1">
                {/* Email */}
                <div className="flex items-center gap-1.5">
                  <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  <span>{profile.email || 'No email registered'}</span>
                  {profile.email ? (
                    profile.email_verified ? (
                      <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-0.5">
                        ✓ Verified
                      </span>
                    ) : (
                      <button
                        onClick={() => onOpenVerifyModal('email')}
                        className="text-[10px] font-bold text-[#ff7518] hover:underline cursor-pointer"
                      >
                        Verify now
                      </button>
                    )
                  ) : null}
                </div>

                {/* Mobile Phone */}
                <div className="flex items-center gap-1.5">
                  <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                  <span>{profile.phone || 'No mobile registered'}</span>
                  {profile.phone ? (
                    profile.phone_verified ? (
                      <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-0.5">
                        ✓ Verified
                      </span>
                    ) : (
                      <button
                        onClick={() => onOpenVerifyModal('phone')}
                        className="text-[10px] font-bold text-[#ff7518] hover:underline cursor-pointer"
                      >
                        Verify now
                      </button>
                    )
                  ) : null}
                </div>
              </div>
            </div>
          </div>

          {/* Profile Completion Indicator Card */}
          <div className="bg-[#0d1d35] border border-[#1b3457] rounded-2xl p-4 min-w-[240px] flex items-center justify-between gap-4">
            <div>
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Profile Readiness
              </span>
              <div className="flex items-baseline gap-1 mt-1">
                <span className="text-2xl font-black text-white">{completion}%</span>
                <span className="text-xs text-slate-400">Complete</span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {completion === 100
                  ? 'All essential records ready'
                  : `${profile.stats.missing_items.length} item(s) pending`}
              </p>
            </div>

            {/* Visual Ring / Gauge */}
            <div className="relative w-14 h-14 flex items-center justify-center shrink-0">
              <svg className="w-14 h-14 transform -rotate-90">
                <circle
                  cx="28"
                  cy="28"
                  r="22"
                  stroke="#162e4f"
                  strokeWidth="5"
                  fill="none"
                />
                <circle
                  cx="28"
                  cy="28"
                  r="22"
                  stroke={completion === 100 ? '#10b981' : '#ff7518'}
                  strokeWidth="5"
                  strokeDasharray="138"
                  strokeDashoffset={138 - (138 * completion) / 100}
                  strokeLinecap="round"
                  fill="none"
                  className="transition-all duration-700 ease-out"
                />
              </svg>
              <span className="absolute text-xs font-bold text-white">
                {completion}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
